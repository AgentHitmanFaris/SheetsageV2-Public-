import logging
import os
import pathlib
import uuid
import tempfile
import numpy as np
import pretty_midi

import os

# Optimize ONNX Runtime initialization
os.environ["BASIC_PITCH_USE_ONNX"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["ORTSESS_OPT_LEVEL"] = "99" # Enable all optimizations


from sheetsage.infer import sheetsage, Status
from sheetsage.theory.internal import Melody, Note
from sheetsage.theory import LeadSheet
from sheetsage.utils import engrave
from sheetsage.align import create_beat_to_time_fn

def transcribe_basic_pitch(audio_path, output_midi_path,
                           segment_start_hint=None,
                           segment_end_hint=None,
                           measures_per_chunk=8,
                           beats_per_measure=None,
                           beats_per_minute_hint=None,
                           onset_threshold=0.5,
                           frame_threshold=0.3,
                           min_note_length=58,
                           min_freq=None,
                           max_freq=None,
                           skip_pdf_generation=False,
                           status_callback=lambda s: None,
                           tqdm_func=lambda x: x):
    """
    Transcribes audio to Lead Sheet using Basic Pitch for melody and Sheet Sage for harmony/grid.

    Args:
        audio_path (str): Path to audio file.
        output_midi_path (str): Path to save final MIDI. (This function also generates PDF/Ly in the same dir)
        skip_pdf_generation (bool): If True, skips LilyPond/PDF generation.
        ... options ...
        tqdm_func (callable): Function to wrap iterables for progress bars (e.g. tqdm).
    """
    logging.info(f"Starting Basic Pitch + Sheet Sage Lead Sheet generation for {audio_path}")

     # Print Hardware Info for User
    try:
        import onnxruntime as ort
        if "CUDAExecutionProvider" in ort.get_available_providers():
             logging.info("Hardware: NVIDIA GPU (ONNX Runtime)")
             print("Hardware: NVIDIA GPU (ONNX Runtime)")
        else:
             logging.info("Hardware: CPU (ONNX Runtime)")
             print("Hardware: CPU (ONNX Runtime)")
    except ImportError:
         pass # Fallback doesn't matter
    
    # 1. Run Sheet Sage to get the infrastructure (Grid, Chords, Meter, Key) 
    # We disable melody detection to save time/resources on the Sheet Sage side.
    logging.info("Running Sheet Sage for infrastructure (Beat Tracking, Harmony)...")
    if status_callback: status_callback("Analyzing Audio Structure (Sheet Sage)...")
    
    # Adapter for Sheet Sage status enum to string callback
    def ss_status_adapter(s):
        if status_callback:
            # s.name is e.g. 'DETECTING_BEATS'
            msg = f"Sheet Sage: {s.name.replace('_', ' ').title()}"
            logging.info(msg)
            status_callback(msg)

    # We need to capture the intermediates
    import time
    ss_start = time.time()
    try:
        # NOTE: We disable the Gradio tqdm here (pass lambda x: x) because generally SheetSage 
        # infrastructure steps can be granular and updating the UI over websockets too frequently 
        # causes massive slowdowns (e.g. 2m vs 30s).
        ss_result = sheetsage(
            audio_path_bytes_or_url=audio_path,
            segment_start_hint=segment_start_hint,
            segment_end_hint=segment_end_hint,

            measures_per_chunk=measures_per_chunk,
            beats_per_measure_hint=beats_per_measure,
            beats_per_minute_hint=beats_per_minute_hint,
            detect_melody=False, # We will replace this
            detect_harmony=True,
            return_intermediaries=False,
            status_change_callback=ss_status_adapter,
            tqdm=lambda x: x # Disable tqdm to avoid Gradio overhead
        )
        lead_sheet_base, segment_beats, segment_beats_times = ss_result
    except Exception as e:
        import traceback
        logging.error(f"Sheet Sage infrastructure failed:\n{traceback.format_exc()}")
        raise e
    ss_end = time.time()
    logging.info(f"Sheet Sage infrastructure completed in {ss_end - ss_start:.2f} seconds")

    # 2. Run Basic Pitch to get the raw notes
    logging.info("Running Basic Pitch for Melody...")
    bp_start = time.time()
    if status_callback: status_callback("Transcribing Melody (Basic Pitch)... This may take a moment to load the model.")
    
    # Defer import to avoid interference with Sheet Sage
    from basic_pitch.inference import predict_and_save, ICASSP_2022_MODEL_PATH
    
    bp_end_import = time.time()
    logging.info(f"Basic Pitch Import took {bp_end_import - bp_start:.2f} seconds")

    output_dir = os.path.dirname(output_midi_path)
    # Use a temp directory for basic pitch output to avoid clutter naming issues
    # Force use of project local temp if available via env vars we set
    target_temp_base = os.environ.get("SHEETSAGE_TEMP", os.environ.get("TEMP", None))
    with tempfile.TemporaryDirectory(dir=target_temp_base) as temp_bp_dir:
        predict_and_save(
            [audio_path],
            output_directory=temp_bp_dir,
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            minimum_note_length=min_note_length,
            minimum_frequency=min_freq,
            maximum_frequency=max_freq
        )
        # Find the generated MIDI
        candidates = list(pathlib.Path(temp_bp_dir).glob("*_basic_pitch.mid"))
        if not candidates:
             raise FileNotFoundError("Basic Pitch did not generate a MIDI file.")
        bp_midi_path = candidates[0]
        
        # Load MIDI
        pm = pretty_midi.PrettyMIDI(str(bp_midi_path))

        # Save Raw Polyphonic MIDI (with Pitch Bends) to output
        output_dir = pathlib.Path(os.path.dirname(output_midi_path))
        raw_midi_path = output_dir / "basic_pitch_raw.midi"
        try:
             import shutil
             shutil.copy2(str(bp_midi_path), str(raw_midi_path))
             logging.info(f"Saved raw Basic Pitch MIDI to {raw_midi_path}")
        except Exception as e:
             logging.warning(f"Failed to save raw MIDI: {e}")
             raw_midi_path = None

    # 3. Integrate: Quantize Basic Pitch notes to Sheet Sage Grid
    logging.info("Aligning Basic Pitch notes to Grid...")
    if status_callback: status_callback("Formatting Lead Sheet...")

    # Reconstruct the grid (tertiaries) from the Lead Sheet result
    # We have segment_beats_times. Tertiaries are 4 per beat.
    # However, sheetsage() returns segment_beats_times which are just beats.
    # We need the full tertiary grid or a way to map to it.
    
    # sheetsage.infer.sheetsage returns (lead_sheet, segment_beats, segment_beats_times)
    # The Grid is defined inside LeadSheet (total_num_tertiary) but we need the TIMES to map audio -> index.
    
    # Actually, we can re-create the beat_to_time function.
    # segment_beats is indices. segment_beats_times is times in seconds.
    # We need to interpolate.
    
    # Note: Sheet Sage assumes constant tempo within measures usually, or linear interpolation.
    grid_times = []
    # segment_beats_times is a list of beat times.
    # 1 beat = 4 tertiaries.
    # If we have beats at t0, t1...
    # The tertiaries between t0 and t1 are t0, t0 + (t1-t0)*0.25, t0 + (t1-t0)*0.5, ...
    
    beats_times = np.array(segment_beats_times)
    
    # Basic interpolation
    # We can use np.interp to map Time -> Beat Index
    # Then Beat Index * 4 = Tertiary Index
    
    # beat_indices = np.arange(len(beats_times))
    # time_to_beat = lambda t: np.interp(t, beats_times, beat_indices)
    
    # However, segment_beats might not start at 0 if we cropped?
    # sheetsage return: segment_beats are indices relative to start?
    # Let's assume standard behavior.
    
    beat_indices = np.arange(len(beats_times))
    
    # Collect all notes from Basic Pitch
    all_notes = []
    for inst in pm.instruments:
        for note in inst.notes:
            all_notes.append(note)
            
    # Sort by start time
    all_notes.sort(key=lambda x: x.start)
    
    # Quantize to Tertiaries
    # Beat index (float)
    start_beats = np.interp([n.start for n in all_notes], beats_times, beat_indices)
    end_beats = np.interp([n.end for n in all_notes], beats_times, beat_indices)
    
    # Tertiary index (int)
    start_tertiaries = np.round(start_beats * 4).astype(int)
    end_tertiaries = np.round(end_beats * 4).astype(int)
    
    # Filter for valid range
    max_tertiary = lead_sheet_base[5] # total_num_tertiary (index 5)
    
    quantized_notes = []
    for i, note in enumerate(all_notes):
        s = start_tertiaries[i]
        e = end_tertiaries[i]
        d = max(1, e - s) # Minimum 1 unit duration
        
        if s >= max_tertiary: continue
        if s < 0: continue # Should not happen if time aligned
        
        # Clip duration
        if s + d > max_tertiary:
            d = max_tertiary - s
            
        quantized_notes.append((s, d, note.pitch))
        
    # 4. Skyline Monophonic Conversion
    # We need a list of non-overlapping notes for LeadSheet Melody.
    # We prioritize higher pitch.
    
    grid = [None] * max_tertiary # Stores pitch at each step
    
    for s, d, pitch in quantized_notes:
        for t in range(s, s + d):
            current = grid[t]
            if current is None or pitch > current:
                grid[t] = pitch
                
    # Convert grid back to notes (run-length encoding)
    final_melody_list = []
    if max_tertiary > 0:
        current_pitch = grid[0]
        current_start = 0
        
        for t in range(1, max_tertiary):
            p = grid[t]
            if p != current_pitch:
                # End of run
                if current_pitch is not None:
                    # Create Note object
                    # midi = 60 + 12*oct + pc -> oct = (midi - 60 - pc)/12
                    pc = current_pitch % 12
                    octave = int((current_pitch - 60 - pc) / 12)
                    note_obj = Note(pc, octave)
                    final_melody_list.append((current_start, t - current_start, note_obj))
                current_pitch = p
                current_start = t
                
        # Final run
        if current_pitch is not None:
             pc = current_pitch % 12
             octave = int((current_pitch - 60 - pc) / 12)
             note_obj = Note(pc, octave)
             final_melody_list.append((current_start, max_tertiary - current_start, note_obj))

    # 5. Create new LeadSheet
    # Unpack base
    meter_changes, tempo_changes, key_changes, harmony, _, total_num_tertiary = lead_sheet_base
    
    # Create new Melody object
    new_melody = Melody(*final_melody_list)
    
    new_lead_sheet = LeadSheet(
        meter_changes,
        tempo_changes,
        key_changes,
        harmony,
        new_melody,
        total_num_tertiary=total_num_tertiary
    )
    
    # 6. Generate Outputs (Ly, PDF, MIDI)
    # Output Dir
    output_dir = pathlib.Path(os.path.dirname(output_midi_path))
    output_filename = pathlib.Path(output_midi_path).stem
    
    # Lilypond
    ly_path = None
    pdf_path = None
    if not skip_pdf_generation:
        try:
            lily = new_lead_sheet.as_lily()
            ly_path = output_dir / f"output.ly"
            with open(ly_path, "w") as f:
                f.write(lily)
                
            # PDF
            pdf_bytes = engrave(lily, out_format="pdf", transparent=False, trim=False, hide_footer=False)
            pdf_path = output_dir / f"output.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as e:
            logging.error(f"Engraving failed: {e}")
    else:
        logging.info("Skipping PDF generation as requested.")
        
    # Formatted MIDI (Lead Sheet style)
    try:
        # Use simple tertiary mapping from tempo changes (assuming 1 tempo for simplicity or extracting from tempo_changes)
        # We need a proper pulse_to_time_fn for as_midi to sound synced.
        # Use the reverse of what we did? 
        # Actually sheetsage provides create_beat_to_time_fn.
        
        beatz = np.arange(len(beats_times))
        beat_to_time = create_beat_to_time_fn(beatz, beats_times)
        # tertiary is beat * 4
        # so tertiary_to_time(t) = beat_to_time(t / 4)
        
        midi_bytes = new_lead_sheet.as_midi(
            pulse_to_time_fn=lambda p: beat_to_time(p / 1) # tertiary is the pulse here?
            # Warning: as_midi implementation: 
            # tertiary_per_pulse = int(np.prod(meter[1:])) -> 4 for (4,2,2)
            # tertiary_to_time_fn = lambda t: pulse_to_time_fn(t / tertiary_per_pulse)
            # So pulse_to_time_fn expects BEATS.
            # My beat_to_time takes beats. Perfect.
        )
        
        with open(output_midi_path, "wb") as f:
            f.write(midi_bytes)
            
    except Exception as e:
         logging.error(f"MIDI generation failed: {e}")
         # Dump raw Basic Pitch MIDI as fallback if alignment failed completely?
         # No, keep consistency.
         raise e
         
    output_files = []
    if ly_path: output_files.append(str(ly_path))
    if pdf_path: output_files.append(str(pdf_path))
    if output_midi_path: output_files.append(str(output_midi_path))
    if raw_midi_path: output_files.append(str(raw_midi_path))
    
    # Copy original audio to output directory (necessary for project bundling)
    try:
        import shutil
        input_ext = os.path.splitext(audio_path)[1]
        dest_audio = output_dir / f"original{input_ext}"
        shutil.copy2(audio_path, dest_audio)
        output_files.append(str(dest_audio))
        logging.info(f"Copied original audio to {dest_audio}")
    except Exception as e:
        logging.warning(f"Failed to copy original audio: {e}")
    
    # Extract metadata for UI
    metadata = {}
    try:
        if 'tempo_changes' in locals() and tempo_changes:
            metadata['bpm'] = round(tempo_changes[0][1])
        if 'key_changes' in locals() and key_changes:
            metadata['key'] = key_changes[0][1]
        if 'meter_changes' in locals() and meter_changes:
            _, num, den = meter_changes[0]
            metadata['meter'] = f"{num}/{den}"
    except:
        pass

    print("Basic Pitch transcription finished successfully.")
    return {
        'files': output_files,
        'metadata': metadata
    }
