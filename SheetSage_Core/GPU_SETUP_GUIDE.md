# Portable GPU Setup Guide for SheetSage

This guide explains how to enable GPU acceleration for Omnizart (and TensorFlow) **without installing anything system-wide**. We will place the necessary DLLs in a folder inside the project.

## Prerequisites
- **NVIDIA Driver**: You already have this (verified via `nvidia-smi`).
- **Disk Space**: ~2 GB for extraction.

## Step 1: Create the Local Library Folder
1. Verify that a folder named `cuda_libs` exists in the root of your `SheetSage_Core` directory.
   - Path: `D:\Document\sheetsage\SheetSage_Core\cuda_libs`
   - (The application will detect this folder automatically).

## Step 2: Get CUDA 11.2 DLLs
1. Download **CUDA Toolkit 11.2.2** (Archive) from NVIDIA:
   - [Official Archive Link](https://developer.nvidia.com/cuda-11-2-2-download-archive?target_os=Windows&target_arch=x86_64&target_version=10&target_type=exe_local)
   - *Note: It's a large download (~2.5GB).*
2. **Do NOT run the installer normally.**
   - Open the `.exe` with a file archiver like **7-Zip** or **WinRAR**.
   - OR run the installer, choose "Extract to", let it extract, then **CANCEL** the installation when the window pops up. Go to the extraction folder (usually `C:\Temp\CUDA...`).
3. Locate the `bin` folder inside the extracted files.
4. Copy the following files into your `SheetSage_Core\cuda_libs` folder:
   - `cudart64_110.dll`
   - `cublas64_11.dll`
   - `cublasLt64_11.dll`
   - `cufft64_10.dll`
   - `curand64_10.dll`
   - `cusolver64_11.dll`
   - `cusparse64_11.dll`

## Step 3: Get cuDNN 8.1 DLLs
1. Download **cuDNN v8.1.1 (Feb 26th, 2021), for CUDA 11.0,11.1 and 11.2**:
   - [NVIDIA cuDNN Archive](https://developer.nvidia.com/rdp/cudnn-archive)
   - *Note: Requires an NVIDIA Developer account (free).*
2. Extract the ZIP file.
3. Open the `bin` folder inside the extracted archive.
4. Copy the following file into your `SheetSage_Core\cuda_libs` folder:
   - `cudnn64_8.dll`

## Step 4: Verification
1. Run the `check_gpu.bat` script (or `run_local.bat`).
2. It should now say `GPU Available: 1` (or count your GPUs).

**Your folder `SheetSage_Core\cuda_libs` should look like this:**
```text
cuda_libs/
├── cublas64_11.dll
├── cublasLt64_11.dll
├── cudart64_110.dll
├── cudnn64_8.dll
├── cufft64_10.dll
├── curand64_10.dll
├── cusolver64_11.dll
└── cusparse64_11.dll
```
