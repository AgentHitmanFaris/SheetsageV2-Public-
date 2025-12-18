import json
import os
import logging
import pathlib
import uuid
import tempfile
import urllib.parse
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
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "piano"
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

        # Generator Mixer HTML
        html_player = generate_mixer_html(
             orig_path=audio_file,
             synth_path=synthesized_audio_path
        )

        return output_files_list, None, html_player, "Transcription successful!"

    except Exception as e:
        logging.exception("Error during piano transcription")
        return None, None, None, f"Error: {str(e)}"

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
                base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
                sep_out_dir = base_output_dir / "demucs" / uuid.uuid4().hex
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
        msg_model = "Model: SheetSage (Standard)"
        
        logging.info(msg_hw)
        logging.info(msg_model)
        print(f"\n--- Starting Lead Sheet Transcription ---")
        print(msg_hw)
        print(msg_model)
        
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
        base_output_dir = pathlib.Path(current_config.get("output_dir", os.path.join(os.getcwd(), "output")))
        base_temp_dir = base_output_dir / "leadsheet"
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

        # Generator Mixer HTML
        html_player = generate_mixer_html(
             orig_path=audio_path_or_url,
             synth_path=synthesized_audio_path,
             vocals_path=demucs_vocals_path
        )
        
        status = "Transcription successful!"
        if not any(f.endswith(".pdf") for f in output_files_list):
             status += " (PDF failed)"

        return output_files_list, fig, html_player, status

    except Exception as e:
        logging.exception("Error during transcription")
        return None, None, None, f"Error: {str(e)}"

