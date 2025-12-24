"""
Video Audio Extraction Utility
Extracts audio from video files using FFmpeg
"""
import subprocess
import pathlib
import logging
import os


def extract_audio_from_video(video_path, output_audio_path=None):
    """
    Extract audio from video file using FFmpeg.
    
    Args:
        video_path (str): Path to input video file
        output_audio_path (str, optional): Path for output audio. If None, creates WAV in temp dir
        
    Returns:
        str: Path to extracted audio file
        
    Raises:
        Exception: If FFmpeg fails or video has no audio track
    """
    video_path = pathlib.Path(video_path)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Generate output path if not provided
    if output_audio_path is None:
        import tempfile
        temp_dir = os.environ.get("ATOSCORE_TEMP", tempfile.gettempdir())
        output_audio_path = pathlib.Path(temp_dir) / f"{video_path.stem}_audio.wav"
    else:
        output_audio_path = pathlib.Path(output_audio_path)
    
    # Ensure output directory exists
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)
    
    # FFmpeg command to extract audio
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", "44100",  # Sample rate
        "-ac", "2",  # Stereo
        "-y",  # Overwrite output file
        str(output_audio_path)
    ]
    
    logging.info(f"Extracting audio from video: {video_path}")
    logging.info(f"Output audio: {output_audio_path}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logging.error(f"FFmpeg stderr: {result.stderr}")
            raise Exception(f"FFmpeg failed to extract audio: {result.stderr}")
        
        if not output_audio_path.exists():
            raise Exception("Audio extraction succeeded but output file not found")
        
        logging.info(f"Audio extracted successfully: {output_audio_path}")
        return str(output_audio_path)
        
    except FileNotFoundError:
        raise Exception("FFmpeg not found. Please ensure FFmpeg is installed and in PATH")
