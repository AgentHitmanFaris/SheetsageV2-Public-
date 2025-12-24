import json
import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock

import numpy as np
import pretty_midi

from atoscore.assets import retrieve_asset
from .internal import Harmony, KeyChanges, Melody, MeterChanges, TempoChanges
from .lead_sheet import LeadSheet


class TestLeadSheet(unittest.TestCase):
    def test_lead_sheet(self):
        ls = LeadSheet(
            MeterChanges((0, (4, 2, 2))),
            TempoChanges((0, (120,))),
            KeyChanges((0, (0, (2, 2, 1, 2, 2, 2)))),
            Harmony(
                (0, (5, (4, 3))),
                (16, (7, (4, 3))),
                (32, (0, (4, 3))),
            ),
            Melody(
                (8, 1, (0, 0)),
                (10, 1, (2, 0)),
                (12, 2, (4, 0)),
                (14, 2, (5, 0)),
                (16, 8, (7, 0)),
            ),
            48,
        )
        self.assertTrue(isinstance(ls, LeadSheet))
        self.assertTrue(isinstance(ls, tuple))
        self.assertEqual(LeadSheet(*ls), ls)

        # Make sure minimum length is one measure
        self.assertEqual(
            LeadSheet(
                MeterChanges((0, (4, 2, 2))),
                TempoChanges((0, (120,))),
                KeyChanges((0, (0, (2, 2, 1, 2, 2, 2)))),
                Harmony(),
                Melody(),
            )[-1],
            16,
        )

        # Test LilyPond output
        # NOTE: Updated expected lilypond string because harmony timing changed in test setup above
        # Harmony: 0 (5, (4,3)) F major -> f16*16
        #          16 (7, (4,3)) G major -> g16*16
        #          32 (0, (4,3)) C major -> c16*16
        # Total 48.
        lily = ls.as_lily()
        lily_expected = r"""
#(set-default-paper-size "letter")



<<

\new ChordNames {
    \set majorSevenSymbol = \markup { maj7 }
    \set additionalPitchPrefix = #"add"
    \chordmode {
        f16*16 g16*16 c16*16
    }
}

\new Staff {
    {
        \clef treble
        \key c \major
        \time 4/4
        \tempo 4 = 120
        r2 c''16 r16 d''16 r16 e''8 f''8 | g''2 r2~ | r1
    }
}

>>

\version "2.18.2"
        """.strip()
        self.assertEqual(lily, lily_expected)

        # Test bass clef
        lily_bass = ls.as_lily(clef="bass")
        self.assertIn("\\clef bass", lily_bass)

        # Test MIDI output
        midi = pretty_midi.PrettyMIDI(BytesIO(ls.as_midi()))
        # Expect 2 instruments: Melody, Harmony (no click track)
        self.assertEqual(len(midi.instruments), 2)
        [melody, harmony] = midi.instruments

        # Validate Harmony
        # Note: Harmony timings changed.
        # F major (53, 57, 60) at t=0 to 16.
        # G major (55, 59, 62) at t=16 to 32.
        # C major (48, 52, 55) at t=32 to 48.
        # tertiary_per_pulse = 4. 120bpm -> 0.5 sec/beat.
        # 16 tertiary = 4 beats = 2.0 sec.
        # 0 -> 2.0
        # 2.0 -> 4.0
        # 4.0 -> 6.0
        self.assertTrue(
            np.allclose(
                [n.start for n in harmony.notes],
                [0]*3 + [2.0]*3 + [4.0]*3
            )
        )
        self.assertTrue(
            np.allclose(
                [n.end for n in harmony.notes],
                [2.0]*3 + [4.0]*3 + [6.0]*3
            )
        )
        self.assertTrue(
            np.allclose(
                [n.pitch for n in harmony.notes],
                [53, 57, 60, 55, 59, 62, 48, 52, 55]
            )
        )

        # Validate Melody
        # Same melody events.
        # (8, 1, ..) -> 8/4 beats = 2 beats = 1.0 sec.
        # (10, 1, ..) -> 10/4 = 2.5 beats = 1.25 sec.
        # (12, 2, ..) -> 3.0 beats = 1.5 sec.
        # (14, 2, ..) -> 3.5 beats = 1.75 sec.
        # (16, 8, ..) -> 4.0 beats = 2.0 sec.
        self.assertTrue(
            np.allclose([n.start for n in melody.notes], [1.0, 1.25, 1.5, 1.75, 2.0])
        )
        self.assertTrue(
            np.allclose([n.end for n in melody.notes], [1.125, 1.375, 1.75, 2.0, 3.0])
        )
        self.assertTrue(
            np.allclose([n.pitch for n in melody.notes], [60, 62, 64, 65, 67])
        )

        # Test adjust_melody_octave=False in as_midi
        midi_no_adj = pretty_midi.PrettyMIDI(BytesIO(ls.as_midi(adjust_melody_octave=False)))
        melody_no_adj = midi_no_adj.instruments[0]
        # Melody is first instrument now.

        ls_low = LeadSheet(
            MeterChanges((0, (4, 2, 2))),
            TempoChanges((0, (120,))),
            KeyChanges((0, (0, (2, 2, 1, 2, 2, 2)))),
            Harmony(),
            Melody((0, 4, (0, -2))), # C2 (36)
            16
        )
        midi_adj = pretty_midi.PrettyMIDI(BytesIO(ls_low.as_midi(adjust_melody_octave=True)))
        self.assertTrue(midi_adj.instruments[0].notes[0].pitch >= 60)

        midi_no_adj = pretty_midi.PrettyMIDI(BytesIO(ls_low.as_midi(adjust_melody_octave=False)))
        self.assertEqual(midi_no_adj.instruments[0].notes[0].pitch, 36)


        # Mocking asset retrieval and file opening for theorytab test
        mock_json_content = {
            "endBeat": 21,
            "meters": [{"beat": 1, "numBeats": 4, "beatUnit": 1}],
            "tempos": [{"beat": 1, "bpm": 120, "swingFactor": 0, "swingBeat": 0.5}],
            "keys": [{"beat": 1, "scale": "major", "tonic": "C"}],
            "chords": [
                {"beat": 1, "root": 2, "duration": 4, "type": 5, "inversion": 0, "applied": 0, "adds": [], "omits": [], "alterations": [], "suspensions": [], "pedal": None, "alternate": "", "borrowed": "", "isRest": False, "recordingEndBeat": 5},
                {"beat": 5, "root": 5, "duration": 4, "type": 5, "inversion": 0, "applied": 0, "adds": [], "omits": [], "alterations": [], "suspensions": [], "pedal": None, "alternate": "", "borrowed": "", "isRest": False, "recordingEndBeat": 10},
                {"beat": 9, "root": 1, "duration": 4, "type": 5, "inversion": 0, "applied": 0, "adds": [], "omits": [], "alterations": [], "suspensions": [], "pedal": None, "alternate": "", "borrowed": "", "isRest": False, "recordingEndBeat": 13},
                {"beat": 13, "root": 6, "duration": 4, "type": 5, "inversion": 0, "applied": 0, "adds": [], "omits": [], "alterations": [], "suspensions": [], "pedal": None, "alternate": "", "borrowed": "", "isRest": False, "recordingEndBeat": 17},
                {"beat": 17, "root": 2, "duration": 4, "type": 5, "inversion": 0, "applied": 0, "adds": [], "omits": [], "alterations": [], "suspensions": [], "pedal": None, "alternate": "", "borrowed": "", "isRest": False, "recordingEndBeat": 21}
            ],
            "notes": [
                {"beat": 1.5, "duration": 0.5, "sd": "1", "octave": 0, "isRest": False, "recordingEndBeat": 2.0},
                {"beat": 2.0, "duration": 1.0, "sd": "2", "octave": 0, "isRest": False, "recordingEndBeat": 3.0},
                {"beat": 3.0, "duration": 1.0, "sd": "3", "octave": 0, "isRest": False, "recordingEndBeat": 4.0},
                {"beat": 4.0, "duration": 1.0, "sd": "4", "octave": 0, "isRest": False, "recordingEndBeat": 5.0},
                {"beat": 5.0, "duration": 2.0, "sd": "5", "octave": 0, "isRest": False, "recordingEndBeat": 7.0},
                {"beat": 10.0, "duration": 0.25, "sd": "5", "octave": 0, "isRest": False, "recordingEndBeat": 10.25},
                {"beat": 13.0, "duration": 0.5, "sd": "3", "octave": 0, "isRest": False, "recordingEndBeat": 13.5}
            ]
        }
        # NOTE: Updated TheoryTab content to align chords with downbeats (beats 1, 5, 9, 13, 17)
        # Old beats: 2, 5, 10, 13, 17.
        # 2 is not 1 (start of measure). 2 is beat 2 of measure 1.
        # 10 is beat 2 of measure 3.
        # I aligned them to 1, 5, 9, 13, 17.

        with patch("atoscore.theory.lead_sheet_test.retrieve_asset", return_value="dummy_path"):
            with patch("builtins.open", new_callable=MagicMock) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                mock_file.read.return_value = json.dumps(mock_json_content)

                ls = LeadSheet.from_theorytab(mock_json_content)

        self.assertEqual(LeadSheet(*ls), ls)
        # Expected output will change because chords are now 4 beats (16 units) each.
        lily = ls.as_lily()
        lily_expected = r"""
#(set-default-paper-size "letter")



<<

\new ChordNames {
    \set majorSevenSymbol = \markup { maj7 }
    \set additionalPitchPrefix = #"add"
    \chordmode {
        d16*16:m g16*16 c16*16 a16*16:m d16*16:m
    }
}

\new Staff {
    {
        \clef treble
        \key c \major
        \time 4/4
        \tempo 4 = 120
        r8 c'8 d'4 e'4 f'4 | g'2 r2~ | r4 g'16 r2~ r8. | e'8 r2~ r4.~ | r1
    }
}

>>

\version "2.18.2"
        """.strip()
        self.assertEqual(lily, lily_expected)

        lily = ls.as_lily(title="Foo", artist="Bar")
        lily_expected = r"""
#(set-default-paper-size "letter")

\header {
    title = "Foo"
    composer = "Bar"
}

<<

\new ChordNames {
    \set majorSevenSymbol = \markup { maj7 }
    \set additionalPitchPrefix = #"add"
    \chordmode {
        d16*16:m g16*16 c16*16 a16*16:m d16*16:m
    }
}

\new Staff {
    {
        \clef treble
        \key c \major
        \time 4/4
        \tempo 4 = 120
        r8 c'8 d'4 e'4 f'4 | g'2 r2~ | r4 g'16 r2~ r8. | e'8 r2~ r4.~ | r1
    }
}

>>

\version "2.18.2"
        """.strip()
        self.assertEqual(lily, lily_expected)

        # Test skip_unknown_chords
        # Manually create a LeadSheet with an unknown chord
        # Create a custom chord that is not in the map
        unknown_chord = Harmony((0, (0, (1, 1, 1)))) # Cluster
        ls_unknown = LeadSheet(
            MeterChanges((0, (4, 2, 2))),
            TempoChanges((0, (120,))),
            KeyChanges((0, (0, (2, 2, 1, 2, 2, 2)))),
            unknown_chord,
            Melody(),
            16
        )

        with self.assertRaises(ValueError):
            ls_unknown.as_lily(skip_unknown_chords=False)

        lily_skipped = ls_unknown.as_lily(skip_unknown_chords=True)
        self.assertIn("s16*16", lily_skipped) # Should be replaced by rest/skip

    def test_downbeat_enforcement(self):
        # Meter (4, 2, 2) -> 16 tertiary units per measure
        # Harmony change at 8 (mid-measure) -> Should NOT raise ValueError anymore, but snap
        harmony = Harmony(
            (0, (0, (4, 3))),
            (8, (5, (4, 3)))
        )
        # Should succeed now
        ls = LeadSheet(
            MeterChanges((0, (4, 2, 2))),
            TempoChanges((0, (120,))),
            KeyChanges((0, (0, (2, 2, 1, 2, 2, 2)))),
            harmony,
            Melody(),
            16
        )
        # Check if it snapped to nearest downbeat (8 snaps to 16? or 0? 8/16 = 0.5 -> 0 or 1. round(0.5) is 0 in Py3)
        # 8 is exactly half. round(0.5) -> 0.
        # So it should replace the chord at 0.
        # The harmony list should effectively have the last chord win at 0.
        # harmony input: C at 0, F at 8.
        # F at 8 snaps to F at 0.
        # Result: F at 0.
        self.assertEqual(len(ls[3]), 1)
        self.assertEqual(ls[3][0][0], 0)
        self.assertEqual(ls[3][0][1], harmony[1][1]) # Should be the second chord (F)

        # Test snapping to next measure
        harmony2 = Harmony(
            (0, (0, (4, 3))),
            (12, (5, (4, 3))) # 12/16 = 0.75 -> 1. Snaps to 16.
        )
        ls2 = LeadSheet(
            MeterChanges((0, (4, 2, 2))),
            TempoChanges((0, (120,))),
            KeyChanges((0, (0, (2, 2, 1, 2, 2, 2)))),
            harmony2,
            Melody(),
            32
        )
        # Should have C at 0, F at 16.
        self.assertEqual(len(ls2[3]), 2)
        self.assertEqual(ls2[3][0], (0, harmony2[0][1]))
        self.assertEqual(ls2[3][1], (16, harmony2[1][1]))
