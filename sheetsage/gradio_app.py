import json
import os
import logging
import pathlib
import uuid
import tempfile
import shutil
import gradio as gr
import matplotlib
matplotlib.use('Agg') # Use Agg backend for non-GUI environments
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
from scipy.io import wavfile
import pretty_midi
import librosa
import torch

from sheetsage.infer import sheetsage
from sheetsage.utils import engrave
from sheetsage.align import create_beat_to_time_fn
from sheetsage.piano_transcription import transcribe_piano
from sheetsage.basic_pitch_transcription import transcribe_basic_pitch

def transcribe_audio_piano(audio_file, progress=gr.Progress()):
    """
    Transcribes audio using ByteDance's Piano Transcription.
    """
    output_dir = None
    output_files_list = []
    synthesized_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None

    if not audio_file:
         return None, None, None, None, None, None, "Please upload an audio file."

    logging.info("Starting Piano Transcription")
    print(f"\n--- Starting Piano Transcription (ByteDance) ---")
    progress(0, desc="Initializing...")

    try:
        # Prepare output directory
        base_temp_dir = pathlib.Path(os.getcwd()) / "output" / "piano"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir = base_temp_dir / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        output_midi_path = output_dir / "transcription.midi"

        # Run transcription
        progress(0.2, desc="Loading Model & Transcribing...")
        transcribe_piano(audio_file, str(output_midi_path))

        output_files_list.append(str(output_midi_path))

        # Synthesize Audio
        progress(0.8, desc="Synthesizing Audio...")
        # Use config soundfont or default
        soundfont_path = current_config.get("soundfont_path", "")
        if not soundfont_path or not os.path.exists(soundfont_path):
             soundfont_path = os.path.join(os.getcwd(), "soundfont", "MS Basic.sf3")

        synthesized_audio_path = synthesize_midi(str(output_midi_path), soundfont_path, output_dir, filename="piano_synth.wav")
        if synthesized_audio_path:
             output_files_list.append(synthesized_audio_path)

             # Mix with original
             mixed_audio_path, original_audio_segment_path = create_mix(
                  audio_file,
                  synthesized_audio_path,
                  output_dir
             )
             if mixed_audio_path:
                  output_files_list.append(mixed_audio_path)

        # Return consistent tuple: files, fig, synth, mix, orig, vocals, status
        return output_files_list, None, synthesized_audio_path, mixed_audio_path, original_audio_segment_path, None, "Transcription successful!"

    except Exception as e:
        logging.exception("Error during piano transcription")
        return None, None, None, None, None, None, f"Error: {str(e)}"

from sheetsage.config_manager import load_config, save_config

# Load initial configuration
current_config = load_config()


def plot_piano_roll(lead_sheet):
    """
    Generates a piano roll plot from the lead sheet.
    """
    # Use object-oriented Figure to avoid memory leaks with pyplot
    fig = Figure(figsize=(12, 6))
    ax = fig.subplots()
    
    # Extract melody notes from LeadSheet tuple (index 4)
    melody = lead_sheet[4]
    
    melody_pitches = []
    melody_onsets = []
    melody_durations = []
    
    for onset, duration, note in melody:
        pitch = note.as_midi_pitch()
        melody_pitches.append(pitch)
        melody_onsets.append(onset)
        melody_durations.append(duration)
        
    if melody_pitches:
        # Create barh (horizontal bars)
        # barh(y, width, left=x, height=height)
        ax.barh(melody_pitches, melody_durations, left=melody_onsets, height=0.8, color='#4A90E2', label='Melody')
        
        # Determine range for clean look
        min_p = min(melody_pitches)
        max_p = max(melody_pitches)
        ax.set_ylim(min_p - 5, max_p + 5)
        
        ax.set_ylabel("MIDI Pitch")
        ax.set_xlabel("Time (Quantized Steps)")
        ax.set_title("Piano Roll Visualization")
        
        # Grid
        ax.grid(True, linestyle='--', alpha=0.3)
    else:
        ax.text(0.5, 0.5, "No Melody Detected", ha='center', va='center', transform=ax.transAxes)
        ax.set_title("Piano Roll (Empty)")

    fig.tight_layout()
    return fig

