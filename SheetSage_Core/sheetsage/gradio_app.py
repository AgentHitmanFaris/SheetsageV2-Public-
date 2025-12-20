import json
import os
import logging
import pathlib
import uuid
import tempfile
import urllib.parse
import shutil
import time
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
import torchaudio
try:
    torchaudio.set_audio_backend("soundfile")
except:
    pass

from sheetsage.infer import sheetsage
from sheetsage.utils import engrave
from sheetsage.align import create_beat_to_time_fn
from sheetsage.piano_transcription import transcribe_piano
from sheetsage.basic_pitch_transcription import transcribe_basic_pitch
from sheetsage.modules.omnizart_transcription import run_omnizart
from sheetsage.modules.lunaverus_cnn import run_inference as run_lunaverus

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
    try:
        from sheetsage.utils import get_approximate_audio_length
        dur = get_approximate_audio_length(audio_file)
        print(f"Detected Audio Duration: {dur:.2f} seconds")
    except Exception as e:
        print(f"Could not detect duration: {e}")
    progress(0, desc="Initializing...")

    try:
        # Prepare output directory
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "piano"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Cleanup filename for folder
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        clean_name = pathlib.Path(audio_file).stem.replace(" ", "_").replace("(", "").replace(")", "")[:20]
        folder_name = f"{timestamp}_{clean_name}_{uuid.uuid4().hex[:6]}"
        
        output_dir = base_temp_dir / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        output_midi_path = output_dir / "transcription.midi"

        import time
        import threading
        # Timer logic
        start_time = time.time()
        stop_event = threading.Event()
        def timer_loop():
            while not stop_event.is_set():
                elapsed = int(time.time() - start_time)
                if elapsed > 0 and elapsed % 2 == 0:
                     print(f"[Piano Timer] Elapsed: {elapsed}s...", end='\r', flush=True)
                time.sleep(1)
        
        t_thread = threading.Thread(target=timer_loop, daemon=True)
        t_thread.start()

        # Run transcription
        progress(0.2, desc="Loading Model & Transcribing...")
        transcribe_piano(audio_file, str(output_midi_path))
        
        stop_event.set()
        t_thread.join(timeout=1.0)

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

        # Prepare Tracks
        tracks_dict = {}
        if original_audio_segment_path or audio_file:
             tracks_dict["Original"] = cache_file_for_playback(original_audio_segment_path if original_audio_segment_path else audio_file)
        if mixed_audio_path:
             tracks_dict["Mixed"] = cache_file_for_playback(mixed_audio_path)
        if synthesized_audio_path:
             tracks_dict["Synthesized"] = cache_file_for_playback(synthesized_audio_path)
             
        return format_player_output(output_files_list, None, tracks_dict, "Transcription successful!")

    except Exception as e:
        logging.exception("Error during piano transcription")
        return format_player_output(None, None, {}, f"Error: {e}")

def transcribe_audio_drums(audio_file, progress=gr.Progress()):
    """
    Transcribes drums using Omnizart (via external env).
    """
    output_dir = None
    output_files_list = []
    synthesized_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None

    if not audio_file:
         return None, None, None, None, None, None, "Please upload an audio file."

    logging.info("Starting Drum Transcription (Omnizart)")
    print(f"--- Starting Drum Transcription (Omnizart) ---")
    progress(0, desc="Initializing...")

    try:
        # Prepare output directory
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "drums"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        clean_name = pathlib.Path(audio_file).stem.replace(" ", "_").replace("(", "").replace(")", "")[:20]
        folder_name = f"{timestamp}_{clean_name}_{uuid.uuid4().hex[:6]}"
        
        output_dir = base_temp_dir / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Run transcription
        progress(0.2, desc="Running Omnizart (This may take a moment)...")
        # Omnizart directly writes MIDI to output_dir
        
        def omni_callback(msg):
             progress(None, desc=f"Omnizart: {msg[:50]}")
             
        # Call run_omnizart with mode="drum"
        output_midi_path = run_omnizart(
            audio_file, 
            str(output_dir), 
            mode="drum", 
            callback=omni_callback
        )
        
        if not output_midi_path:
             raise Exception("Omnizart failed to generate MIDI. Check console/logs.")

        output_files_list.append(str(output_midi_path))
        print(f"Omnizart output: {output_midi_path}")

        # Synthesize Audio (Drums usually need a drum soundfont or General MIDI channel 10)
        # FluidSynth uses Channel 10 for drums. PrettyMIDI might not default to Ch 10 unless the MIDI file specifies it.
        # Omnizart likely produces a MIDI file with Program 0 on Channel 9 (0-indexed).
        
        progress(0.8, desc="Synthesizing Audio...")
        # Use config soundfont or default
        soundfont_path = current_config.get("soundfont_path", "")
        if not soundfont_path or not os.path.exists(soundfont_path):
             soundfont_path = os.path.join(os.getcwd(), "soundfont", "MS Basic.sf3")

        # Synthesize
        synthesized_audio_path = synthesize_midi(str(output_midi_path), soundfont_path, output_dir, filename="drums_synth.wav")
        if synthesized_audio_path:
             output_files_list.append(synthesized_audio_path)
             
             # Mix
             mixed_audio_path, original_audio_segment_path = create_mix(
                  audio_file,
                  synthesized_audio_path,
                  output_dir
             )
             if mixed_audio_path:
                  output_files_list.append(mixed_audio_path)

        # Prepare Tracks
        tracks_dict = {}
        if original_audio_segment_path or audio_file:
             tracks_dict["Original"] = cache_file_for_playback(original_audio_segment_path if original_audio_segment_path else audio_file)
        if mixed_audio_path:
             tracks_dict["Mixed"] = cache_file_for_playback(mixed_audio_path)
        if synthesized_audio_path:
             tracks_dict["Synthesized"] = cache_file_for_playback(synthesized_audio_path)
             
        return format_player_output(output_files_list, None, tracks_dict, "Drum Transcription successful!")

    except Exception as e:
        logging.exception("Error during drum transcription")
        return format_player_output(None, None, {}, f"Error: {e}")

