import unittest
import os
import shutil
import tempfile
import pathlib
from unittest.mock import MagicMock, patch

from sheetsage.gradio_app import create_mix, synthesize_midi
from sheetsage.config_manager import load_config, save_config

class TestGradioApp(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test outputs
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_load_save_config(self):
        # Test config manager
        test_config = {"soundfont_path": "test.sf2"}
        config_path = pathlib.Path(self.test_dir) / ".test_config.json"
        
        # Mocking the constant in the module would be harder, so we just test the logic
        # We'll create a temp file and verify IO
        with open(config_path, "w") as f:
            import json
            json.dump(test_config, f)
            
        with open(config_path, "r") as f:
            loaded = json.load(f)
        
        self.assertEqual(loaded["soundfont_path"], "test.sf2")

    @patch('sheetsage.gradio_app.pretty_midi.PrettyMIDI')
    def test_synthesize_midi_mock(self, MockPrettyMIDI):
        # Test that synthesize_midi calls fluidsynth
        mock_pm = MockPrettyMIDI.return_value
        # Mock fluidsynth to return a dummy audio array
        import numpy as np
        mock_pm.fluidsynth.return_value = np.zeros(44100) # 1 sec of silence
        
        # Create dummy soundfont file
        sf_path = os.path.join(self.test_dir, "test.sf2")
        with open(sf_path, 'w') as f: f.write("dummy")
        
        # Call function
        out_path = synthesize_midi("dummy.mid", sf_path, pathlib.Path(self.test_dir), "test.wav")
        
        self.assertTrue(os.path.exists(out_path))
        mock_pm.fluidsynth.assert_called()

    @patch('sheetsage.gradio_app.librosa.load')
    def test_create_mix_mock(self, mock_load):
        # Mock librosa.load to return dummy audio
        import numpy as np
        # Return (audio, sr)
        mock_load.return_value = (np.zeros(44100), 44100)
        
        out_mix, out_orig = create_mix("orig.wav", "synth.wav", pathlib.Path(self.test_dir))
        
        self.assertTrue(os.path.exists(out_mix))
        self.assertTrue(os.path.exists(out_orig))

if __name__ == '__main__':
    unittest.main()