def synthesize_midi(midi_path, soundfont_path_config, output_dir, filename="output.wav"):
    """
    Synthesizes MIDI file to WAV using FluidSynth.
    """
    try:
        if not os.path.exists(soundfont_path_config):
             logging.warning(f"Soundfont not found at {soundfont_path_config}")
             return None
             
        pm = pretty_midi.PrettyMIDI(midi_path)
        audio_data = pm.fluidsynth(fs=44100, sf2_path=soundfont_path_config)
        
        # Normalize
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data = audio_data / max_val
        else:
            logging.warning("Synthesized audio is silent.")
        
        # Convert to 16-bit PCM for broader compatibility
        audio_data_int16 = (audio_data * 32767).astype(np.int16)
        
        wav_path = output_dir / filename
        wavfile.write(str(wav_path), 44100, audio_data_int16)
        return str(wav_path)
    except Exception as e:
        logging.error(f"Synthesis failed: {e}")
        return None

def create_mix(original_path, synth_path, output_dir, offset=0.0, duration=None):
    """
    Mixes original audio (cropped) with synthesized audio.
    """
    try:
        # Load Original
        y_orig, _ = librosa.load(original_path, sr=44100, offset=offset, duration=duration, mono=True)
        
        # Load Synth
        y_synth, _ = librosa.load(synth_path, sr=44100, mono=True)
        
        # Pad or Trim to match lengths
        max_len = max(len(y_orig), len(y_synth))
        
        # Pad original if shorter
        if len(y_orig) < max_len:
            y_orig = np.pad(y_orig, (0, max_len - len(y_orig)))
            
        # Pad synth if shorter
        if len(y_synth) < max_len:
            y_synth = np.pad(y_synth, (0, max_len - len(y_synth)))
            
        # Mix (Weighted average to avoid clipping)
        y_mix = (y_orig * 0.4) + (y_synth * 0.6)
        
        # Normalize
        max_val = np.abs(y_mix).max()
        if max_val > 0:
             y_mix /= max_val

        # Convert to int16
        audio_data_int16 = (y_mix * 32767).astype(np.int16)
        
        mix_path = output_dir / "output_mixed.wav"
        wavfile.write(str(mix_path), 44100, audio_data_int16)
        
        # Also save the original cropped segment for preview
        orig_crop_path = output_dir / "output_original.wav"
        y_orig_int16 = (y_orig * 32767).astype(np.int16)
        wavfile.write(str(orig_crop_path), 44100, y_orig_int16)

        return str(mix_path), str(orig_crop_path)
    except Exception as e:
        logging.error(f"Mixing failed: {e}")
        return None, None


