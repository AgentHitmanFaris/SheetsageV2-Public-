# Simple CUDA DLL Extractor for Windows
# Extracts cudart64_110.dll from CUDA 11.2.2 installer

$ErrorActionPreference = "Stop"

Write-Host "=============================================="
Write-Host "CUDA 11.2 Runtime DLL Extractor"
Write-Host "=============================================="

# Paths
$cudaInstaller = "D:\Download\Programs\cuda_11.2.2_461.33_win10.exe"
$cudaLibsDir = "D:\Document\sheetsage\SheetSage_Core\cuda_libs"
$tempDir = "D:\Document\sheetsage\SheetSage_Core\temp_cuda"

# Verify installer exists
if (-not (Test-Path $cudaInstaller)) {
    Write-Host "ERROR: CUDA installer not found at: $cudaInstaller"
    exit 1
}

Write-Host "`nFound installer: $cudaInstaller"
$size = (Get-Item $cudaInstaller).Length / 1MB
Write-Host "Size: $([math]::Round($size, 2)) MB"

# Create temp directory
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host "`n[1/3] Extracting CUDA installer (this may take 2-3 minutes)..."
    
    # Use Windows built-in extractor (slower but works without 7-Zip)
    $exePath = "C:\Windows\System32\expand.exe"
    
    if (Test-Path $exePath) {
        # Try expand command
        $result = & $exePath $cudaInstaller $tempDir -F:* 2>&1
        Write-Host "Expand completed"
    } else {
        Write-Host "ERROR: No extraction tool available"
        Write-Host "`nPlease extract manually:"
        Write-Host "1. Right-click: $cudaInstaller"
        Write-Host "2. Choose 7-Zip > Extract to 'cuda_11.2.2...'"
        Write-Host "3. Navigate to: cuda_cudart\cudart\bin"
        Write-Host "4. Copy cudart64_110.dll to: $cudaLibsDir"
        exit 1
    }
    
    Write-Host "`n[2/3] Searching for cudart64_110.dll..."
    
    # Find the DLL
    $dllPath = Get-ChildItem -Path $tempDir -Recurse -Filter "cudart64_110.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if (-not $dllPath) {
        Write-Host "ERROR: cudart64_110.dll not found in extracted files"
        Write-Host "`nExtracted files location: $tempDir"
        Write-Host "Please navigate there and manually locate the DLL"
        exit 1
    }
    
    Write-Host "Found: $($dllPath.FullName)"
    $dllSize = $dllPath.Length / 1KB
    Write-Host "Size: $([math]::Round($dllSize, 2)) KB"
    
    Write-Host "`n[3/3] Installing to cuda_libs..."
    
    # Backup old DLL
    $destPath = Join-Path $cudaLibsDir "cudart64_110.dll"
    if (Test-Path $destPath) {
        $backupPath = Join-Path $cudaLibsDir "cudart64_110_old.dll"
        Move-Item $destPath $backupPath -Force
        Write-Host "Backed up old DLL to: cudart64_110_old.dll"
    }
    
    # Copy new DLL
    Copy-Item $dllPath.FullName $destPath -Force
    Write-Host "Installed: cudart64_110.dll"
    
    # Verify
    if (Test-Path $destPath) {
        $newSize = (Get-Item $destPath).Length / 1KB
        $newDate = (Get-Item $destPath).LastWriteTime
        
        Write-Host "`n=============================================="
        Write-Host "SUCCESS!"
        Write-Host "=============================================="
        Write-Host "New CUDA runtime DLL:"
        Write-Host "  Path: $destPath"
        Write-Host "  Size: $([math]::Round($newSize, 2)) KB"
        Write-Host "  Date: $($newDate.ToString('yyyy-MM-dd HH:mm'))"
        Write-Host "`nNext steps:"
        Write-Host "1. Restart SheetSage application"
        Write-Host "2. GPU acceleration should now work!"
        Write-Host "=============================================="
    }
    
} catch {
    Write-Host "`nERROR: $($_.Exception.Message)"
    Write-Host "`nStack trace:"
    Write-Host $_.ScriptStackTrace
    exit 1
} finally {
    # Cleanup
    Write-Host "`nCleaning up temporary files..."
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Cleanup complete"
}
