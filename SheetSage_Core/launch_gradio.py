import os
import sys
import shutil
import tempfile
import logging
import asyncio
import platform

# Fix for "ConnectionResetError: [WinError 10054]" on Windows
# This is a benign error caused by the ProactorEventLoop when clients disconnect abruptly.
# Switching to SelectorEventLoopPolicy avoids this specific noise.
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Force temp directory to be local to the project
local_temp_dir = os.path.join(os.getcwd(), "temp")
os.makedirs(local_temp_dir, exist_ok=True)
os.environ["TEMP"] = local_temp_dir
os.environ["TMP"] = local_temp_dir
os.environ["TMPDIR"] = local_temp_dir
os.environ["SHEETSAGE_TEMP"] = local_temp_dir
tempfile.tempdir = local_temp_dir
print(f"Set temporary directory to: {local_temp_dir}")

try:
    import numpy as np
    if not hasattr(np, 'long') and not hasattr(np, 'int'):
        np.long = int
        print("Patched np.long for numba compatibility")
except ImportError:
    pass

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

# Ensure we can find the sheetsage package
sys.path.append(os.getcwd())

# Set Hugging Face and Torch cache to local directory for portability
os.environ['HF_HOME'] = os.path.join(os.getcwd(), 'cache', 'huggingface')
os.environ['TORCH_HOME'] = os.path.join(os.getcwd(), 'cache', 'torch')

# Configuration for Audio Synthesis (Fluidsynth)
bin_dir = os.path.join(os.getcwd(), "bin")
if os.path.isdir(bin_dir):
    # Add to DLL search path (Python 3.8+ Windows)
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(bin_dir)
            print(f"Added {bin_dir} to DLL search path")
        except Exception as e:
            print(f"Failed to add DLL directory: {e}")
            
    # Add to PATH
    os.environ["PATH"] += os.pathsep + bin_dir
    
    # Ensure libfluidsynth.dll exists (copy from libfluidsynth-3.dll if needed)
    fs_dll_v3 = os.path.join(bin_dir, "libfluidsynth-3.dll")
    fs_dll_generic = os.path.join(bin_dir, "libfluidsynth.dll")
    if os.path.exists(fs_dll_v3) and not os.path.exists(fs_dll_generic):
        try:
            shutil.copy2(fs_dll_v3, fs_dll_generic)
            print(f"Copied {fs_dll_v3} to {fs_dll_generic} for compatibility")
        except Exception as e:
            print(f"Failed to copy libfluidsynth DLL: {e}")

from sheetsage.gradio_app import demo, css


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser on startup")
    args, unknown = parser.parse_known_args()

    print("Launching Sheet Sage Gradio Interface...")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"Hardware Detected: GPU ({gpu_name})")
            print("Instruction: Will use GPU for inference where supported.")
        else:
            print("Hardware Detected: CPU Only")
            print("Instruction: Will use CPU for inference.")
    except ImportError:
        print("Warning: Torch not found. Hardware detection failed.")

    print("Access the interface at http://127.0.0.1:7860")
    # Determine drive root (e.g., D:\) to allow absolute path access
    drive_root = os.path.splitdrive(os.getcwd())[0] + os.sep
    
    demo.queue().launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=not args.no_browser,
        allowed_paths=[
            ".", 
            os.getcwd(), 
            os.path.join(os.getcwd(), "temp_playback"),
            drive_root, 
            drive_root.replace("\\", "/"),
            "C:\\", "C:/", "D:\\", "D:/"
        ],
        css=css
    )
