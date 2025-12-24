import sys
import soundfile
import torchaudio
import torch

# Force soundfile backend if possible
try:
    torchaudio.set_audio_backend("soundfile")
    print("Set torchaudio backend to 'soundfile'")
except Exception as e:
    print(f"Could not set torchaudio backend: {e}")

def patched_save(filepath, src, sample_rate, **kwargs):
    # Demucs passes src as (Channels, Time) tensor
    # Soundfile expects (Time, Channels) numpy array
    try:
        if hasattr(src, "detach"):
            src = src.detach().cpu().numpy()
        
        # Transpose to (Time, Channels) if needed
        # Check integrity: channels should be small (1 or 2 usually), time is long
        if src.ndim == 2:
            if src.shape[0] < src.shape[1] and src.shape[0] <= 128: 
               # Heuristic: likely (C, T) -> Transpose to (T, C)
               src = src.T
            elif src.shape[1] < src.shape[0] and src.shape[1] <= 128:
               # Heuristic: likely (T, C) -> Keep as is
               pass
           
        soundfile.write(str(filepath), src, sample_rate)
    except Exception as e:
        print(f"Error in patched_save: {e}")
        # Last ditch effort: try native save if patched fails? 
        # No, native save is what causes the error. Raise.
        raise e

# Monkey patch torchaudio.save
torchaudio.save = patched_save
print("Patched torchaudio.save with soundfile-based implementation")

try:
    from demucs.separate import main
except ImportError:
    # If demucs is not installed or import fails
    print("Error: Could not import demucs.separate")
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
