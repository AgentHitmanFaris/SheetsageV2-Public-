import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scipy.io.wavfile import read as wavread
from sheetsage.assets import retrieve_asset
from sheetsage.beat_track import beatnet_beat_track

def test_beatnet():
    try:
        asset_path = retrieve_asset("TEST_WAV")
        print(f"Asset Path: {asset_path}")
        if not os.path.exists(asset_path):
            print("TEST_WAV asset not found.")
            return

        sr, wav = wavread(asset_path)
        print(f"Loaded WAV: sr={sr}, shape={wav.shape}, dtype={wav.dtype}")
        
        print("Running BeatNet (Expecting SUCCESS with Madmom)...")
        first_downbeat, beats_per_bar, beats = beatnet_beat_track(sr, wav)
        
        print("--- Results ---")
        print(f"First Downbeat Index: {first_downbeat}")
        print(f"Beats Per Bar: {beats_per_bar}")
        print(f"Detected Beats ({len(beats)}): {beats}")
        
        if len(beats) > 0:
            print("SUCCESS: Beats detected.")
        else:
            print("FAILURE: No beats returned.")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_beatnet()
