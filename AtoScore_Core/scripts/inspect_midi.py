
import os
import sys

# Patch os.add_dll_directory to avoid crashes in dependencies (like pyfluidsynth)
if hasattr(os, 'add_dll_directory'):
    _original_add_dll_directory = os.add_dll_directory
    def _patched_add_dll_directory(path):
        try:
            return _original_add_dll_directory(path)
        except OSError as e:
            # print(f"Warning: Suppressed error adding DLL directory '{path}': {e}")
            return None
    os.add_dll_directory = _patched_add_dll_directory

import pretty_midi

midi_path = r"D:\Document\sheetsage\output\debug_test.mid"

if os.path.exists(midi_path):
    print(f"Inspecting MIDI: {midi_path}")
    try:
        pm = pretty_midi.PrettyMIDI(midi_path)
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
    print(f"Error: MIDI file not found at {midi_path}")