def transcribe_audio_lead_sheet(
    audio_file,
    audio_url,
    segment_start_hint,
    segment_end_hint,
    use_jukebox,
    measures_per_chunk,
    segment_hints_are_downbeats,
    beats_per_measure,
    beats_per_minute_hint,
    melody_threshold,
    harmony_threshold,
    detect_melody,
    detect_harmony,
    legacy_behavior,
    separate_vocals=False,
    progress=gr.Progress()
):
    """
    Transcribes audio to a lead sheet (PDF and MIDI).
    """
    output_dir = None
    output_files_list = []
    fig = None
    synthesized_audio_path = None
    mixed_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None
    demucs_vocals_path = None
    audio_path_melody = None # Path for melody detection (vocals)

    try:
        # Determine audio source
        audio_path_or_url = None
        if audio_file is not None:
            audio_path_or_url = audio_file
        elif audio_url and audio_url.strip():
            audio_path_or_url = audio_url.strip()

        if not audio_path_or_url:
            return None, None, None, None, None, None, "Please provide an audio file or URL."

        # Demucs Separation (if enabled)
        if separate_vocals and audio_file:
            try:
                msg_demucs = "Separating vocals with Demucs..."
                print(msg_demucs)
                progress(0.1, desc=msg_demucs)
                
                # Import here to avoid slow load if unused
                import demucs.separate
                import shlex
                import subprocess
                
                # Create a local dir for separation (Portable)
                sep_out_dir = pathlib.Path(os.getcwd()) / "output" / "demucs" / uuid.uuid4().hex
                sep_out_dir.mkdir(parents=True, exist_ok=True)
                
                # Run Demucs via command line (safest way to use the library)
                # Using htdemucs for speed/quality balance on GTX 1060
                # We use the embedded python for this call
                python_exe = os.path.join("python_embeded", "python.exe") if os.path.isdir("python_embeded") else "python"
                
                # Use list arguments to avoid Windows quoting issues with shlex
                cmd_args = [
                    python_exe, "-m", "demucs.separate",
                    "-n", "htdemucs",
                    "-o", str(sep_out_dir),
                    audio_path_or_url
                ]
                print(f"Running Demucs: {' '.join(cmd_args)}")
                
                proc = subprocess.run(cmd_args, shell=False, capture_output=True, text=True)
                
                if proc.returncode != 0:
                     logging.error(f"Demucs failed: {proc.stderr}")
                     print(f"Demucs failed: {proc.stderr}")
                else:
                     # Find the vocal track
                     # Structure: output_dir / htdemucs / track_name / vocals.wav
                     filename = pathlib.Path(audio_path_or_url).stem
                     vocals_path = sep_out_dir / "htdemucs" / filename / "vocals.wav"
                     if vocals_path.exists():
                          print(f"Using separated vocals: {vocals_path}")
                          demucs_vocals_path = str(vocals_path)
                          audio_path_melody = demucs_vocals_path
            except Exception as e:
                logging.error(f"Demucs error: {e}")

        # Logging Info
        device = "cuda" if torch.cuda.is_available() else "cpu"
        device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        msg_hw = f"Hardware: {device_name} ({device})"
        msg_model = f"Model: {'Jukebox' if use_jukebox else 'SheetSage (Standard)'}"
        
        logging.info(msg_hw)
        logging.info(msg_model)
        print(f"\n--- Starting Lead Sheet Transcription ---")
        print(msg_hw)
        print(msg_model)
        
        if use_jukebox and torch.cuda.is_available():
             vram = torch.cuda.get_device_properties(0).total_memory / 1e9
             if vram < 11.0:
                  warn = f"⚠️ WARNING: Low VRAM detected ({vram:.1f} GB). Jukebox mode typically requires >11 GB VRAM. This process may crash or freeze your system."
                  print(warn)
                  logging.warning(warn)
                  gr.Warning(warn) # Gradio popup warning if supported in this version

        progress(0, desc="Initializing...")

        # Handle optional float/int inputs that might be None or 0
        segment_start_hint = float(segment_start_hint) if segment_start_hint is not None else None
        segment_end_hint = float(segment_end_hint) if segment_end_hint is not None else None

        # Sanitize hints
        start_val = segment_start_hint if segment_start_hint is not None else 0.0
        if segment_end_hint is not None and segment_end_hint <= start_val:
            logging.warning(f"Ignoring invalid segment_end_hint ({segment_end_hint}) <= start ({start_val})")
            segment_end_hint = None

        # Run transcription
        result_tuple = sheetsage(
            audio_path_bytes_or_url=audio_path_or_url,
            audio_path_melody=audio_path_melody,
            audio_path_harmony=audio_path_or_url,
            segment_start_hint=segment_start_hint,
            segment_end_hint=segment_end_hint,
            # use_jukebox parameter removed from sheetsage()
            # use_jukebox=use_jukebox, 
            measures_per_chunk=int(measures_per_chunk),
            segment_hints_are_downbeats=segment_hints_are_downbeats,
            beats_per_measure_hint=int(beats_per_measure) if beats_per_measure else None,
            beats_per_minute_hint=int(beats_per_minute_hint) if beats_per_minute_hint else None,
            detect_melody=detect_melody,
            detect_harmony=detect_harmony,
            melody_threshold=float(melody_threshold) if melody_threshold is not None else None,
            harmony_threshold=float(harmony_threshold) if harmony_threshold is not None else None,
            legacy_behavior=legacy_behavior,
            status_change_callback=lambda s: print(f"Progress Update: {s.name}"),
            tqdm=progress.tqdm,
            return_intermediaries=False
        )
        progress(0.7, desc="Generating Output Files...")
        
        # Unpack results
        lead_sheet, segment_beats, segment_beats_times = result_tuple

        # Generate output files
        # Use tempfile.gettempdir() for cross-platform compatibility
        # Use temporary directory relative to project
        base_temp_dir = pathlib.Path(os.getcwd()) / "output" / "leadsheet"
        base_temp_dir.mkdir(parents=True, exist_ok=True)

        output_dir = base_temp_dir / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Inform regarding separation
        if separate_vocals:
             print("TIP: If separation succeeded, check the 'output/demucs' folder for the separated vocal stems. You can use those stems for manual refinement if needed.")

        # Generate Piano Roll
        try:
            fig = plot_piano_roll(lead_sheet)
        except Exception as e:
            logging.error(f"Piano roll generation failed: {e}")

        # Convert to LilyPond
        lily = lead_sheet.as_lily()
        ly_path = output_dir / "output.ly"
        with open(ly_path, "w") as f:
            f.write(lily)
        output_files_list.append(str(ly_path))

        # Engrave to PDF (Optional - Soft Failure)
        try:
            pdf_bytes = engrave(lily, out_format="pdf", transparent=False, trim=False, hide_footer=False)
            pdf_path = output_dir / "output.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            output_files_list.append(str(pdf_path))
        except Exception as e:
            logging.error(f"Engraving to PDF failed: {e}")
            logging.warning("Continuing to generate MIDI output...")

        # Generate MIDI (Optional - Soft Failure)
        midi_path_str = None
        try:
            midi_bytes = lead_sheet.as_midi(
                pulse_to_time_fn=create_beat_to_time_fn(segment_beats, segment_beats_times)
            )
            midi_path = output_dir / "output.midi"
            with open(midi_path, "wb") as f:
                f.write(midi_bytes)
            output_files_list.append(str(midi_path))
            midi_path_str = str(midi_path)
        except Exception as e:
             logging.error(f"MIDI generation failed: {e}")
             
        # Synthesize Audio (if MIDI success)
        if midi_path_str:
             synthesized_audio_path = synthesize_midi(midi_path_str, current_config["soundfont_path"], output_dir)
             if synthesized_audio_path:
                  output_files_list.append(synthesized_audio_path)
                  
                  # Attempt to mix if local file is available
                  if os.path.isfile(audio_path_or_url):
                      duration = None
                      if segment_start_hint is not None and segment_end_hint is not None:
                          duration = segment_end_hint - segment_start_hint
                      elif segment_start_hint is not None:
                          # Est duration from synth
                          pass # Librosa handles None duration as 'until end'
                          
                      mixed_audio_path, original_audio_segment_path = create_mix(
                          audio_path_or_url, 
                          synthesized_audio_path, 
                          output_dir, 
                          offset=segment_start_hint if segment_start_hint else 0.0,
                          duration=duration
                      )
                      if mixed_audio_path:
                           output_files_list.append(mixed_audio_path)
                      if original_audio_segment_path:
                           pass # Don't add to download list necessarily, but used for preview
        
        status = "Transcription successful!"
        if not any(f.endswith(".pdf") for f in output_files_list):
             status += " (PDF failed)"
        if not any(f.endswith(".midi") for f in output_files_list):
             status += " (MIDI failed)"
        if synthesized_audio_path:
             status += " (Audio synthesized)"

        return output_files_list, fig, synthesized_audio_path, mixed_audio_path, original_audio_segment_path, demucs_vocals_path, status

    except Exception as e:
        logging.exception("Error during transcription")
        return None, None, None, None, None, None, f"Error: {str(e)}\n\nIf you see a 403 Forbidden error, the model files could not be downloaded."

