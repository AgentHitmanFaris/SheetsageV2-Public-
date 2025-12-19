import logging
import math
import numpy as np
import librosa

def librosa_beat_track(sr, audio, beats_per_bar=None, beats_per_minute_hint=None):
    """
    Runs beat tracking using Librosa (replacing the heavy Madmom binary dependency).

    Args:
        sr (int): The sample rate of the audio.
        audio (np.ndarray): The audio signal.
        beats_per_bar (int or list, optional): The expected number of beats per bar (time signature numerator).
            Can be a single integer or a list of possible integers.
        beats_per_minute_hint (float, optional): A hint for the tempo in beats per minute.

    Returns:
        tuple: A tuple containing:
            - first_downbeat (int or None): The index of the first downbeat in the list of beat times.
            - detected_beats_per_bar (int or None): The detected number of beats per bar.
            - merged (list): A sorted list of timestamps (in seconds) for all detected beats.
    """
    if beats_per_minute_hint is not None and beats_per_minute_hint < 0:
        raise ValueError("BPM hint must be non-negative")

    # Ensure audio is float for librosa
    if audio.dtype != np.float32 and audio.dtype != np.float64:
            audio_float = audio.astype(np.float32)
            if np.abs(audio_float).max() > 1.0:
                audio_float /= np.iinfo(audio.dtype).max
            audio = audio_float

    # Ensure Mono for Librosa Beat Tracking
    if audio.ndim > 1:
        audio_mono = np.mean(audio, axis=1)
    else:
        audio_mono = audio

    start_bpm = beats_per_minute_hint if beats_per_minute_hint else 120.0
    
    try:
        # Compute onset envelope
        onset_env = librosa.onset.onset_strength(y=audio_mono, sr=sr)
        
        # Run Librosa Beat Tracking
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env, 
            sr=sr, 
            start_bpm=start_bpm,
            units='frames'
        )
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        merged = beat_times.tolist()
        
        # Determine Time Signature (Beats Per Bar)
        detected_beats_per_bar = 4
        if beats_per_bar is not None:
            if isinstance(beats_per_bar, list):
                detected_beats_per_bar = beats_per_bar[0]
            else:
                detected_beats_per_bar = beats_per_bar
        
        # Simple Downbeat Assumption: First beat is downbeat
        # (Librosa doesn't do downbeat tracking natively without complex RNNs)
        first_downbeat = 0
        
        if len(merged) == 0:
                raise Exception("Librosa found no beats.")

        # Ensure 100Hz quantization for consistency with rest of pipeline
        merged = [round(t * 100) / 100 for t in merged]

        return first_downbeat, detected_beats_per_bar, merged

    except Exception as e:
        logging.warning(f"Librosa beat tracking failed: {e}. Falling back to constant grid.")
        
        # Fallback constant grid
        fallback_bpm = start_bpm
        fallback_bpb = 4
        if beats_per_bar is not None:
            if isinstance(beats_per_bar, list):
                fallback_bpb = beats_per_bar[0]
            else:
                fallback_bpb = beats_per_bar
        
        duration = len(audio) / sr
        beat_interval = 60.0 / fallback_bpm
        
        merged = []
        t = 0.0
        while t < duration:
            merged.append(t)
            t += beat_interval
            
        merged = [round(t * 100) / 100 for t in merged]
        return 0, fallback_bpb, merged
