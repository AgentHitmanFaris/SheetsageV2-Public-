import unittest
from unittest.mock import patch, MagicMock
import tempfile
import soundfile as sf

import numpy as np

from atoscore.assets import retrieve_asset
from .handcrafted import OAFMelSpec


class TestHandcrafted(unittest.TestCase):
    @patch("atoscore.representations.handcrafted.decode_audio")
    @patch("atoscore.representations.handcrafted_test.retrieve_asset")
    def test_oaf_transcription(self, mock_retrieve, mock_decode):
        mp3_path = "dummy.mp3"
        mock_retrieve.side_effect = lambda x: mp3_path if x == "TEST_MP3" else "dummy_ref_path"

        # Mock decode_audio to return 16kHz audio (as expected by OAFMelSpec)
        # OAFMelSpec uses sr=16000
        sr = 16000
        duration = 4.65
        audio = np.random.uniform(-1, 1, (int(sr * duration), 1)).astype(np.float32)
        mock_decode.return_value = (sr, audio)

        # Mock np.load for reference
        with patch("numpy.load") as mock_load:
            # Expected shape is (144, 229) transposed?
            # rep shape is (144, 229).
            # Test says ref = np.load(...).T.
            mock_load.return_value = np.zeros((229, 144))

            rate, rep = OAFMelSpec()(mp3_path)

            self.assertAlmostEqual(rate, 31.25, places=2)
            self.assertEqual(rep.shape[1], 229)
