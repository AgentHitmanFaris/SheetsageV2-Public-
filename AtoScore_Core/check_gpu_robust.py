import os
import sys

# Inject the cuda_libs path directly into the process PATH / DLL directory search
cuda_libs = r"D:\Document\atoscore\atoscore_Core\cuda_libs"
os.environ["PATH"] = cuda_libs + ";" + os.environ["PATH"]

# Also try the Python 3.8+ specific DLL loading mechanism
try:
    os.add_dll_directory(cuda_libs)
    print(f"Added DLL directory: {cuda_libs}")
except AttributeError:
    pass # Python < 3.8
except Exception as e:
    print(f"Failed to add DLL directory: {e}")

print("Testing TensorFlow GPU detection...")
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
print(f"Num GPUs Available: {len(gpus)}")
if len(gpus) > 0:
    for gpu in gpus:
        print(f" - {gpu}")
else:
    print("No GPUs found. Troubleshooting info:")
    # Try initializing a CUDA lib explicitly
    try:
        from ctypes import cdll
        cdll.LoadLibrary(os.path.join(cuda_libs, "cudart64_110.dll"))
        print(" - Successfully loaded cudart64_110.dll manually (Library is accessible)")
    except Exception as e:
        print(f" - Failed to load cudart64_110.dll manually: {e}")


