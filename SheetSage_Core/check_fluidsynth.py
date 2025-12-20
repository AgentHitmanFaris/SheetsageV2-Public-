import os
import sys

# Add bin to DLL search path (mimic launch_gradio.py)
bin_dir = os.path.join(os.getcwd(), "bin")
if os.path.exists(bin_dir):
    try:
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(bin_dir)
        os.environ["PATH"] += os.pathsep + bin_dir
        print(f"Added {bin_dir} to DLL path")
    except Exception as e:
        print(f"Failed to add DLL dir: {e}")

try:
    import fluidsynth
    print(f"Fluidsynth imported successfully. Version: {fluidsynth.__version__ if hasattr(fluidsynth, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"Fluidsynth import failed: {e}")
    exit(1)
except Exception as e:
    print(f"Fluidsynth check failed: {e}")
    exit(1)