def transcribe_audio_omnizart_advanced(audio_file, mode, progress=gr.Progress()):
    """
    Transcribes audio using Omnizart with a selected mode.
    Modes: music, chord, drum, vocal, vocal-contour, beat
    """
    output_dir = None
    output_files_list = []
    synthesized_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None

    if not audio_file:
         return None, None, None, None, None, None, "Please upload an audio file."
    
    if not mode:
         mode = "music" # logical default

    logging.info(f"Starting Omnizart Advanced Transcription (Mode: {mode})")
    print(f"--- Starting Omnizart Advanced Transcription (Mode: {mode}) ---")
    progress(0, desc="Initializing...")

    try:
        # Prepare output directory
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "omnizart_advanced"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        clean_name = pathlib.Path(audio_file).stem.replace(" ", "_").replace("(", "").replace(")", "")[:20]
        folder_name = f"{timestamp}_{clean_name}_{mode}_{uuid.uuid4().hex[:6]}"
        
        output_dir = base_temp_dir / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Run transcription
        progress(0.2, desc=f"Running Omnizart ({mode})...")
        
        def omni_callback(msg):
             progress(None, desc=f"Omnizart ({mode}): {msg[:50]}")
             
        output_path = run_omnizart(audio_file, str(output_dir), mode=mode, callback=omni_callback)
        
        if not output_path:
             raise Exception("Omnizart failed to generate output. Check console/logs.")

        output_files_list.append(str(output_path))
        print(f"Omnizart output: {output_path}")

        # Synthesize Audio (if MIDI)
        # 'vocal-contour' might produce MIDI or CSV? Default omnizart usually produces midi for notes.
        # 'beat' produces txt.
        
        is_midi = output_path.lower().endswith(('.mid', '.midi'))
        
        if is_midi:
            progress(0.8, desc="Synthesizing Audio...")
            soundfont_path = current_config.get("soundfont_path", "")
            if not soundfont_path or not os.path.exists(soundfont_path):
                 soundfont_path = os.path.join(os.getcwd(), "soundfont", "MS Basic.sf3")
    
            # Special handling for drums soundfont or channel?
            # Existing synth function uses default fluid settings
            synthesized_audio_path = synthesize_midi(str(output_path), soundfont_path, output_dir, filename=f"{mode}_synth.wav")
            
            if synthesized_audio_path:
                 output_files_list.append(synthesized_audio_path)
                 
                 mixed_audio_path, original_audio_segment_path = create_mix(
                      audio_file,
                      synthesized_audio_path,
                      output_dir
                 )
                 if mixed_audio_path:
                      output_files_list.append(mixed_audio_path)
        else:
             # Non-MIDI output (beat txt, etc) - No synthesis
             # Still cache original for playback
             original_audio_segment_path = audio_file

        # Prepare Tracks
        tracks_dict = {}
        if original_audio_segment_path:
             tracks_dict["Original"] = cache_file_for_playback(original_audio_segment_path)
        if mixed_audio_path:
             tracks_dict["Mixed"] = cache_file_for_playback(mixed_audio_path)
        if synthesized_audio_path:
             tracks_dict["Synthesized"] = cache_file_for_playback(synthesized_audio_path)
             
        return format_player_output(output_files_list, None, tracks_dict, f"Omnizart ({mode}) Transcription successful!")

    except Exception as e:
        logging.exception(f"Error during omnizart {mode} transcription")
        return format_player_output(None, None, {}, f"Error: {e}")

def transcribe_audio_lunaverus(audio_file, progress=gr.Progress()):
    """
    Transcribes audio using the SheetSage V3 (Lunaverus-style) CNN.
    """
    output_dir = None
    output_files_list = []
    synthesized_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None

    if not audio_file:
         return None, None, None, None, None, None, "Please upload an audio file."
    
    logging.info("Starting SheetSage V3 (Lunaverus) Transcription")
    print(f"--- Starting SheetSage V3 (Lunaverus) Transcription ---")
    progress(0, desc="Initializing...")

    try:
        # Prepare output directory
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "sheetsage_v3"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        clean_name = pathlib.Path(audio_file).stem.replace(" ", "_").replace("(", "").replace(")", "")[:20]
        folder_name = f"{timestamp}_{clean_name}_v3_{uuid.uuid4().hex[:6]}"
        
        output_dir = base_temp_dir / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Run transcription
        progress(0.2, desc="Running CNN Inference (This might take a while)...")
        
        # Look for weights
        weights_path = os.path.join(os.path.dirname(__file__), "modules", "lunaverus_weights.pth")
        
        import timeit
        import threading
        
        # Timer logic
        t_start_time = time.time()
        stop_event = threading.Event()
        def timer_loop():
             while not stop_event.is_set():
                elapsed = int(time.time() - t_start_time)
                if elapsed > 0 and elapsed % 2 == 0:
                     print(f"[V3 Timer] Elapsed: {elapsed}s...", end='\r', flush=True)
                time.sleep(1)
        
        t_thread = threading.Thread(target=timer_loop, daemon=True)
        t_thread.start()

        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"V3 Running on: {device}")
        
        output_midi_path = run_lunaverus(audio_file, model_weights_path=weights_path, device=device)
        
        stop_event.set()
        t_thread.join(timeout=1.0)
        
        if not output_midi_path:
             raise Exception("Inference failed to generate MIDI.")

        # Move correct output to our folder if needed, or just use it
        # The module writes to same directory as input usually, let's move it to output_dir
        final_midi_path = output_dir / "transcription.midi"
        shutil.move(output_midi_path, final_midi_path)
        
        output_files_list.append(str(final_midi_path))
        print(f"Output: {final_midi_path}")

        # Synthesize Audio 
        progress(0.8, desc="Synthesizing Audio...")
        soundfont_path = current_config.get("soundfont_path", "")
        if not soundfont_path or not os.path.exists(soundfont_path):
             soundfont_path = os.path.join(os.getcwd(), "soundfont", "MS Basic.sf3")

        synthesized_audio_path = synthesize_midi(str(final_midi_path), soundfont_path, output_dir, filename="v3_synth.wav")
        if synthesized_audio_path:
             output_files_list.append(synthesized_audio_path)
             
             mixed_audio_path, original_audio_segment_path = create_mix(
                  audio_file,
                  synthesized_audio_path,
                  output_dir
             )
             if mixed_audio_path:
                  output_files_list.append(mixed_audio_path)

        # Prepare Tracks
        tracks_dict = {}
        if original_audio_segment_path or audio_file:
             tracks_dict["Original"] = cache_file_for_playback(original_audio_segment_path if original_audio_segment_path else audio_file)
        if mixed_audio_path:
             tracks_dict["Mixed"] = cache_file_for_playback(mixed_audio_path)
        if synthesized_audio_path:
             tracks_dict["Synthesized"] = cache_file_for_playback(synthesized_audio_path)
             
        return format_player_output(output_files_list, None, tracks_dict, "SheetSage V3 Transcription successful!")

    except Exception as e:
        logging.exception("Error during V3 transcription")
        return format_player_output(None, None, {}, f"Error: {e}")

from sheetsage.config_manager import load_config, save_config

# Load initial configuration
# Load initial configuration
current_config = load_config()

def cache_file_for_playback(original_path):
    """
    Returns the original file path for Gradio to serve.
    (Caching disabled - Gradio has issues serving copied files)
    """
    if not original_path or not os.path.exists(original_path):
        return None
    
    # Return original path directly - Gradio will serve it
    print(f"Audio file ready: {original_path}")
    return original_path

def get_history_items():
    """
    Scans the output directory for historical transcription projects.
    Returns a list of strings formatted as "[YYYY-MM-DD HH:MM] Relative/Path"
    """
    history_dir = current_config.get("output_dir", os.path.join(os.getcwd(), "output"))
    items = []
    
    if not os.path.exists(history_dir):
        return []

    # Using os.walk to find leaf directories or directories that look like projects
    for root, dirs, files in os.walk(history_dir):
        # A project usually has identifying files
        if any(f.endswith((".midi", ".mid", ".wav")) for f in files):
            # Check if this is a leaf node or a project folder
            # We filter out the 'demucs' folder internal structures usually, but showing them is harmless if they contain audio
            
            # Simple heuristic: If it has "output_mixed.wav" or "basic_pitch.midi" or "transcription.midi"
            valid_indicators = ["output_mixed.wav", "basic_pitch.midi", "transcription.midi", "vocals.wav"]
            if any(f in files for f in valid_indicators):
                rel_path = os.path.relpath(root, history_dir)
                try:
                     mtime = os.path.getmtime(root)
                     import datetime
                     dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                     items.append(f"[{dt}] {rel_path}")
                except:
                     items.append(rel_path)
    
    items.sort(reverse=True)
    return items

