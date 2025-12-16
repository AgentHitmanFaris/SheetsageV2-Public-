import logging
import os
import pathlib
import tempfile
import torch
import librosa
from .assets import retrieve_asset

def transcribe_piano(audio_path, output_midi_path, device=None):
    """
    Transcribes piano audio to MIDI using ByteDance's Piano Transcription with Pedals model.

    Args:
        audio_path (str): Path to the audio file.
        output_midi_path (str): Path where the MIDI file will be saved.
        device (str, optional): Device to run inference on ('cuda' or 'cpu'). Defaults to auto-detect.
    """
    from piano_transcription_inference import PianoTranscription, sample_rate

    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    logging.info(f"Using device: {device}")

    # Retrieve the model checkpoint from assets
    # checkpoint_path = retrieve_asset("PIANO_TRANSCRIPTION_MODEL", delete_wrong=True)
    # logging.info(f"Using piano transcription model at: {checkpoint_path}")

    # Load audio
    logging.info(f"Loading audio from {audio_path}")
    audio, _ = librosa.load(audio_path, sr=sample_rate, mono=True)

    # Initialize transcriptor
    # If checkpoint_path is None, the library downloads the default model automatically.
    transcriptor = PianoTranscription(device=device, checkpoint_path=None)

    # Transcribe
    logging.info("Starting piano transcription...")
    transcriptor.transcribe(audio, output_midi_path)
    logging.info(f"Transcription complete. Saved to {output_midi_path}")