def transcribe_audio_basic_pitch(audio_file, progress=gr.Progress()):
    """
    Transcribes audio using Spotify's Basic Pitch (Melody) + Sheet Sage (Infrastructure).
    """
    output_dir = None
    output_files_list = []
    synthesized_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None

    if not audio_file:
         return None, None, None, None, None, None, "Please upload an audio file."

    logging.info("Starting Basic Pitch Transcription")
    print(f"\n--- Starting Basic Pitch Transcription ---")
    progress(0, desc="Initializing...")

    try:
        # Prepare output directory
        base_temp_dir = pathlib.Path(os.getcwd()) / "output" / "basic_pitch"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir = base_temp_dir / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        output_midi_path = output_dir / "basic_pitch.midi"

        # Run transcription (Now returns list of files: Ly, PDF, MIDI)
        generated_files = transcribe_basic_pitch(
            audio_file, 
            str(output_midi_path),
            status_callback=lambda s: progress(None, desc=s),
            tqdm_func=progress.tqdm
        )
        
        output_files_list.extend(generated_files)

        # Synthesize Audio (Standard Logic)
        # We look for the MIDI file in the returned list
        # Prioritize RAW MIDI (Polyphonic + Bends) for synthesis if available
        midi_file = next((f for f in generated_files if "raw" in pathlib.Path(f).name), None)
        if not midi_file:
             midi_file = next((f for f in generated_files if f.endswith(".midi") or f.endswith(".mid") ), None)
        
        if midi_file:
            synthesized_audio_path = synthesize_midi(midi_file, current_config["soundfont_path"], output_dir, filename="basic_pitch_synth.wav")
            if synthesized_audio_path:
                 output_files_list.append(synthesized_audio_path)

                 # Mix with original
                 mixed_audio_path, original_audio_segment_path = create_mix(
                      audio_file,
                      synthesized_audio_path,
                      output_dir
                 )
                 if mixed_audio_path:
                      output_files_list.append(mixed_audio_path)

        # Return consistent tuple: files, fig, synth, mix, orig, vocals, status
        return output_files_list, None, synthesized_audio_path, mixed_audio_path, original_audio_segment_path, None, "Basic Pitch transcription successful!"

    except Exception as e:
        logging.exception("Error during basic pitch transcription")
        return None, None, None, None, None, None, f"Error: {str(e)}"

