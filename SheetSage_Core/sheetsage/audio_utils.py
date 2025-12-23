import os
import pathlib
import logging
import pretty_midi
import scipy.io.wavfile as wav
import numpy as np

def synthesize_midi(midi_path, soundfont_path, output_dir, filename="synth.wav"):
    """
    Synthesizes MIDI file to WAV using FluidSynth.
    """
    try:
        # Resolve paths
        midi_path = str(midi_path)
        soundfont_path = str(soundfont_path)
        output_dir = pathlib.Path(output_dir)
        
        if not os.path.exists(soundfont_path):
            logging.warning(f"Soundfont not found at {soundfont_path}")
            return None
            
        if not os.path.exists(midi_path) or os.path.getsize(midi_path) == 0:
             logging.warning(f"MIDI file missing or empty: {midi_path}")
             return None

        # Load MIDI
        try:
            pm = pretty_midi.PrettyMIDI(midi_path)
        except Exception as e:
            logging.error(f"Failed to load MIDI file {midi_path}: {e}")
            return None

        # Synthesize
        fs = 44100
        try:
            audio = pm.fluidsynth(fs=fs, sf2_path=soundfont_path)
        except Exception as e:
            logging.error(f"FluidSynth synthesis failed: {e}")
            return None
        
        # Write to file
        out_path = output_dir / filename
        
        # Normalize and convert to 16-bit PCM for broader compatibility if needed, 
        # but scipy.io.wavfile.write handles float32 (-1.0 to 1.0) usually.
        # However, pydub often likes integers if we load it later for mixing without warnings.
        
        # Normalize to avoid clipping
        if audio.size == 0:
            logging.info("Synthesized audio is empty (no notes detected?)")
            return None
            
        max_amp = np.max(np.abs(audio))
        logging.info(f"Synthesized audio max amplitude: {max_amp}")
        
        if max_amp > 0:
            audio = audio / max_amp * 0.9
            
        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        
        wav.write(str(out_path), fs, audio_int16)
        
        return str(out_path)
        
    except Exception as e:
        logging.error(f"Synthesis failed: {e}")
        return None

def create_mix(original_audio_path, synth_audio_path, output_dir, filename="mixed.wav"):
    """
    Mixes original audio with synthesized audio.
    Returns (mixed_path, original_segment_path)
    """
    try:
        from pydub import AudioSegment
        
        if not original_audio_path or not os.path.exists(original_audio_path):
            return None, None
            
        if not synth_audio_path or not os.path.exists(synth_audio_path):
            # Just copy original to output for consistency?
            out_orig = pathlib.Path(output_dir) / "original.wav"
            try:
                # Use pydub to convert/copy to ensure wav format
                orig = AudioSegment.from_file(original_audio_path)
                orig.export(str(out_orig), format="wav")
                return None, str(out_orig)
            except:
                return None, original_audio_path
            
        
        orig = AudioSegment.from_file(original_audio_path)
        synth = AudioSegment.from_file(synth_audio_path)
        
        # Lower original volume to let synth be heard clearly
        orig_quieter = orig - 6  # Reduce by 6dB
        
        # Overlay synth on top of original
        mixed = orig_quieter.overlay(synth)
        
        out_path = pathlib.Path(output_dir) / filename
        mixed.export(str(out_path), format="wav")
        
        # Export original as wav too for easy playback/reference
        out_orig = pathlib.Path(output_dir) / "original.wav"
        if not out_orig.exists():
             orig.export(str(out_orig), format="wav")
        
        return str(out_path), str(out_orig)
        
    except Exception as e:
        logging.error(f"Mixing failed: {e}")
        # Identify return: mixed, original
        return None, original_audio_path
