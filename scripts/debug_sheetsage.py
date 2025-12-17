
import os
import sys
import logging
import time


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

# Update cache dir
local_cache = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".sheetsage"))
os.environ["SHEETSAGE_CACHE_DIR"] = local_cache

logging.basicConfig(level=logging.INFO)

from sheetsage.infer import sheetsage

audio_path = r"D:\Download\Music\BABYMONSTER - PSYCHO MV.mp3"

print("Running Sheet Sage Infrastructure Test...")
start_time = time.time()
try:
    # Use same params as in code (detect_harmony=True, detect_melody=False)
    ss_result = sheetsage(
        audio_path_bytes_or_url=audio_path,
        detect_melody=False,
        detect_harmony=True,
        tqdm=lambda x: x # Disable tqdm prints
    )
    print("Sheet Sage finished successfully.")
    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds")
except Exception as e:
    print(f"Sheet Sage failed: {e}")
    import traceback
    traceback.print_exc()

