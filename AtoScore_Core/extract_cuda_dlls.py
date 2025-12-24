"""
Extract CUDA 11.2 Runtime DLLs from installer archive
Replaces outdated CUDA 11.0 DLLs in cuda_libs folder
"""
import os
import shutil
import pathlib
import subprocess
import sys

def extract_cuda_dlls():
    print("="*70)
    print("CUDA 11.2.2 Runtime DLL Extractor")
    print("="*70)
    
    # Paths
    cuda_libs = pathlib.Path(__file__).parent / "cuda_libs"
    cuda_libs.mkdir(exist_ok=True)
    
    # Ask user for CUDA installer location
    print("\nPlease provide the path to your CUDA 11.2.2 installer:")
    print("(Or press Enter if it's in Downloads)")
    
    user_path = input("\nPath: ").strip('"')
    
    if not user_path:
        # Check common locations
        downloads = pathlib.Path.home() / "Downloads"
        candidates = list(downloads.glob("cuda_11.2.2*.exe"))
        if candidates:
            installer_path = candidates[0]
            print(f"\nFound installer: {installer_path}")
        else:
            print("\n✗ CUDA installer not found in Downloads folder.")
            print("Please specify the full path to the installer.")
            return False
    else:
        installer_path = pathlib.Path(user_path)
        if not installer_path.exists():
            print(f"\n✗ File not found: {installer_path}")
            return False
    
    # Create temp extraction directory
    temp_dir = pathlib.Path(__file__).parent / "temp_cuda_extract"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        print(f"\n[1/3] Extracting CUDA installer archive...")
        print(f"Source: {installer_path}")
        print(f"Temp dir: {temp_dir}")
        
        # Use 7-Zip (if available) or built-in extractor
        seven_zip = r"C:\Program Files\7-Zip\7z.exe"
        
        if pathlib.Path(seven_zip).exists():
            print("Using 7-Zip...")
            cmd = [seven_zip, "x", str(installer_path), f"-o{temp_dir}", "-y"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"7-Zip error: {result.stderr}")
                return False
        else:
            print("✗ 7-Zip not found. Please install 7-Zip or extract manually.")
            print("\nManual steps:")
            print("1. Right-click the CUDA installer → 7-Zip → Extract Here")
            print("2. Navigate to: cuda_cudart\\cudart\\bin")
            print("3. Copy cudart64_110.dll to:", cuda_libs)
            return False
        
        print("✓ Extraction complete!")
        
        # Find and copy runtime DLLs
        print("\n[2/3] Locating runtime DLLs...")
        
        # Expected paths in extracted archive
        search_patterns = [
            "cuda_cudart/cudart/bin/cudart64_110.dll",
            "cuda_cudart\\cudart\\bin\\cudart64_110.dll",
            "**/cudart64_110.dll"
        ]
        
        dll_found = None
        for pattern in search_patterns:
            matches = list(temp_dir.glob(pattern))
            if matches:
                dll_found = matches[0]
                break
        
        if not dll_found:
            print("✗ cudart64_110.dll not found in extracted files.")
            print("\nSearching all DLLs in temp folder...")
            all_dlls = list(temp_dir.rglob("*.dll"))
            if all_dlls:
                print(f"Found {len(all_dlls)} DLL files:")
                for dll in all_dlls[:10]:  # Show first 10
                    print(f"  • {dll.relative_to(temp_dir)}")
            return False
        
        print(f"✓ Found: {dll_found.relative_to(temp_dir)}")
        
        # Verify DLL
        dll_size = dll_found.stat().st_size
        print(f"  Size: {dll_size:,} bytes ({dll_size/1024:.1f} KB)")
        
        # Copy to cuda_libs
        print(f"\n[3/3] Installing to cuda_libs...")
        
        dest = cuda_libs / dll_found.name
        
        # Backup old DLL if exists
        if dest.exists():
            backup = cuda_libs / f"{dest.stem}_old{dest.suffix}"
            shutil.move(str(dest), str(backup))
            print(f"  • Backed up old version to: {backup.name}")
        
        shutil.copy2(dll_found, dest)
        print(f"  ✓ Installed: {dll_found.name}")
        
        # Verify installation
        print("\n" + "="*70)
        print("Installation Summary")
        print("="*70)
        print(f"Target directory: {cuda_libs}")
        print("\nCurrent CUDA runtime DLLs:")
        for dll in sorted(cuda_libs.glob("cudart*.dll")):
            size = dll.stat().st_size
            print(f"  • {dll.name} ({size:,} bytes)")
        
        print("\n✓ CUDA 11.2 runtime DLL installed successfully!")
        print("\n" + "="*70)
        print("Next Steps:")
        print("1. Restart the atoscore application")
        print("2. Try Omnizart transcription - GPU should now work!")
        print("="*70)
        
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
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("✓ Cleanup complete!")
        except:
            pass

if __name__ == "__main__":
    try:
        success = extract_cuda_dlls()
        if not success:
            print("\n⚠ Extraction failed.")
            print("\nAlternative: Manual installation")
            print("1. Use 7-Zip to extract the CUDA installer")
            print("2. Copy cudart64_110.dll from cuda_cudart\\cudart\\bin")
            print("3. Paste to: D:\\Document\\atoscore\\atoscore_Core\\cuda_libs")
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\nFatal error: {e}")
    
    input("\nPress Enter to close...")