# Rename for backward compatibility or simple renaming
transcribe_audio = transcribe_audio_lead_sheet

# Unified Transcriber Handler
def unified_transcriber(
    mode,
    audio_file,
    audio_url,
    segment_start_hint,
    segment_end_hint,
    measures_per_chunk,
    segment_hints_are_downbeats,
    beats_per_measure,
    beats_per_minute_hint,
    melody_threshold,
    harmony_threshold,
    detect_melody,
    detect_harmony,
    legacy_behavior,
    separate_vocals,
    progress=gr.Progress()
):
    if mode == "Piano (Polyphonic)":
        return transcribe_audio_piano(audio_file, progress=progress)
    elif mode == "Basic Pitch (Polyphonic)":
        return transcribe_audio_basic_pitch(audio_file, progress=progress)
    else: # Lead Sheet (Standard)
        return transcribe_audio_lead_sheet(
            audio_file, audio_url, segment_start_hint, segment_end_hint,
            False, # use_jukebox
            measures_per_chunk, segment_hints_are_downbeats, beats_per_measure,
            beats_per_minute_hint, melody_threshold, harmony_threshold,
            detect_melody, detect_harmony, legacy_behavior, separate_vocals,
            progress=progress
        )

# Custom CSS for a better look
css = """
.container { max-width: 900px; margin: auto; padding-top: 20px; }
h1 { text-align: center; color: #2d3748; }
.description { text-align: center; margin-bottom: 20px; color: #4a5568; }
.footer { text-align: center; margin-top: 40px; font-size: 0.8em; color: #718096; }
"""