def load_history_project(selected_item):
    """
    Loads results from a selected history item back into the interface.
    """
    if not selected_item:
        return format_player_output(None, None, {}, "No item selected.")

    try:
        # Parse path
        if "] " in selected_item:
            rel_path = selected_item.split("] ", 1)[1]
        else:
            rel_path = selected_item
            
        base_output_dir = current_config.get("output_dir", os.path.join(os.getcwd(), "output"))
        project_dir = os.path.join(base_output_dir, rel_path)
        
        if not os.path.exists(project_dir):
            return format_player_output(None, None, {}, "Project directory not found.")

        # Security check: Ensure project_dir is inside base_output_dir
        # Resolve absolute paths to handle '..' correctly
        abs_base = os.path.abspath(base_output_dir)
        abs_project = os.path.abspath(project_dir)

        # Robust check using commonpath to prevent partial path traversal
        try:
             # commonpath raises ValueError if paths are on different drives
             if os.path.commonpath([abs_base, abs_project]) != abs_base:
                  raise ValueError("Path outside base directory")
        except ValueError:
             logging.warning(f"Security Alert: Path traversal attempt blocked. {abs_project} is not in {abs_base}")
             return format_player_output(None, None, {}, "Invalid project path.")
            
        files = [os.path.join(project_dir, f) for f in os.listdir(project_dir) if os.path.isfile(os.path.join(project_dir, f))]
        
        # 1. Output Files (Downloadable)
        # Filter for relevant extensions
        download_files = [f for f in files if f.lower().endswith(('.pdf', '.midi', '.mid', '.ly', '.wav'))]
        
        # 2. Audio Paths for Mixer
        # Basic heuristic to find the "best" file for each slot
        
        # Original
        # create_mix guarantees "output_original.wav"
        orig_path = next((f for f in files if "output_original.wav" in f), None)
        if not orig_path:
             # Fallback to anything with "original"
             orig_path = next((f for f in files if "original" in f and f.endswith(".wav")), None)
        
        # Mixed
        mix_path = next((f for f in files if "output_mixed.wav" in f), None)

        # Synth
        # "piano_synth.wav", "basic_pitch_synth.wav"
        synth_path = next((f for f in files if "synth" in f and f.endswith(".wav")), None)
        
        # Vocals
        # "vocals.wav" usually from demucs
        # For history, we might need to look deeper if it's the main project folder
        vocals_path = next((f for f in files if "vocals" in f and f.endswith(".wav")), None)
        
        # 3. Piano Roll
        fig = None
        midi_path = next((f for f in download_files if f.endswith(".midi") or f.endswith(".mid")), None)
        if midi_path:
            try:
                pm = pretty_midi.PrettyMIDI(midi_path)
                fig = Figure(figsize=(12, 6))
                ax = fig.subplots()
                
                # Collect notes
                all_notes = []
                for inst in pm.instruments:
                    for note in inst.notes:
                         all_notes.append((note.start, note.end, note.pitch))
                
                if all_notes:
                    starts = [n[0] for n in all_notes]
                    durations = [n[1] - n[0] for n in all_notes]
                    pitches = [n[2] for n in all_notes]
                    
                    ax.barh(pitches, durations, left=starts, height=0.8, color='#4A90E2')
                    mean_p = sum(pitches)/len(pitches)
                    ax.set_ylim(mean_p-12, mean_p+12) # Approximate view
                    ax.set_xlabel("Time (s)")
                    ax.set_ylabel("MIDI Pitch")
                    ax.set_title(f"Piano Roll: {os.path.basename(midi_path)}")
                    ax.grid(True, linestyle='--', alpha=0.3)
                    fig.tight_layout()
                else:
                    ax.text(0.5, 0.5, "Empty MIDI", ha='center', va='center')
            except Exception as e:
                 logging.warning(f"Failed to plot piano roll from history: {e}")
        # Vocals and other stems
        # Look for exact matches "vocals.wav", "bass.wav", "drums.wav", "other.wav"
        stems_map = {
            "Vocals": "vocals.wav",
            "Bass": "bass.wav", 
            "Drums": "drums.wav", 
            "Other": "other.wav"
        }
        
        tracks_dict = {}
        if orig_path: tracks_dict["Original"] = cache_file_for_playback(orig_path)
        if mix_path: tracks_dict["Mixed"] = cache_file_for_playback(mix_path)
        if synth_path: tracks_dict["Synthesized"] = cache_file_for_playback(synth_path)
        
        for label, filename in stems_map.items():
            found = next((f for f in files if os.path.basename(f) == filename), None)
            if found:
                tracks_dict[label] = cache_file_for_playback(found)

        return format_player_output(download_files, fig, tracks_dict, f"Loaded project: {rel_path}")
        
    except Exception as e:
        return format_player_output(None, None, {}, f"Error loading history: {e}")

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
             
        # Check if MIDI file exists and has size
        if not os.path.exists(midi_path) or os.path.getsize(midi_path) == 0:
             logging.warning(f"MIDI file is missing or empty: {midi_path}")
             return None

        pm = pretty_midi.PrettyMIDI(midi_path)
        
        # Debug MIDI content
        total_notes = sum(len(i.notes) for i in pm.instruments)
        duration = pm.get_end_time()
        # logging.info(f"Synthesizing MIDI: {total_notes} notes, {duration:.2f}s duration.")
        
        if total_notes == 0 or duration <= 0:
             logging.warning("MIDI file has no notes or zero duration. Skipping synthesis.")
             return None

        audio_data = pm.fluidsynth(fs=44100, sf2_path=soundfont_path_config)
        
        if audio_data is None or len(audio_data) == 0:
             logging.warning("Synthesized audio is empty.")
             return None

        # Normalize safely
        chk_max = np.abs(audio_data).max() if audio_data.size > 0 else 0
        if chk_max > 0:
            audio_data = audio_data / chk_max
        
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
            return format_player_output(None, None, {}, "Please provide an audio file or URL.")

        original_display_name = None
        if audio_file:
             original_display_name = os.path.basename(audio_file)

        # Sanitize filename for local files to avoid Unicode issues with Demucs/subprocess
        # We process a copy with a safe ASCII name
        if audio_file and os.path.exists(audio_file):
            safe_dir = pathlib.Path(os.getcwd()) / "temp" / "safe_inputs"
            safe_dir.mkdir(parents=True, exist_ok=True)
            ext = os.path.splitext(audio_file)[1]
            if not ext: ext = ".mp3" # Fallback
            safe_name = f"input_{uuid.uuid4().hex[:8]}{ext}"
            safe_path = safe_dir / safe_name
            import shutil
            shutil.copy(audio_file, safe_path)
            logging.info(f"Sanitized input: {audio_path_or_url} -> {safe_path}")
            audio_path_or_url = str(safe_path)
            audio_file = str(safe_path) # Update reference for downstream logic

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
                base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
                sep_out_dir = base_output_dir / "demucs" / uuid.uuid4().hex
                sep_out_dir.mkdir(parents=True, exist_ok=True)
                
                # Run Demucs via command line (safest way to use the library)
                # Using htdemucs for speed/quality balance on GTX 1060
                # We use the embedded python for this call
                python_exe = os.path.join("python_embeded", "python.exe") if os.path.isdir("python_embeded") else "python"
                
                # Use list arguments to avoid Windows quoting issues with shlex
                cmd_args = [
                    python_exe, os.path.join("sheetsage", "run_demucs.py"),
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
                     else:
                          print(f"Warning: Vocals file not found at {vocals_path}")
                          ht_dir = sep_out_dir / "htdemucs"
                          if ht_dir.exists():
                               try:
                                   files = [str(p.relative_to(ht_dir)) for p in ht_dir.glob('**/*')]
                                   print(f"Contents of {ht_dir}: {files}")
                               except:
                                   print(f"Could not list contents of {ht_dir}")
                          else:
                               print(f"Directory {ht_dir} does not exist.")
            except Exception as e:
                logging.error(f"Demucs error: {e}")

        # Logging Info
        device = "cuda" if torch.cuda.is_available() else "cpu"
        device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        msg_hw = f"Hardware: {device_name} ({device})"
        msg_model = "Model: SheetSage (Standard)"
        
        logging.info(msg_hw)
        logging.info(msg_model)
        print(f"\n--- Starting Lead Sheet Transcription ---")
        print(msg_hw)
        print(msg_model)
        
        try:
            from sheetsage.utils import get_approximate_audio_length
            dur = get_approximate_audio_length(audio_path_or_url or audio_file)
            print(f"Detected Audio Duration: {dur:.2f} seconds")
        except Exception as e:
            print(f"Could not detect duration: {e}")
        
        progress(0, desc="Initializing...")

        # Handle optional float/int inputs that might be None or 0
        segment_start_hint = float(segment_start_hint) if segment_start_hint is not None else None
        segment_end_hint = float(segment_end_hint) if segment_end_hint is not None else None

        # Sanitize hints
        start_val = segment_start_hint if segment_start_hint is not None else 0.0
        if segment_end_hint is not None and segment_end_hint <= start_val:
            logging.warning(f"Ignoring invalid segment_end_hint ({segment_end_hint}) <= start ({start_val})")
            segment_end_hint = None

        # Helper for status
        def status_cb(s):
             msg = f"SheetSage: {s.name.replace('_', ' ').title()}"
             print(f"[LeadSheet] {msg}")
             progress(None, desc=msg)

        import time
        import threading
        
        # Timer logic
        start_time = time.time()
        stop_event = threading.Event()
        def timer_loop():
            while not stop_event.is_set():
                elapsed = int(time.time() - start_time)
                if elapsed > 0 and elapsed % 2 == 0:
                     print(f"[SheetSage Timer] Elapsed: {elapsed}s...", end='\r', flush=True)
                time.sleep(1)
        
        t_thread = threading.Thread(target=timer_loop, daemon=True)
        t_thread.start()

        # Run transcription
        result_tuple = sheetsage(
            audio_path_bytes_or_url=audio_path_or_url,
            audio_path_melody=audio_path_melody,
            audio_path_harmony=audio_path_or_url,
            segment_start_hint=segment_start_hint,
            segment_end_hint=segment_end_hint,
            measures_per_chunk=int(measures_per_chunk),
            segment_hints_are_downbeats=segment_hints_are_downbeats,
            beats_per_measure_hint=int(beats_per_measure) if beats_per_measure else None,
            beats_per_minute_hint=int(beats_per_minute_hint) if beats_per_minute_hint else None,
            detect_melody=detect_melody,
            detect_harmony=detect_harmony,
            melody_threshold=float(melody_threshold) if melody_threshold is not None else None,
            harmony_threshold=float(harmony_threshold) if harmony_threshold is not None else None,
            legacy_behavior=legacy_behavior,
            status_change_callback=status_cb,
            tqdm=progress.tqdm,
            return_intermediaries=False
        )
        
        stop_event.set()
        t_thread.join(timeout=1.0)
        progress(0.7, desc="Generating Output Files...")
        
        # Unpack results
        lead_sheet, segment_beats, segment_beats_times = result_tuple

        # Generate output files
        # Use tempfile.gettempdir() for cross-platform compatibility
        # Use temporary directory relative to project
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "leadsheet"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Cleanup filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        name_src = original_display_name if original_display_name else audio_path_or_url
        if not name_src: name_src = "audio"
        
        # Robust name cleaning for folder creation
        # Remove extension
        stem = pathlib.Path(name_src).stem
        # Replace common delimiters with underscore
        clean_name = stem.replace(" ", "_").replace("(", "").replace(")", "")
        # Remove non-ascii or risky chars
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', clean_name)
        if not clean_name: clean_name = "audio_project"
        clean_name = clean_name[:40] #Reasonable length

        folder_name = f"{timestamp}_{clean_name}_{uuid.uuid4().hex[:6]}"

        output_dir = base_temp_dir / folder_name
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

        # Prepare Audio Tracks
        tracks_dict = {}
        if original_audio_segment_path or audio_path_or_url:
            tracks_dict["Original"] = cache_file_for_playback(original_audio_segment_path if original_audio_segment_path else audio_path_or_url)
        if mixed_audio_path:
            tracks_dict["Mixed"] = cache_file_for_playback(mixed_audio_path)
        if synthesized_audio_path:
            tracks_dict["Synthesized"] = cache_file_for_playback(synthesized_audio_path)
            
        # Demucs Stems
        if demucs_vocals_path and os.path.exists(demucs_vocals_path):
             tracks_dict["Vocals"] = cache_file_for_playback(demucs_vocals_path)
             # Check for other stems (bass, drums, other)
             parent_dir = os.path.dirname(demucs_vocals_path)
             for stem in ["bass.wav", "drums.wav", "other.wav"]:
                  stem_path = os.path.join(parent_dir, stem)
                  if os.path.exists(stem_path):
                       tracks_dict[stem.replace(".wav", "").capitalize()] = cache_file_for_playback(stem_path)
             
        return format_player_output(output_files_list, fig, tracks_dict, status)

    except Exception as e:
        logging.exception("Error during transcription")
        return format_player_output(None, None, {}, f"Error: {e}")

def generate_mixer_html(orig_path, synth_path, vocals_path=None):
    """
    Generates an AnthemScore-style HTML5 Audio Mixer.
    Features: Master Clock, Synchronized Seek, Independent Volume Sliders.
    """
    import uuid
    import urllib.parse
    
    player_id = f"mixer_{uuid.uuid4().hex[:8]}"
    
    def make_src(path):
        if not path: return ""
        s = str(path)
        if s.startswith("http") or s.startswith("data:"): return s
        
        # Enable absolute path handling for proper Gradio serving
        # Gradio 'allowed_paths' works best with absolute paths
        s = os.path.abspath(s)
        
        # Local file: Normalize and Encode for Gradio
        s = s.replace("\\", "/")
        # We generally do NOT need to quote the path for /file= locally if using basic ascii
        # But for spaces we do. urllib.parse.quote preserves / by default only if safe='/'
        # However, Gradio usually expects /file=D:/Folder/File.wav
        # Let's use quote but ensure slashes are kept
        encoded = urllib.parse.quote(s, safe=":/") 
        return f"/gradio_api/file={encoded}"

    src_orig = make_src(orig_path)
    src_synth = make_src(synth_path)
    src_vocals = make_src(vocals_path)
    
    # --- BUILD TRACKS & CONTROLS ---
    tracks_dom = ""
    controls_html = ""
    js_refs = ""
    
    # Helper to build a track row (Label + Volume Slider)
    # Replicates the AnthemScore look: Label on left, Long Slider on right
    def mk_track_row(label, aud_id, vol_id, color_hex):
        return f"""
        <div class="track-row">
            <div class="track-label" style="border-left: 4px solid {color_hex};">
                <span class="icon">🔊</span> {label}
            </div>
            <input type="range" id="{vol_id}" class="vol-slider" min="0" max="1" step="0.01" value="1.0" 
                   oninput="document.getElementById('{aud_id}').volume=this.value">
        </div>
        """

    # 1. Original Track
    if src_orig:
        tracks_dom += f'<audio id="{player_id}_orig" src="{src_orig}" preload="auto"></audio>'
        controls_html += mk_track_row("Original", f"{player_id}_orig", f"{player_id}_vol_orig", "#3b82f6") # Blue
        js_refs += f'const t1 = document.getElementById("{player_id}_orig"); tracks.push(t1);\n'

    # 2. Synth Track
    if src_synth:
        tracks_dom += f'<audio id="{player_id}_synth" src="{src_synth}" preload="auto"></audio>'
        controls_html += mk_track_row("Transcribe", f"{player_id}_synth", f"{player_id}_vol_synth", "#eab308") # Yellow
        js_refs += f'const t2 = document.getElementById("{player_id}_synth"); tracks.push(t2);\n'

    # 3. Vocals Track (Optional)
    if src_vocals:
        tracks_dom += f'<audio id="{player_id}_vocals" src="{src_vocals}" preload="auto"></audio>'
        controls_html += mk_track_row("Vocals", f"{player_id}_vocals", f"{player_id}_vol_vocals", "#ef4444") # Red
        js_refs += f'const t3 = document.getElementById("{player_id}_vocals"); tracks.push(t3);\n'

    # --- HTML / CSS BLOCK ---
    html = f"""
    <style>
        /* AnthemScore-ish Dark Theme */
        #{player_id}_container {{
            background-color: #2b2b2b;
            color: #ececec;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Segoe UI', sans-serif;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }}
        /* Master Controls */
        #{player_id}_master {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #444;
        }}
        .play-btn {{
            background: #eab308;
            color: #111;
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.1s;
        }}
        .play-btn:active {{ transform: scale(0.95); }}
        
        /* Seek Bar */
        .seek-container {{ flex-grow: 1; position: relative; }}
        input[type=range].master-seek {{
            width: 100%;
            cursor: pointer;
            accent-color: #eab308;
        }}
        .time-display {{ font-family: monospace; font-size: 14px; color: #aaa; min-width: 80px; text-align: right; }}

        /* Track Rows */
        .track-rows {{ display: flex; flex-direction: column; gap: 10px; }}
        .track-row {{
            display: flex;
            align-items: center;
            background: #1e1e1e;
            padding: 8px 12px;
            border-radius: 6px;
        }}
        .track-label {{
            width: 120px;
            font-weight: 600;
            font-size: 14px;
            padding-left: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .vol-slider {{
            flex-grow: 1;
            margin-left: 15px;
            height: 6px;
            cursor: pointer;
            accent-color: #3b82f6; /* Default Blue */
        }}
        /* Specific slider colors override via ID in inline styles above */
    </style>

    <div id="{player_id}_container">
        <div style="display:none;">{tracks_dom}</div>

        <div id="{player_id}_master">
            <button id="{player_id}_btn" class="play-btn">▶</button>
            <div class="seek-container">
                <input type="range" id="{player_id}_seek" class="master-seek" min="0" max="100" value="0" step="0.1">
            </div>
            <div id="{player_id}_time" class="time-display">0:00 / 0:00</div>
        </div>

        <div class="track-rows">
            {controls_html}
        </div>
    </div>

    <script>
    (function() {{
        setTimeout(() => {{
            const tracks = [];
            {js_refs}
            
            const btn = document.getElementById("{player_id}_btn");
            const seek = document.getElementById("{player_id}_seek");
            const timeDisp = document.getElementById("{player_id}_time");
            let isDragging = false;

            // Pick a master track (Original prefers, else Synth)
            const master = tracks[0]; 
            if(!master) return;

            // --- 1. Master Play/Pause ---
            btn.onclick = function() {{
                if(master.paused) {{
                    // Play all
                    tracks.forEach(t => t.play().catch(e => console.log(e)));
                    btn.innerHTML = "⏸";
                }} else {{
                    // Pause all
                    tracks.forEach(t => t.pause());
                    btn.innerHTML = "▶";
                }}
            }};

            // --- 2. Update Seek Bar & Time ---
            master.ontimeupdate = function() {{
                if(!isDragging && master.duration) {{
                    const pct = (master.currentTime / master.duration) * 100;
                    seek.value = pct;
                    
                    // Sync others just in case they drift
                    tracks.forEach(t => {{
                        if(t !== master && Math.abs(t.currentTime - master.currentTime) > 0.2) {{
                            t.currentTime = master.currentTime;
                        }}
                    }});
                }}
                
                // Update Time Text
                const cur = fmtTime(master.currentTime);
                const tot = fmtTime(master.duration || 0);
                timeDisp.innerText = cur + " / " + tot;
            }};

            // --- 3. Handle User Seeking ---
            seek.oninput = function(e) {{
                isDragging = true;
                const pct = e.target.value;
                const time = (pct / 100) * master.duration;
                tracks.forEach(t => t.currentTime = time);
            }};
            
            seek.onchange = function(e) {{
                isDragging = false;
                const pct = e.target.value;
                const time = (pct / 100) * master.duration;
                tracks.forEach(t => t.currentTime = time);
            }};

            // Helper: Format Seconds to MM:SS
            function fmtTime(s) {{
                if(isNaN(s)) return "0:00";
                const m = Math.floor(s / 60);
                const sec = Math.floor(s % 60);
                return m + ":" + (sec < 10 ? "0" : "") + sec;
            }}
            
            // Initial Volume Set
            tracks.forEach(t => t.volume = 1.0);
            
            // Mute Vocals (Track 3) by default if it exists
            if (tracks.length >= 3 && tracks[2]) {{
                 tracks[2].volume = 0.0;
                 const volSlider3 = document.getElementById("{player_id}_vol_vocals");
                 if(volSlider3) volSlider3.value = 0.0;
            }}

        }}, 500); // Small delay to ensure DOM is ready
    }})();
    </script>
    """
    return html
    
def transcribe_audio_basic_pitch(
    audio_file,
    segment_start_hint=None,
    segment_end_hint=None,
    measures_per_chunk=8,
    beats_per_measure=None,
    beats_per_minute_hint=None,
    generate_pdf=True, 
    separate_vocals=False, 
    progress=gr.Progress()
):
    """
    Transcribes audio using Spotify's Basic Pitch (Melody) + Sheet Sage (Infrastructure).
    """
    output_dir = None
    output_files_list = []
    synthesized_audio_path = None
    mixed_audio_path = None
    original_audio_segment_path = None
    target_audio_path = audio_file # Default to original
    
    # Import subprocess at top of function to avoid UnboundLocalError
    import subprocess
    import sys

    if not audio_file:
         return None, None, None, None, None, None, "Please upload an audio file."

    # Sanitize hints (Copy-pasted from Lead Sheet logic)
    # Ensure float conversion if not None
    segment_start_hint = float(segment_start_hint) if segment_start_hint is not None else None
    segment_end_hint = float(segment_end_hint) if segment_end_hint is not None else None
    
    start_val = segment_start_hint if segment_start_hint is not None else 0.0
    if segment_end_hint is not None and segment_end_hint <= start_val:
        logging.warning(f"Ignoring invalid segment_end_hint ({segment_end_hint}) <= start ({start_val})")
        segment_end_hint = None

    logging.info("Starting Basic Pitch Transcription")
    print(f"\n--- Starting Basic Pitch Transcription ---")
    try:
        from sheetsage.utils import get_approximate_audio_length
        dur = get_approximate_audio_length(audio_file)
        print(f"Detected Audio Duration: {dur:.2f} seconds")
    except Exception as e:
        print(f"Could not detect duration: {e}")
    progress(0, desc="Initializing...")

    try:
        # Demucs Separation (if enabled)
        if separate_vocals and audio_file:
            try:
                msg_demucs = "Separating vocals with Demucs (this may take a few minutes)..."
                print(msg_demucs)
                progress(0.1, desc=msg_demucs)
                
                # Create a local dir for separation
                base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
                sep_out_dir = base_output_dir / "demucs" / uuid.uuid4().hex
                sep_out_dir.mkdir(parents=True, exist_ok=True)
                
                # Run Demucs via command line
                python_exe = os.path.join("python_embeded", "python.exe") if os.path.isdir("python_embeded") else "python"
                
                cmd_args = [
                    python_exe, "-m", "demucs.separate",
                    "-n", "htdemucs", # Fast and good
                    "-o", str(sep_out_dir),
                    str(audio_file)
                ]
                print(f"Running Demucs: {' '.join(cmd_args)}")
                
                proc = subprocess.run(cmd_args, shell=False, capture_output=True, text=True)
                
                if proc.returncode != 0:
                     logging.error(f"Demucs failed: {proc.stderr}")
                     print(f"Demucs failed: {proc.stderr}")
                else:
                     # Find the vocal track
                     filename = pathlib.Path(audio_file).stem
                     # Demucs output folder structure might vary slightly but usually:
                     # htdemucs/filename/vocals.wav
                     vocals_path = sep_out_dir / "htdemucs" / filename / "vocals.wav"
                     if vocals_path.exists():
                          print(f"Using separated vocals: {vocals_path}")
                          target_audio_path = str(vocals_path)
                     else:
                          print(f"Warning: Vocals file not found at {vocals_path}")
            except Exception as e:
                logging.error(f"Demucs error: {e}")
                print(f"Demucs error: {e}")

        # Prepare output directory
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "basic_pitch"
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Cleanup filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        clean_name = pathlib.Path(audio_file).stem.replace(" ", "_").replace("(", "").replace(")", "")[:20]
        folder_name = f"{timestamp}_{clean_name}_{uuid.uuid4().hex[:6]}"
        
        output_dir = base_temp_dir / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        output_midi_path = output_dir / "basic_pitch.midi"

        # Run transcription via subprocess to avoid Gradio/Multiprocessing slowdowns
        script_path = os.path.join(os.getcwd(), "scripts", "run_bp_inference.py")
        python_exe = sys.executable
        
        cmd = [
            python_exe, script_path,
            "--audio_path", str(target_audio_path), # Use target (vocals or original)
            "--output_midi_path", str(output_midi_path),
            "--measures_per_chunk", str(measures_per_chunk)
        ]
        
        # Add optional args
        if segment_start_hint is not None:
            cmd.extend(["--segment_start_hint", str(segment_start_hint)])
        if segment_end_hint is not None:
            cmd.extend(["--segment_end_hint", str(segment_end_hint)])
        if beats_per_measure:
            cmd.extend(["--beats_per_measure_hint", str(beats_per_measure)])
        if beats_per_minute_hint:
             cmd.extend(["--beats_per_minute_hint", str(beats_per_minute_hint)])
        
        if not generate_pdf:
             cmd.append("--skip_pdf")
             
        logging.info(f"Running subprocess: {' '.join(cmd)}")
             
        logging.info(f"Running subprocess: {' '.join(cmd)}")
        print(f"Running Basic Pitch in subprocess...")
        
        import time
        import threading

        # Timer logic
        start_time = time.time()
        stop_event = threading.Event()

        def timer_loop():
            while not stop_event.is_set():
                elapsed = int(time.time() - start_time)
                if elapsed > 0 and elapsed % 2 == 0:
                     print(f"[BP Timer] Elapsed: {elapsed}s...", end='\r', flush=True)
                time.sleep(1)
        
        t_thread = threading.Thread(target=timer_loop, daemon=True)
        t_thread.start()

        # Run and capture output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8', 
            errors='replace', 
            bufsize=1,
            cwd=os.getcwd()
        )
        
        generated_files = []
        
        # Read output line by line
        last_update = 0
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                if line.startswith("STATUS:"):
                    msg = line[len("STATUS:"):].strip()
                    print(f"Subprocess: {msg}")
                    progress(None, desc=msg)
                elif line.startswith("JSON_RESULT:"):
                    json_str = line[len("JSON_RESULT:"):].strip()
                    generated_files = json.loads(json_str)
                elif line.startswith("ERROR:"):
                     logging.error(line)
                     print(line)
                else:
                     # Normal log -> Update Progress too
                     print(f"[BP]: {line}")
                     now = time.time()
                     if now - last_update > 0.5: # throttle
                         progress(None, desc=f"BP: {line[:50]}")
                         last_update = now

        stop_event.set()
        t_thread.join(timeout=1.0)

        if process.returncode != 0:
             raise Exception("Basic Pitch subprocess failed. Check console logs.")
        
        output_files_list.extend(generated_files)

        # Synthesize Audio (Standard Logic)
        # We look for the MIDI file in the returned list
        # Prioritize RAW MIDI (Polyphonic + Bends) for synthesis if available
        midi_file = next((f for f in generated_files if "raw" in pathlib.Path(f).name), None)
        if not midi_file:
             midi_file = next((f for f in generated_files if f.endswith(".midi") or f.endswith(".mid") ), None)
        
        if midi_file:
            progress(0.7, desc="Synthesizing Audio via FluidSynth...")
            print("Status: Synthesizing Audio...")
            synthesized_audio_path = synthesize_midi(midi_file, current_config["soundfont_path"], output_dir, filename="basic_pitch_synth.wav")
            if synthesized_audio_path:
                 output_files_list.append(synthesized_audio_path)

                 # Mix with original
                 progress(0.9, desc="Mixing Audio Tracks (may take a moment)...")
                 print("Status: Mixing Audio Tracks...")
                 mixed_audio_path, original_audio_segment_path = create_mix(
                      audio_file,
                      synthesized_audio_path,
                      output_dir
                 )
                 if mixed_audio_path:
                      output_files_list.append(mixed_audio_path)

        status_str = "Basic Pitch transcription finished successfully."
        
        # Generate Mixer HTML
        # Prepare Tracks
        tracks_dict = {}
        if original_audio_segment_path or audio_file:
             tracks_dict["Original"] = cache_file_for_playback(original_audio_segment_path if original_audio_segment_path else target_audio_path)
        if mixed_audio_path:
             tracks_dict["Mixed"] = cache_file_for_playback(mixed_audio_path)
        if synthesized_audio_path:
             tracks_dict["Synthesized"] = cache_file_for_playback(synthesized_audio_path)
        
        return format_player_output(output_files_list, None, tracks_dict, "Transcription successful!")

    except Exception as e:
        logging.exception("Error during basic pitch transcription")
        return format_player_output(None, None, {}, f"Error: {e}")

