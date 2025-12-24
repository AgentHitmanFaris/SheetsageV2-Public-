import os
import ctypes
import sys

bin_dir = os.path.join(os.getcwd(), "bin")
dll_path = os.path.join(bin_dir, "libfluidsynth-3.dll")

print(f"Testing DLL load from: {dll_path}")

if hasattr(os, 'add_dll_directory'):
    print("Adding DLL directory...")
    os.add_dll_directory(bin_dir)

try:
    lib = ctypes.CDLL(dll_path)
    print("Successfully loaded DLL via ctypes.")
except Exception as e:
    print(f"Failed to load DLL: {e}")

try:
    import fluidsynth
    print("Fluidsynth import success")
except Exception as e:
    print(f"Fluidsynth import fail: {e}")
