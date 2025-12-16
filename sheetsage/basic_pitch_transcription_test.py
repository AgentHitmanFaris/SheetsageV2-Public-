import unittest
import os
import shutil
import tempfile
import pathlib
from unittest.mock import MagicMock, patch

# We need to mock basic_pitch before importing the module under test
# because it might have heavy dependencies or be broken
import sys
mock_bp = MagicMock()
sys.modules["basic_pitch"] = mock_bp
sys.modules["basic_pitch.inference"] = mock_bp.inference

from sheetsage.basic_pitch_transcription import transcribe_basic_pitch

class TestBasicPitchTranscription(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.audio_path = os.path.join(self.test_dir, "test.wav")
        # Create dummy audio
        with open(self.audio_path, "w") as f:
            f.write("RIFF")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("sheetsage.basic_pitch_transcription.sheetsage")
    @patch("sheetsage.basic_pitch_transcription.predict_and_save")
    @patch("sheetsage.basic_pitch_transcription.tempfile.TemporaryDirectory")
    @patch("sheetsage.basic_pitch_transcription.LeadSheet")
    def test_transcribe_basic_pitch_success(self, mock_LeadSheet, mock_temp_dir, mock_predict, mock_sheetsage):
        # Setup mock temp dir
        temp_dir_obj = MagicMock()
        temp_dir_path = os.path.join(self.test_dir, "mock_bp_temp")
        os.makedirs(temp_dir_path, exist_ok=True)
        temp_dir_obj.__enter__.return_value = temp_dir_path
        mock_temp_dir.return_value = temp_dir_obj

        # Configure mocked LeadSheet
        mock_ls_instance = mock_LeadSheet.return_value
        mock_ls_instance.as_lily.return_value = "\\score {}"
        mock_ls_instance.as_midi.return_value = b"MThd..."

        # Create dummy MIDI file in that dir
        dummy_midi = os.path.join(temp_dir_path, "output_basic_pitch.mid")
        with open(dummy_midi, "w") as f:
            f.write("MThd...")

        # Mock predict_and_save side effect (just pass)
        mock_predict.side_effect = lambda *args, **kwargs: None
        
        # Mock output path
        output_midi_path = os.path.join(self.test_dir, "output.midi")
        
        # Mock sheetsage return value (lead_sheet, beats, beat_times)
        mock_ls = MagicMock()
        mock_ls.as_lily.return_value = "\\score {}"
        # Make lead_sheet iterable with 6 elements
        # (meter, tempo, key, harmony, melody, total_tertiary)
        mock_ls.__iter__.return_value = iter([
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), 100
        ])
        mock_ls.__getitem__ = lambda self, idx: 100 if idx == 5 else MagicMock()
        
        # Need accurate beats for interpolation logic
        # 10 seconds, 1 beat per second
        mock_sheetsage.return_value = (mock_ls, list(range(10)), list(range(10)))

        # Mock PrettyMIDI
        with patch("sheetsage.basic_pitch_transcription.pretty_midi.PrettyMIDI") as MockPM:
            pm_instance = MockPM.return_value
            # Add dummy notes
            inst = MagicMock()
            note = MagicMock()
            note.start = 0.0
            note.end = 1.0
            note.pitch = 60
            inst.notes = [note]
            pm_instance.instruments = [inst]
            
            # Mock engrave and other utils
            with patch("sheetsage.basic_pitch_transcription.engrave") as mock_engrave, \
                 patch("builtins.open", unittest.mock.mock_open(read_data=b"dummy")):
                
                result = transcribe_basic_pitch(self.audio_path, output_midi_path)
                
                self.assertTrue(len(result) > 0)
                mock_predict.assert_called_once()
                mock_sheetsage.assert_called_once()

if __name__ == '__main__':
    unittest.main()
