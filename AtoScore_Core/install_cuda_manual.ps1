# Manual CUDA DLL Installation Guide
# Quick steps to copy the correct CUDA 11.2 runtime DLL

Write-Host "=============================================="
Write-Host "CUDA 11.2 Runtime DLL - Manual Installation"
Write-Host "=============================================="

Write-Host "`nYou have the CUDA archive open in 7-Zip already."
Write-Host "Follow these steps:"
Write-Host ""
Write-Host "1. In 7-Zip, navigate to this location in the archive:"
Write-Host "   cuda_cudart\cudart\bin\"
Write-Host ""
Write-Host "2. You should see: cudart64_110.dll (464 KB, dated 2021-02-15)"
Write-Host ""
Write-Host "3. Right-click cudart64_110.dll > Copy To..."
Write-Host ""
Write-Host "4. Navigate to and select this folder:"
Write-Host "   D:\Document\atoscore\atoscore_Core\cuda_libs\"
Write-Host ""
Write-Host "5. Click OK to copy (overwrite the existing file)"
Write-Host ""
Write-Host "=============================================="
Write-Host "Verification:"
Write-Host "=============================================="

$cudaLibs = "D:\Document\atoscore\atoscore_Core\cuda_libs"
$targetDll = Join-Path $cudaLibs "cudart64_110.dll"

if (Test-Path $targetDll) {
    $currentFile = Get-Item $targetDll
    $size = [math]::Round($currentFile.Length / 1KB, 0)
    $date = $currentFile.LastWriteTime.ToString('yyyy-MM-dd HH:mm')
    
    Write-Host "`nCurrent file:"
    Write-Host "  Path: $targetDll"
    Write-Host "  Size: $size KB"
    Write-Host "  Date: $date"
    
    if ($size -eq 454) {
        Write-Host "`n  STATUS: OLD CUDA 11.0 version (still needs update)"
    } elseif ($size -eq 464) {
        Write-Host "`n  STATUS: CORRECT! This is CUDA 11.2"  
        Write-Host "`n  Next step: Restart atoscore application"
    } else {
        Write-Host "`n  STATUS: Unknown version (size: $size KB)"
    }
}

Write-Host "`n=============================================="
Write-Host "Press Enter when done copying..."
$null = Read-Host

