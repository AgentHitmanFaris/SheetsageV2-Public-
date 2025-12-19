import sys
import soundfile
import torchaudio

def patched_save(filepath, src, sample_rate, **kwargs):
    # Demucs passes src as (Channels, Time) tensor
    # Soundfile expects (Time, Channels) numpy array
    try:
        if hasattr(src, "detach"):
            src = src.detach().cpu().numpy()
        
        # Transpose to (Time, Channels)
        if src.ndim == 2 and src.shape[0] < src.shape[1]:
           src = src.T
           
        soundfile.write(str(filepath), src, sample_rate)
    except Exception as e:
        print(f"Error in patched_save: {e}")
        raise e

# Monkey patch torchaudio.save
torchaudio.save = patched_save

from demucs.separate import main

if __name__ == "__main__":
    sys.exit(main())
