import logging
import math
import numpy as np
import librosa
import tempfile
import soundfile as sf
import os

def _librosa_beat_track_impl(sr, audio, beats_per_bar=None, beats_per_minute_hint=None):
    """
    Runs beat tracking using Librosa (replacing the heavy Madmom binary dependency).
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

# Maintain alias for compatibility
librosa_beat_track = _librosa_beat_track_impl

def beatnet_beat_track(sr, audio, beats_per_bar=None, beats_per_minute_hint=None):
    """
    Runs beat tracking using BeatNet, failing back to Librosa.
    """
    try:
        from BeatNet.BeatNet import BeatNet
        
        # Save audio to temporary file for BeatNet
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        # Ensure audio is float32 for soundfile write purity or just same as input
        sf.write(temp_path, audio, sr)
        
        try:
            # Initialize BeatNet
            estimator = BeatNet(1, mode='offline', inference_model='DBN', plot=[], thread=False, device='cuda')
            
            output = estimator.process(temp_path)
            
            if output is None or len(output) == 0:
                 raise Exception("BeatNet found no beats.")
    
            beat_times = output[:, 0]
            beat_indices = output[:, 1].astype(int)
            
            # Determine Time Signature
            max_beat = np.max(beat_indices)
            detected_beats_per_bar = max_beat 
            
            # Override if hint provided
            if beats_per_bar is not None:
                 if isinstance(beats_per_bar, list):
                     detected_beats_per_bar = beats_per_bar[0]
                 else:
                     detected_beats_per_bar = beats_per_bar
            
            if detected_beats_per_bar is None: 
                detected_beats_per_bar = 4
            
            # Find first downbeat (index 1)
            first_downbeat = 0
            for i, b_idx in enumerate(beat_indices):
                if b_idx == 1:
                    first_downbeat = i
                    break
            
            # Ensure first_downbeat is bar-local
            first_downbeat = first_downbeat % detected_beats_per_bar
            
            merged = [round(t * 100) / 100 for t in beat_times.tolist()]
            return first_downbeat, detected_beats_per_bar, merged
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        # Catch ImportError (missing madmom) or Runtime errors
        logging.warning(f"BeatNet beat tracking failed/unavailable: {e}. Falling back to Librosa.")
        return _librosa_beat_track_impl(sr, audio, beats_per_bar, beats_per_minute_hint)
