import os
import pretty_midi
import numpy as np
import logging
from scipy.io import wavfile

logging.basicConfig(level=logging.INFO)

midi_path = r"D:\Document\atoscore\atoscore_Core\output\omnizart_advanced\20251220_2102_Aisha_Retno_-_Tak_Ad_drum_8d0ffb\Aisha Retno - Tak Adil Official Music Video fMiH9F7O9eM.mid"
soundfont_path = r"D:\Document\atoscore\atoscore_Core\soundfont\MS Basic.sf3"
output_dir = r"D:\Document\atoscore\atoscore_Core\temp"

def synthesize_midi(midi_path, soundfont_path_config, output_dir, filename="output.wav"):
    try:
        if not os.path.exists(soundfont_path_config):
             logging.warning(f"Soundfont not found at {soundfont_path_config}")
             return None
             
        # Check if MIDI file exists and has size
        if not os.path.exists(midi_path) or os.path.getsize(midi_path) == 0:
             logging.warning(f"MIDI file is missing or empty: {midi_path}")
             return None

        pm = pretty_midi.PrettyMIDI(midi_path)
        
        # Debug MIDI content
        total_notes = sum(len(i.notes) for i in pm.instruments)
        duration = pm.get_end_time()
        print(f"Synthesizing MIDI: {total_notes} notes, {duration:.2f}s duration.")
        
        if total_notes == 0 or duration <= 0:
             logging.warning("MIDI file has no notes or zero duration. Skipping synthesis.")
             return None

        audio_data = pm.fluidsynth(fs=44100, sf2_path=soundfont_path_config)
        
        if audio_data is None or len(audio_data) == 0:
             logging.warning("Synthesized audio is empty.")
             return None

        # Normalize safely
        chk_max = np.abs(audio_data).max() if audio_data.size > 0 else 0
        if chk_max > 0:
            audio_data = audio_data / chk_max
        
        # Convert to 16-bit PCM for broader compatibility
        audio_data_int16 = (audio_data * 32767).astype(np.int16)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        wav_path = os.path.join(output_dir, filename)
        wavfile.write(str(wav_path), 44100, audio_data_int16)
        print(f"Success: {wav_path}")
        return str(wav_path)
    except Exception as e:
        logging.error(f"Synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

synthesize_midi(midi_path, soundfont_path, output_dir)