# Handle Rename
transcribe_audio = transcribe_audio_lead_sheet

def update_audio_player(selected_track, tracks_dict):
    if not tracks_dict or selected_track not in tracks_dict:
        return None
    return tracks_dict.get(selected_track)

def format_player_output(files, fig, tracks_dict, status):
    if not tracks_dict: tracks_dict = {}
    choices = list(tracks_dict.keys())
    # Sort choices to have Original first, then Synth, then Vocals
    def sort_key(k):
        if "Original" in k: return 0
        if "Synthesized" in k: return 1
        return 2
    choices.sort(key=sort_key)
    
    val = choices[0] if choices else None
    path = tracks_dict.get(val) if val else None
    
    return files, fig, tracks_dict, status, gr.update(choices=choices, value=val), path

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
    generate_pdf, # New argument
    progress=gr.Progress()
):
    # Validation: Check if audio input is provided
    if mode in ["Piano (Polyphonic)", "Basic Pitch (Polyphonic)", "Drums (Omnizart)"]:
        if audio_file is None:
            msg = f"Please upload an audio file for {mode}."
            gr.Warning(msg)
            return format_player_output(None, None, {}, msg)
    else: # Lead Sheet
        if audio_file is None and (audio_url is None or not audio_url.strip()):
            msg = "Please upload an audio file or provide a URL."
            gr.Warning(msg)
            return format_player_output(None, None, {}, msg)

    if mode == "Piano (Polyphonic)":
        return transcribe_audio_piano(audio_file, progress=progress)
    elif mode == "Drums (Omnizart)":
        return transcribe_audio_drums(audio_file, progress=progress)
    elif mode == "Basic Pitch (Polyphonic)":
        return transcribe_audio_basic_pitch(
            audio_file,
            segment_start_hint=segment_start_hint,
            segment_end_hint=segment_end_hint,
            measures_per_chunk=measures_per_chunk,
            beats_per_measure=beats_per_measure,
            beats_per_minute_hint=beats_per_minute_hint,
            generate_pdf=generate_pdf,
            separate_vocals=separate_vocals, 
            progress=progress
        )
    elif mode == "SheetSage V3 (Lunaverus)":
        return transcribe_audio_lunaverus(audio_file, progress=progress)
    else: # Lead Sheet (Standard)
        return transcribe_audio_lead_sheet(
            audio_file, audio_url, segment_start_hint, segment_end_hint,
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

with gr.Blocks(title="Sheet Sage") as demo:
    gr.Markdown("# 🎼 Sheet Sage")
    gr.Markdown("### Audio to Lead Sheet Transcription", elem_classes=["description"])
    
    # Global Control Buttons (Always Accessible)
    with gr.Row():
        restart_btn_global = gr.Button("🔄 Restart App", variant="secondary", scale=1)
        stop_app_btn_global = gr.Button("⛔ Stop App", variant="stop", scale=1)

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
                        ["Lead Sheet (Standard)", "Piano (Polyphonic)", "Basic Pitch (Polyphonic)", "Drums (Omnizart)", "SheetSage V3 (Lunaverus)"],
                        label="Transcription Mode",
                        value="Lead Sheet (Standard)",
                        info="Select the transcription model suitable for your audio."
                    )
                    
                    # === Shared Options Group (Visible for Lead Sheet + Basic Pitch) ===
                    with gr.Group(visible=True) as shared_options:
                        gr.Markdown("### 3. Settings")
                        with gr.Row():
                             separate_vocals = gr.Checkbox(label="Separate Vocals (Demucs)", value=True, info="Recommended for songs with vocals.")
                             generate_pdf = gr.Checkbox(label="Generate Sheet Music PDF", value=True, info="If unchecked, skips PDF formatting (Faster).")

                    # === Lead Sheet Specific (Visible ONLY for Lead Sheet) ===
                    with gr.Group(visible=True) as lead_sheet_options:
                        # gr.Markdown("(Advanced Fine-Tuning)")
                        with gr.Accordion("Fine-Tuning (Lead Sheet)", open=False):
                            with gr.Row():
                                segment_start_hint = gr.Number(
                                    label="Start Time (s)",
                                    value=None,
                                    precision=1,
                                    info="Start processing from this timestamp (in seconds)."
                                )
                                segment_end_hint = gr.Number(
                                    label="End Time (s)",
                                    value=None,
                                    precision=1,
                                    info="Stop processing at this timestamp (in seconds)."
                                )
                            
                            with gr.Row():
                                 detect_melody = gr.Checkbox(
                                     label="Detect Melody",
                                     value=True,
                                     info="Enable melody transcription."
                                 )
                                 detect_harmony = gr.Checkbox(
                                     label="Detect Harmony",
                                     value=True,
                                     info="Enable chord transcription."
                                 )
                            
                            with gr.Row():
                                melody_threshold = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    step=0.05,
                                    value=0.5,
                                    label="Melody Threshold",
                                    info="Confidence threshold for melody detection. Higher values result in fewer, more certain notes."
                                )
                                harmony_threshold = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    step=0.05,
                                    value=0.5,
                                    label="Harmony Threshold",
                                    info="Confidence threshold for chord detection."
                                )

                            with gr.Row():
                                beats_per_measure = gr.Dropdown(
                                    choices=[3, 4],
                                    label="Beats Per Measure",
                                    value=None,
                                    info="Hint for the time signature."
                                )
                                beats_per_minute_hint = gr.Number(
                                    label="BPM Hint",
                                    value=None,
                                    info="Hint for the tempo."
                                )

                            measures_per_chunk = gr.Slider(
                                minimum=1,
                                maximum=24,
                                step=1,
                                value=8,
                                label="Measures Per Chunk",
                                info="Number of measures processed at once."
                            )
                            segment_hints_are_downbeats = gr.Checkbox(
                                label="Start/End align with Downbeats",
                                value=False,
                                info="Assumes start/end times correspond to downbeats."
                            )
                            legacy_behavior = gr.Checkbox(
                                label="Legacy Behavior",
                                value=False,
                                info="Use the older alignment algorithm."
                            )

                    with gr.Row():
                         submit_btn = gr.Button("Transcribe", variant="primary", size="lg", scale=2)
                         cancel_btn = gr.Button("Cancel Task", variant="stop", scale=1)

                    with gr.Row():
                         restart_btn = gr.Button("Restart App", variant="secondary", scale=1)
                         stop_app_btn = gr.Button("Stop App", variant="secondary", scale=1)
                    
                    # Visibility Logic
                    def update_visibility(selected_mode):
                        # Shared: Visible for Lead Sheet OR Basic Pitch OR Drums
                        show_shared = (selected_mode in ["Lead Sheet (Standard)", "Basic Pitch (Polyphonic)", "Drums (Omnizart)"])
                        # Advanced: Visible ONLY for Lead Sheet
                        show_advanced = (selected_mode == "Lead Sheet (Standard)")
                        
                        return [
                            gr.update(visible=show_shared),
                            gr.update(visible=show_advanced)
                        ]
                    
                    mode.change(
                        fn=update_visibility, 
                        inputs=mode, 
                        outputs=[shared_options, lead_sheet_options]
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### Output")
                    status_msg = gr.Textbox(label="Status", interactive=False)
                    output_files = gr.Files(label="Download Results", visible=True, file_types=[ ".pdf", ".midi", ".ly", ".wav"])

                    with gr.Accordion("Preview", open=True):
                         piano_roll_plot = gr.Plot(label="Piano Roll Visualization")
                         with gr.Row():
                              transcribe_track_selector = gr.Dropdown(label="Select Track", choices=[], interactive=True, scale=1)
                              transcribe_main_player = gr.Audio(label="Audio Player", type="filepath", interactive=False, scale=3)
                         transcribe_tracks_state = gr.State({})

                    transcribe_track_selector.change(
                         fn=update_audio_player,
                         inputs=[transcribe_track_selector, transcribe_tracks_state],
                         outputs=transcribe_main_player
                    )

            submit_event = submit_btn.click(
                unified_transcriber,
                inputs=[
                    mode,
                    audio_file, audio_url, 
                    segment_start_hint, segment_end_hint, 
                    measures_per_chunk, segment_hints_are_downbeats, beats_per_measure,
                    beats_per_minute_hint, melody_threshold, harmony_threshold,
                    detect_melody, detect_harmony, legacy_behavior, separate_vocals,
                    generate_pdf
                ],
                outputs=[output_files, piano_roll_plot, transcribe_tracks_state, status_msg, transcribe_track_selector, transcribe_main_player],
            )
            cancel_btn.click(fn=None, inputs=None, outputs=None, cancels=[submit_event])
            
            def restart_app():
                import os
                import logging
                import time
                import threading
                
                def delayed_exit():
                    time.sleep(1.0) # Give the server time to respond to the client
                    logging.info("Exiting now (Exit Code 42)...")
                    os._exit(42)

                logging.info("Requesting application restart (Exit Code 42)...")
                # Start a separate thread to kill the server after a short delay
                # This prevents "Protocol Error" by allowing the current response to finish flushing
                threading.Thread(target=delayed_exit, daemon=True).start()

            restart_js = """
            () => {
                const style = document.createElement('style');
                style.innerHTML = `
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    .loader {
                        border: 8px solid #f3f3f3;
                        border-top: 8px solid #3498db;
                        border-radius: 50%;
                        width: 60px;
                        height: 60px;
                        animation: spin 2s linear infinite;
                        margin-bottom: 20px;
                    }
                `;
                document.head.appendChild(style);

                const div = document.createElement('div');
                div.style.position = 'fixed';
                div.style.top = '0';
                div.style.left = '0';
                div.style.width = '100%';
                div.style.height = '100%';
                div.style.background = 'rgba(0,0,0,0.85)';
                div.style.color = 'white';
                div.style.display = 'flex';
                div.style.flexDirection = 'column';
                div.style.justifyContent = 'center';
                div.style.alignItems = 'center';
                div.style.zIndex = '9999';
                div.style.fontFamily = 'sans-serif';
                
                div.innerHTML = `
                    <div class="loader"></div>
                    <div style="font-size: 1.5em; font-weight: bold;">Restarting Application...</div>
                    <div style="margin-top: 10px; opacity: 0.8;">The page will reload automatically when the server is ready.</div>
                `;
                
                document.body.appendChild(div);

                // Wait 5 seconds for server to shut down, then start polling
                setTimeout(() => {
                    const poll = setInterval(() => {
                        fetch('/')
                        .then(r => {
                            if(r.ok) {
                                clearInterval(poll);
                                window.location.reload();
                            }
                        })
                        .catch(e => console.log('Waiting for server...'));
                    }, 1000);
                }, 5000);
            }
            """

            stop_js = """
            () => {
                const div = document.createElement('div');
                div.style.position = 'fixed';
                div.style.top = '0';
                div.style.left = '0';
                div.style.width = '100%';
                div.style.height = '100%';
                div.style.background = 'rgba(0,0,0,0.8)';
                div.style.color = 'white';
                div.style.display = 'flex';
                div.style.justifyContent = 'center';
                div.style.alignItems = 'center';
                div.style.zIndex = '9999';
                div.style.fontSize = '2em';
                div.style.fontFamily = 'sans-serif';
                div.innerText = 'Application Stopped. You can close this tab.';
                document.body.appendChild(div);
            }
            """

            def stop_app():
                import os
                import logging
                logging.info("Stopping application...")
                # Nuclear option for Windows to ensure immediate return to shell
                os.system(f"taskkill /F /PID {os.getpid()}")

            restart_btn.click(restart_app, inputs=None, outputs=None, js=restart_js)
            stop_app_btn.click(stop_app, inputs=None, outputs=None, js=stop_js)


        # Omnizart Advanced Tab
        with gr.TabItem("Omnizart (Advanced)"):
            gr.Markdown("### Advanced Omnizart Transcription")
            gr.Markdown("Use the full capabilities of Omnizart for various transcription tasks.")
            
            with gr.Row(elem_classes=["container"]):
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Input & Settings")
                    input_omni_adv = gr.Audio(type="filepath", label="Audio File")
                    
                    mode_omni_adv = gr.Dropdown(
                        choices=["music", "chord", "drum", "vocal", "vocal-contour", "beat"],
                        value="music",
                        label="Transcription Mode",
                        info="Select the specific Omnizart model."
                    )
                    
                    omni_desc = gr.Markdown(value="**Music**: General polyphonic transcription (e.g., Piano).")
                    
                    def update_desc_fn(m):
                         descs = {
                             "music": "**Music**: General polyphonic transcription (e.g., Piano).",
                             "chord": "**Chord**: Identifies chord progressions.",
                             "drum": "**Drum**: Transcribes percussive elements.",
                             "vocal": "**Vocal**: Extracts the main vocal melody as MIDI notes.",
                             "vocal-contour": "**Vocal-contour**: Extracts detailed pitch curves.",
                             "beat": "**Beat**: Tracks beats and tempo."
                         }
                         return descs.get(m, "")
                    
                    mode_omni_adv.change(update_desc_fn, mode_omni_adv, omni_desc)
                    
                    btn_omni_adv = gr.Button("Transcribe", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                     gr.Markdown("### 2. Output")
                     status_omni_adv = gr.Textbox(label="Status", interactive=False)
                     files_omni_adv = gr.Files(label="Download Results")
                     
                     with gr.Group():
                          plot_omni_adv = gr.Plot(label="Piano Roll", visible=False) # Helper for structure
                          player_omni_adv = gr.Audio(label="Audio Player", interactive=False)
                          track_sel_omni_adv = gr.Dropdown(label="Select Track", choices=[], interactive=True)
                          tracks_state_omni_adv = gr.State({})

                     track_sel_omni_adv.change(
                          fn=update_audio_player,
                          inputs=[track_sel_omni_adv, tracks_state_omni_adv],
                          outputs=player_omni_adv
                     )

            btn_omni_adv.click(
                transcribe_audio_omnizart_advanced,
                inputs=[input_omni_adv, mode_omni_adv],
                outputs=[files_omni_adv, plot_omni_adv, tracks_state_omni_adv, status_omni_adv, track_sel_omni_adv, player_omni_adv]
            )

        # History Tab
        with gr.TabItem("History"):
            gr.Markdown("### 📂 Previous Projects")
            gr.Markdown("Select a previous transcription to reload its results (Downloads, Mixer, Piano Roll).")
            
            with gr.Row(elem_classes=["container"]):
                with gr.Column(scale=3):
                    history_dropdown = gr.Dropdown(
                        label="Project History", 
                        choices=get_history_items(),
                        interactive=True,
                        value=None
                    )
                with gr.Column(scale=1):
                    refresh_hist_btn = gr.Button("🔄 Refresh List")
                    load_hist_btn = gr.Button("📂 Load Project", variant="primary")
            
            # We can Output to the same components as Transcribe! 
            # This is great because it reuses the Preview window on the right (if we move it out of Transcribe Tab?)
            # BUT, the Output components are currently INSIDE the Transcribe Tab. 
            # Moving them OUTSIDE the tabs would make them shared.
            # OR we can duplicate them here.
            # Duplicating is safer to avoid layout breakage.
            
            with gr.Row():
                 with gr.Column():
                      hist_status = gr.Textbox(label="Status", interactive=False)
                      hist_files = gr.Files(label="Download Results")
                 with gr.Column():
                      hist_plot = gr.Plot(label="Piano Roll")
                      with gr.Row():
                           hist_track_selector = gr.Dropdown(label="Select Track", choices=[], interactive=True, scale=1)
                           hist_main_player = gr.Audio(label="Audio Player", type="filepath", interactive=False, scale=3)
                      hist_tracks_state = gr.State({})

            hist_track_selector.change(
                 fn=update_audio_player,
                 inputs=[hist_track_selector, hist_tracks_state],
                 outputs=hist_main_player
            )
            
            def refresh_history():
                return gr.update(choices=get_history_items())
            
            refresh_hist_btn.click(fn=refresh_history, outputs=history_dropdown)
            
            load_hist_btn.click(
                fn=load_history_project,
                inputs=[history_dropdown],
                outputs=[hist_files, hist_plot, hist_tracks_state, hist_status, hist_track_selector, hist_main_player]
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

    # Wire up global control buttons (reuse functions from Transcribe tab)
    restart_btn_global.click(restart_app, inputs=None, outputs=None, js=restart_js)
    stop_app_btn_global.click(stop_app, inputs=None, outputs=None, js=stop_js)

    gr.Markdown("Built with Sheetsage", elem_classes=["footer"])

if __name__ == "__main__":
    # Ensure allowed_paths captures D:\Document\sheetsage\output correctly
    # We add current working directory and the specific output folder to allow lists
    allowed = [
        os.getcwd(), 
        os.path.join(os.getcwd(), "output"),
        os.path.join(os.getcwd(), "temp_playback"),  # Explicitly allow cached audio
        "D:\\", 
        "C:\\"
    ]
    if current_config.get("output_dir"):
         allowed.append(current_config.get("output_dir"))
         
    demo.queue(max_size=5)
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=False,
        allowed_paths=allowed
    )
