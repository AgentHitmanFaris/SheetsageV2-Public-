"""
Helper script to copy cuDNN 8.1 DLLs to cuda_libs folder.
Run this after extracting cuDNN zip file.
"""
import os
import shutil
import pathlib

def install_cudnn():
    print("cuDNN 8.1.1 Installation Helper")
    print("================================\n")
    
    # Get cuDNN extraction path from user
    cudnn_path = input("Enter the path where you extracted cuDNN (e.g., C:\\cudnn-11.2-windows-x64-v8.1.1.33): ").strip('"')
    
    if not os.path.exists(cudnn_path):
        print(f"Error: Path does not exist: {cudnn_path}")
        return
    
    cudnn_bin = os.path.join(cudnn_path, "bin")
    if not os.path.exists(cudnn_bin):
        print(f"Error: 'bin' folder not found in {cudnn_path}")
        print("Please verify you extracted the cuDNN zip correctly.")
        return
    
    # Target directory
    cuda_libs_dir = pathlib.Path(__file__).parent / "cuda_libs"
    cuda_libs_dir.mkdir(exist_ok=True)
    
    # Find and copy all DLLs
    dll_files = list(pathlib.Path(cudnn_bin).glob("*.dll"))
    
    if not dll_files:
        print(f"Error: No DLL files found in {cudnn_bin}")
        return
    
    print(f"\nFound {len(dll_files)} DLL file(s) in cuDNN bin folder:")
    for dll in dll_files:
        print(f"  - {dll.name}")
    
    print(f"\nCopying to: {cuda_libs_dir}")
    
    copied = 0
    for dll in dll_files:
        dest = cuda_libs_dir / dll.name
        try:
            shutil.copy2(dll, dest)
            print(f"  ✓ Copied {dll.name}")
            copied += 1
        except Exception as e:
            print(f"  ✗ Failed to copy {dll.name}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Successfully copied {copied}/{len(dll_files)} files!")
    print("\nNext steps:")
    print("1. Verify CUDA 11.2 is installed in: C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.2")
    print("2. Restart the SheetSage application")
    print("3. Omnizart will now use GPU acceleration!")

if __name__ == "__main__":
    try:
        install_cudnn()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")
    except Exception as e:
        print(f"\nError: {e}")
    
    input("\nPress Enter to close...")
