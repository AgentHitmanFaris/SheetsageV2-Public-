"""
Automatic CUDA 11.2.2 Runtime Installer for Omnizart
Downloads and installs only the required runtime DLLs to cuda_libs folder.
"""
import os
import urllib.request
import zipfile
import pathlib
import shutil

def download_file(url, dest_path):
    """Download file with progress indicator."""
    print(f"Downloading: {url}")
    print(f"Destination: {dest_path}")
    
    def reporthook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        print(f"\rProgress: {percent}%", end='', flush=True)
    
    urllib.request.urlretrieve(url, dest_path, reporthook)
    print("\n✓ Download complete!")

def install_cuda_runtime():
    """
    Install CUDA 11.2.2 runtime DLLs to cuda_libs folder.
    """
    print("="*60)
    print("CUDA 11.2.2 Runtime Installer for Omnizart")
    print("="*60)
    
    # Define target directory
    cuda_libs_dir = pathlib.Path(__file__).parent / "cuda_libs"
    cuda_libs_dir.mkdir(exist_ok=True)
    
    # CUDA 11.2.2 runtime redistributable URLs (from NVIDIA official CDN)
    cuda_runtime_url = "https://developer.download.nvidia.com/compute/cuda/redist/cuda_cudart/windows-x86_64/cuda_cudart-windows-x86_64-11.2.152-archive.zip"
    
    temp_dir = pathlib.Path(__file__).parent / "temp_cuda_download"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Download CUDA runtime
        zip_path = temp_dir / "cuda_runtime.zip"
        print("\n[1/3] Downloading CUDA 11.2.2 Runtime...")
        download_file(cuda_runtime_url, zip_path)
        
        # Extract
        print("\n[2/3] Extracting archive...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        print("✓ Extraction complete!")
        
        # Find and copy DLLs
        print("\n[3/3] Installing DLLs to cuda_libs...")
        dll_found = False
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.dll'):
                    src = os.path.join(root, file)
                    dest = cuda_libs_dir / file
                    shutil.copy2(src, dest)
                    print(f"  ✓ Installed: {file}")
                    dll_found = True
        
        if not dll_found:
            print("⚠ Warning: No DLL files found in downloaded archive.")
            return False
        
        # Verify installation
        print("\n" + "="*60)
        print("Installation Summary")
        print("="*60)
        print(f"Target directory: {cuda_libs_dir}")
        print("\nInstalled DLLs:")
        for dll in sorted(cuda_libs_dir.glob("*.dll")):
            size_mb = dll.stat().st_size / (1024*1024)
            print(f"  • {dll.name} ({size_mb:.2f} MB)")
        
        # Check for required DLLs
        required_dlls = ['cudart64_112.dll', 'cudnn64_8.dll', 'zlibwapi.dll']
        missing = [dll for dll in required_dlls if not (cuda_libs_dir / dll).exists()]
        
        if missing:
            print(f"\n⚠ Missing required DLLs: {', '.join(missing)}")
            if 'cudart64_112.dll' in missing:
                print("\n  The downloaded archive may have a different structure.")
                print("  Please check the temp_cuda_download folder manually.")
        else:
            print("\n✓ All required DLLs present!")
        
        print("\n" + "="*60)
        print("Next Steps:")
        print("1. Restart the atoscore application")
        print("2. Omnizart will automatically use GPU acceleration")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            print("\nCleaning up temporary files...")
            shutil.rmtree(temp_dir)
            print("✓ Cleanup complete!")
        except:
            pass

if __name__ == "__main__":
    try:
        success = install_cuda_runtime()
        if success:
            print("\n✓ Installation successful!")
        else:
            print("\n✗ Installation failed. Please install CUDA 11.2 manually.")
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
    except Exception as e:
        print(f"\nFatal error: {e}")
    
    input("\nPress Enter to close...")

