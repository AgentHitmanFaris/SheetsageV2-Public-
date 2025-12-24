import os
import shutil

root_libs = r"D:\Document\atoscore\atoscore_Core\cuda_libs"
required_dlls = [
    "cublas64_11.dll",
    "cublasLt64_11.dll", 
    "cufft64_10.dll",
    "curand64_10.dll",
    "cusolver64_11.dll",
    "cusparse64_11.dll",
    "cudnn64_8.dll"
]

# Search recursively for these files in cuda_libs and move them to root
found_count = 0
for dp, dn, filenames in os.walk(root_libs):
    if dp == root_libs: continue # Skip root
    
    for f in filenames:
        if f in required_dlls:
            src = os.path.join(dp, f)
            dst = os.path.join(root_libs, f)
            if not os.path.exists(dst):
                print(f"Moving {f} to root...")
                shutil.move(src, dst)
                found_count += 1
            else:
                print(f"{f} already in root.")

print(f"Moved {found_count} files.")

# Verify
missing = []
for dll in required_dlls + ["cudart64_110.dll"]:
    if not os.path.exists(os.path.join(root_libs, dll)):
        missing.append(dll)

if missing:
    print(f"MISSING: {missing}")
else:
    print("SUCCESS: All DLLs present.")

