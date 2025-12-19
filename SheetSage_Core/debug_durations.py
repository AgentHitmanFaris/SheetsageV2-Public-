import os
import glob

# Patch for fluidsynth hardcoded path error
if os.name == 'nt' and hasattr(os, 'add_dll_directory'):
    _orig = os.add_dll_directory
    def _patched(path):
        try:
            return _orig(path)
        except OSError:
            return None
    os.add_dll_directory = _patched

import librosa
import pretty_midi
import pathlib

def find_latest_file(pattern):
    files = glob.glob(pattern, recursive=True)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def check_durations():
    print("--- Debugging Durations ---")
    
    # Check Vocals (WAV)
    vocals_pattern = os.path.join("output", "demucs", "**", "vocals.wav")
    latest_vocals = find_latest_file(vocals_pattern)
    
    if latest_vocals:
        print(f"Latest Vocals: {latest_vocals}")
        print(f"Size: {os.path.getsize(latest_vocals)} bytes")
        try:
            y, sr = librosa.load(latest_vocals, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            print(f"Librosa Duration: {duration:.2f} seconds")
        except Exception as e:
            print(f"Librosa Load Failed: {e}")
    else:
        print("No vocals.wav found.")

    # Check MIDI
    midi_pattern = os.path.join("output", "basic_pitch", "**", "basic_pitch_raw.midi")
    latest_midi = find_latest_file(midi_pattern)
    
    if latest_midi:
        print(f"\nLatest MIDI: {latest_midi}")
        try:
            pm = pretty_midi.PrettyMIDI(latest_midi)
            print(f"MIDI End Time: {pm.get_end_time():.2f} seconds")
            print(f"Total Notes: {sum(len(i.notes) for i in pm.instruments)}")
        except Exception as e:
             print(f"MIDI Parse Failed: {e}")
    else:
        print("No basic_pitch_raw.midi found.")

if __name__ == "__main__":
    check_durations()