def generate_mixer_html(orig_path, synth_path, vocals_path=None):
    """
    Generates a custom HTML5 Audio Mixer for playing tracks in sync.
    """
    import uuid
    import json
    player_id = f"mixer_{uuid.uuid4().hex[:8]}"
    
    def make_src(path):
        if not path: return ""
        s = str(path)
        if s.startswith("http") or s.startswith("data:"): return s
        # Local file: Normalize and Encode
        s = s.replace("\\", "/")
        encoded = urllib.parse.quote(s)
        return f"/gradio_api/file={encoded}"

    src_orig = make_src(orig_path)
    src_synth = make_src(synth_path)
    src_vocals = make_src(vocals_path)
    
    tracks_html = ""
    controls_html = ""
    js_refs = ""
    
    # Track 1: Original
    if src_orig:
        tracks_html += f'<audio id="{player_id}_orig" src="{src_orig}" preload="auto"></audio>'
        controls_html += f"""
        <div style="margin-bottom: 10px; display: flex; align-items: center;">
            <span style="width: 80px; font-weight: bold;">Original</span>
            <input type="range" id="{player_id}_vol_orig" min="0" max="1" step="0.01" value="0.6" style="flex-grow: 1; margin: 0 10px;">
        </div>
        """
        js_refs += f'const aOrig = document.getElementById("{player_id}_orig");\n'
    else:
        js_refs += 'const aOrig = null;\n'

    # Track 2: Synth
    if src_synth:
        tracks_html += f'<audio id="{player_id}_synth" src="{src_synth}" preload="auto"></audio>'
        controls_html += f"""
        <div style="margin-bottom: 10px; display: flex; align-items: center;">
            <span style="width: 80px; font-weight: bold;">Synth</span>
            <input type="range" id="{player_id}_vol_synth" min="0" max="1" step="0.01" value="0.8" style="flex-grow: 1; margin: 0 10px;">
        </div>
        """
        js_refs += f'const aSynth = document.getElementById("{player_id}_synth");\n'
    else:
        js_refs += 'const aSynth = null;\n'

    # Track 3: Vocals (Optional)
    if src_vocals:
        tracks_html += f'<audio id="{player_id}_vocals" src="{src_vocals}" preload="auto"></audio>'
        controls_html += f"""
        <div style="margin-bottom: 10px; display: flex; align-items: center;">
            <span style="width: 80px; font-weight: bold;">Vocals</span>
            <input type="range" id="{player_id}_vol_vocals" min="0" max="1" step="0.01" value="0.0" style="flex-grow: 1; margin: 0 10px;">
        </div>
        """
        js_refs += f'const aVocals = document.getElementById("{player_id}_vocals");\n'
    else:
        js_refs += 'const aVocals = null;\n'

    html = f"""
    <div style="border: 1px solid #cbd5e0; padding: 15px; border-radius: 8px; background: #e2e8f0; color: #1a202c;">
        {tracks_html}
        
        <div style="display: flex; gap: 10px; margin-bottom: 15px; align-items: center;">
            <button id="{player_id}_btn" onclick="{player_id}_toggle()" style="padding: 10px 20px; font-size: 16px; font-weight: bold; cursor: pointer; background: #3182ce; color: white; border: none; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">▶ Play</button>
            <div style="flex-grow: 1; display: flex; align-items: center;">
                 <input type="range" id="{player_id}_seek" min="0" max="100" value="0" style="width: 100%; cursor: pointer;">
            </div>
        </div>

        {controls_html}
    </div>

    <script>
    (function() {{
        setTimeout(function() {{
            {js_refs}
            const btn = document.getElementById("{player_id}_btn");
            const slider = document.getElementById("{player_id}_seek");
            
            // Volume Handlers
            if(aOrig && document.getElementById("{player_id}_vol_orig")) document.getElementById("{player_id}_vol_orig").oninput = (e) => aOrig.volume = e.target.value;
            if(aSynth && document.getElementById("{player_id}_vol_synth")) document.getElementById("{player_id}_vol_synth").oninput = (e) => aSynth.volume = e.target.value;
            if(aVocals && document.getElementById("{player_id}_vol_vocals")) document.getElementById("{player_id}_vol_vocals").oninput = (e) => aVocals.volume = e.target.value;

            // Master Controller (Use Original as timing master if avail, else Synth)
            const master = aOrig || aSynth || aVocals;
            const slaves = [aOrig, aSynth, aVocals].filter(a => a && a !== master);

            if (master) {{
                // Slider Update
                master.ontimeupdate = () => {{
                    if(master.duration && !Number.isNaN(master.duration)) slider.value = (master.currentTime / master.duration) * 100;
                }};
                
                // Seek Handler
                slider.oninput = (e) => {{
                    if(master.duration) {{
                        const t = (e.target.value / 100) * master.duration;
                        master.currentTime = t;
                        slaves.forEach(s => s.currentTime = t);
                    }}
                }};
                
                // Sync on seek
                master.onseeked = () => {{
                     slaves.forEach(s => s.currentTime = master.currentTime);
                }};
                
                // Play Toggle
                window["{player_id}_toggle"] = function() {{
                    if (master.paused) {{
                        master.play().then(() => {{
                             slaves.forEach(s => s.play().catch(e => console.log("Slave play error", e))); 
                        }}).catch(e => console.error("Play failed", e));
                        btn.innerText = "⏸ Pause";
                    }} else {{
                        master.pause();
                        slaves.forEach(s => s.pause());
                        btn.innerText = "▶ Play";
                    }}
                }};
            }}
        }}, 500);
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
        output_dir = base_temp_dir / uuid.uuid4().hex
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
        
        # Run and capture output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8', # Force UTF-8 reading
            errors='replace', # Prevent crashing on bad chars
            bufsize=1,
            cwd=os.getcwd()
        )
        
        generated_files = []
        
        # Read output line by line
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
                     # Normal log
                     print(f"[BP]: {line}")

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

        status_str = "Basic Pitch transcription finished successfully."
        
        # Generate Mixer HTML
        vocals_track = target_audio_path if separate_vocals else None
        
        html_player = generate_mixer_html(
            orig_path=audio_file,
            synth_path=synthesized_audio_path,
            vocals_path=vocals_track
        )

        return output_files_list, None, html_player, status_str

    except Exception as e:
        logging.exception("Error during basic pitch transcription")
        return None, None, None, f"Error: {str(e)}"

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
    generate_pdf, # New argument
    progress=gr.Progress()
):
    if mode == "Piano (Polyphonic)":
        return transcribe_audio_piano(audio_file, progress=progress)
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
                        # Shared: Visible for Lead Sheet OR Basic Pitch
                        show_shared = (selected_mode in ["Lead Sheet (Standard)", "Basic Pitch (Polyphonic)"])
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
                         html_player = gr.HTML(label="Multi-Track Mixer")

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
                outputs=[output_files, piano_roll_plot, html_player, status_msg],
            )
            cancel_btn.click(fn=None, inputs=None, outputs=None, cancels=[submit_event])
            
            def restart_app():
                import sys
                import os
                import subprocess
                import platform
                logging.info("Restarting application...")
                
                # Prepare command
                startup_script = os.path.join(os.getcwd(), "run_local.bat")
                if os.path.exists(startup_script):
                    # Use cmd /c to run the batch file properly without shell=True if needed, 
                    # but shell=True is simpler for batch files. 
                    # We use CREATE_NEW_CONSOLE to detach.
                    cmd = [startup_script, "--no-browser"]
                    shell_cmd = True
                else:
                    cmd = [sys.executable] + sys.argv + ["--no-browser"]
                    shell_cmd = False
                
                # Spawn new process
                # CREATE_NEW_CONSOLE (0x10) ensures it starts in a new window/process group on Windows
                # close_fds=True ensures no file handles (pipes) are inherited, allowing the parent to exit fully
                creation_flags = 0x00000010 if platform.system() == "Windows" else 0
                
                subprocess.Popen(
                    cmd, 
                    shell=shell_cmd, 
                    cwd=os.getcwd(), 
                    creationflags=creation_flags,
                    close_fds=True
                )
                
                # Exit the current process immediately
                os._exit(0)

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
