
import os
import sys
import logging
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Patch os.add_dll_directory to avoid crashes in dependencies (like pyfluidsynth)
if hasattr(os, 'add_dll_directory'):
    _original_add_dll_directory = os.add_dll_directory
    def _patched_add_dll_directory(path):
        try:
            return _original_add_dll_directory(path)
        except OSError as e:
            print(f"Warning: Suppressed error adding DLL directory '{path}': {e}")
            return None
    os.add_dll_directory = _patched_add_dll_directory

# Point to local cache directory so it finds the assets the user downloaded
local_cache = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".atoscore"))
os.environ["atoscore_CACHE_DIR"] = local_cache
print(f"Set cache dir to: {local_cache}")

import onnxruntime as ort
print("ONNX Runtime Providers:", ort.get_available_providers())

from atoscore.basic_pitch_transcription import transcribe_basic_pitch

audio_path = r"D:\Download\Music\BABYMONSTER - PSYCHO MV.mp3"
output_midi_path = r"D:\Document\atoscore\output\debug_test.mid"

# Create output dir if not exists
os.makedirs(os.path.dirname(output_midi_path), exist_ok=True)

if not os.path.exists(audio_path):
    print(f"Error: File not found: {audio_path}")
    # Try to find it or ask user? 
    # For now let's see if this fails.
    pass

print(f"Processing {audio_path}...")
start_time = time.time()

try:
    # Use transcribe_basic_pitch which calls predict_and_save
    # We want to see if it uses GPU.
    # The function inside sets os.environ["BASIC_PITCH_USE_ONNX"] = "1"
    

    # Use transcribe_basic_pitch to verify full pipeline (Sheet Sage + Basic Pitch)
    
    print("\n--- Running Full Pipeline (transcribe_basic_pitch) ---")
    results = transcribe_basic_pitch(
        audio_path=audio_path,
        output_midi_path=output_midi_path,
        status_callback=print
    )
    print("Results:", results)

    # Inspect the output MIDI for pitch bends
    raw_midi_path = output_midi_path
            
    if os.path.exists(raw_midi_path):
        print(f"Inspecting MIDI: {raw_midi_path}")
        try:
            import pretty_midi
            pm = pretty_midi.PrettyMIDI(raw_midi_path)
            total_bends = 0
            for inst in pm.instruments:
                print(f"Instrument {inst.program}: {len(inst.notes)} notes, {len(inst.pitch_bends)} pitch bends")
                total_bends += len(inst.pitch_bends)
            
            if total_bends > 0:
                print(f"SUCCESS: Detected {total_bends} pitch bends! Pitch bending detection is WORKING.")
            else:
                print("WARNING: No pitch bends detected. Check if the model supports it or if the song has bends.")
        except Exception as e:
            print(f"Failed to inspect MIDI: {e}")
    else:
        print("WARNING: No raw MIDI output found.")
    
except Exception as e:
    print("An error occurred:", e)
    import traceback
    traceback.print_exc()

end_time = time.time()
print(f"Total time: {end_time - start_time:.2f} seconds")