with gr.Blocks(title="Sheet Sage", css=css) as demo:
    gr.Markdown("# 🎼 Sheet Sage")
    gr.Markdown("### Audio to Lead Sheet Transcription", elem_classes=["description"])

    with gr.Tabs():
        with gr.TabItem("Transcribe"):
            with gr.Row(elem_classes=["container"]):
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Input")
                    
                    with gr.Tabs():
                        with gr.TabItem("Upload File"):
                            audio_file = gr.Audio(type="filepath", label="Audio File")
                        with gr.TabItem("Audio URL"):
                            audio_url = gr.Textbox(label="URL", placeholder="https://example.com/audio.mp3")

                    gr.Markdown("### 2. Mode")
                    mode = gr.Radio(
                        ["Lead Sheet (Standard)", "Piano (Polyphonic)", "Basic Pitch (Polyphonic)"],
                        label="Transcription Mode",
                        value="Lead Sheet (Standard)",
                        info="Select the transcription model suitable for your audio."
                    )
                    
                    # Lead Sheet Settings Group
                    with gr.Group(visible=True) as lead_sheet_options:
                        gr.Markdown("### 3. Advanced Settings")
                        with gr.Row():
                             separate_vocals = gr.Checkbox(label="Separate Vocals (Demucs)", value=True, info="Recommended for songs with vocals.")
                        
                        with gr.Accordion("Fine-Tuning", open=False):
                            with gr.Row():
                                segment_start_hint = gr.Number(label="Start Time (s)", value=None, precision=1)
                                segment_end_hint = gr.Number(label="End Time (s)", value=None, precision=1)
                            
                            with gr.Row():
                                 detect_melody = gr.Checkbox(label="Detect Melody", value=True)
                                 detect_harmony = gr.Checkbox(label="Detect Harmony", value=True)
                            
                            with gr.Row():
                                melody_threshold = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, value=0.5, label="Melody Threshold")
                                harmony_threshold = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, value=0.5, label="Harmony Threshold")

                            with gr.Row():
                                beats_per_measure = gr.Dropdown(choices=[3, 4], label="Beats Per Measure", value=None)
                                beats_per_minute_hint = gr.Number(label="BPM Hint", value=None)

                            measures_per_chunk = gr.Slider(minimum=1, maximum=24, step=1, value=8, label="Measures Per Chunk")
                            segment_hints_are_downbeats = gr.Checkbox(label="Start/End align with Downbeats", value=False)
                            legacy_behavior = gr.Checkbox(label="Legacy Behavior", value=False)

                    submit_btn = gr.Button("Transcribe", variant="primary", size="lg")
                    
                    # Visibility Logic
                    def update_visibility(selected_mode):
                        return gr.Group(visible=(selected_mode == "Lead Sheet (Standard)"))
                    
                    mode.change(fn=update_visibility, inputs=mode, outputs=lead_sheet_options)

                with gr.Column(scale=1):
                    gr.Markdown("### Output")
                    status_msg = gr.Textbox(label="Status", interactive=False)
                    output_files = gr.Files(label="Download Results", visible=True, file_types=[ ".pdf", ".midi", ".ly", ".wav"])

                    with gr.Accordion("Preview", open=True):
                         piano_roll_plot = gr.Plot(label="Piano Roll Visualization (Lead Sheet Only)")
                         
                         with gr.Tabs():
                            with gr.TabItem("Mixed Overlay"):
                                 audio_output_mix = gr.Audio(label="Mixed (Original + Notes)", interactive=False)
                            with gr.TabItem("Synthesized"):
                                 audio_output_synth = gr.Audio(label="Notes Only", interactive=False)
                            with gr.TabItem("Original Segment"):
                                 audio_output_orig = gr.Audio(label="Original Sound", interactive=False)
                            with gr.TabItem("Separated Vocals (Demucs)"):
                                 audio_output_vocals = gr.Audio(label="Vocals", interactive=False)

            submit_event = submit_btn.click(
                unified_transcriber,
                inputs=[
                    mode,
                    audio_file, audio_url, 
                    segment_start_hint, segment_end_hint, 
                    measures_per_chunk, segment_hints_are_downbeats, beats_per_measure,
                    beats_per_minute_hint, melody_threshold, harmony_threshold,
                    detect_melody, detect_harmony, legacy_behavior, separate_vocals
                ],
                outputs=[output_files, piano_roll_plot, audio_output_synth, audio_output_mix, audio_output_orig, audio_output_vocals, status_msg],
            )

        # Settings Tab
        with gr.TabItem("Settings"):
            gr.Markdown("### Application Settings")
            with gr.Row(elem_classes=["container"]):
                with gr.Column():
                    sf_path_input = gr.Textbox(
                        label="SoundFont Path",
                        value=current_config.get("soundfont_path", ""),
                        info="Path to the .sf2 or .sf3 file used for MIDI synthesis.",
                        interactive=True
                    )
                    settings_status = gr.Textbox(label="Status", interactive=False)
                    save_settings_btn = gr.Button("Save Settings", variant="primary")

            def save_settings(sf_path):
                global current_config
                new_config = current_config.copy()
                new_config["soundfont_path"] = sf_path
                save_config(new_config)
                current_config = new_config
                return "Settings saved successfully!"

            save_settings_btn.click(
                save_settings,
                inputs=[sf_path_input],
                outputs=[settings_status]
            )

    gr.Markdown("Built with Sheetsage", elem_classes=["footer"])
