import unittest

import numpy as np

from .internal import (
    Chord,
    Harmony,
    Key,
    KeyChanges,
    Melody,
    Meter,
    MeterChanges,
    Note,
    Tempo,
    TempoChanges,
    _InstantEventList,
    _SustainedEventList,
)


class TestInternal(unittest.TestCase):
    def test_meter(self):
        ms = Meter(4, 2, 2)
        self.assertTrue(isinstance(ms, Meter))
        self.assertTrue(isinstance(ms, tuple))
        self.assertEqual(Meter(*ms), ms)
        self.assertEqual(ms, (4, 2, 2))
        self.assertEqual(Meter(4, 2, 2).as_lily(), ("4", "4"))
        self.assertEqual(Meter(3, 2, 2).as_lily(), ("3", "4"))
        with self.assertRaises(NotImplementedError):
            Meter(4, 2, 1)

    def test_tempo(self):
        ts = Tempo(120)
        self.assertTrue(isinstance(ts, Tempo))
        self.assertTrue(isinstance(ts, tuple))
        self.assertEqual(len(ts), 1)
        self.assertEqual(Tempo(*ts), ts)
        ms = Meter(4, 2, 2)
        self.assertEqual(ts.as_lily(ms), ("4", "120"))
        self.assertEqual(
            Tempo(60).as_lily(Meter(3, 2, 2)),
            (
                "4",
                "60",
            ),
        )
        with self.assertRaises(TypeError):
            Tempo(120.5)
        with self.assertRaises(ValueError):
            Tempo(0)
        with self.assertRaises(ValueError):
            Tempo(-1)

    def test_key(self):
        ks = Key(0, (2, 2, 1, 2, 2, 2))
        self.assertTrue(isinstance(ks, Key))
        self.assertTrue(isinstance(ks, tuple))
        self.assertEqual(len(ks), 2)
        self.assertEqual(Key(*ks), ks)
        self.assertEqual(ks.as_lily(), ("c", "major"))
        self.assertEqual(Key(10, (2, 1, 2, 2, 1, 2)).as_lily(), ("bes", "minor"))
        with self.assertRaises(TypeError):
            Key("0", (2, 2, 1, 2, 2, 2))
        with self.assertRaises(TypeError):
            Key(0, "0")
        with self.assertRaises(ValueError):
            Key(0, (0, 2, 2, 1, 2, 2, 2))
        with self.assertRaises(ValueError):
            Key(0, (-1, 2, 2, 1, 2, 2, 2))
        with self.assertRaises(ValueError):
            Key(0, (2, 2, 1, 2, 2, 2, 1))

    def test_note(self):
        ns = Note(0, 0)
        self.assertTrue(isinstance(ns, Note))
        self.assertTrue(isinstance(ns, tuple))
        self.assertEqual(len(ns), 2)
        self.assertEqual(Note(*ns), ns)
        ks = Key(0, (2, 2, 1, 2, 2, 2))
        self.assertEqual(ns.as_lily(ks), ("c", "'"))
        self.assertEqual(
            Note(1, -1).as_lily(Key(11, (2, 2, 1, 2, 2, 2))),
            ("cis", ""),
        )
        # Test as_midi_pitch
        # C4 (middle C) -> MIDI 60
        # internal.Note(pc, octave) -> octave 0 is C4 (midi 60) based on default implementation?
        # Note implementation: 12 + (12 * (octave_0 + self[1])) + self[0]
        # octave_0 defaults to 4.
        # So Note(0, 0) -> 12 + 12*4 + 0 = 60.
        self.assertEqual(Note(0, 0).as_midi_pitch(), 60)
        self.assertEqual(Note(0, 1).as_midi_pitch(), 72)
        self.assertEqual(Note(0, -1).as_midi_pitch(), 48)
        self.assertEqual(Note(1, 0).as_midi_pitch(), 61)

        with self.assertRaises(TypeError):
            Note("0", 0)
        with self.assertRaises(TypeError):
            Note(0, "0")

    def test_chord(self):
        cs = Chord(0, (4, 3))
        self.assertTrue(isinstance(cs, Chord))
        self.assertTrue(isinstance(cs, tuple))
        self.assertEqual(len(cs), 2)
        self.assertEqual(Chord(*cs), cs)
        ks = Key(0, (2, 2, 1, 2, 2, 2))
        self.assertEqual(cs.as_lily(ks), ("c", ""))
        self.assertEqual(Chord(None, None).as_lily(ks), ("r", ""))

        # Test as_midi_pitches
        # C major (C E G) at octave 3
        # internal.Chord(root, intervals)
        # as_midi_pitches(octave_0=3) -> 12 + 12*3 + chord_pitches
        # chord_pitches = [0, 4, 7]
        # base = 48. [48, 52, 55]
        self.assertEqual(Chord(0, (4, 3)).as_midi_pitches(), [48, 52, 55])
        self.assertEqual(Chord(0, (3, 4)).as_midi_pitches(octave_0=4), [60, 63, 67])
        self.assertEqual(Chord(None, None).as_midi_pitches(), [])

        with self.assertRaises(TypeError):
            Chord("0", (4, 3))
        with self.assertRaises(TypeError):
            Chord(0, "0")
        with self.assertRaises(ValueError):
            Chord(0, (0, 4, 3))
        with self.assertRaises(ValueError):
            Chord(0, (-1, 4, 3))

    def test_meter_changes(self):
        mc = MeterChanges((0, (4, 2, 2)))
        self.assertTrue(isinstance(mc, MeterChanges))
        self.assertTrue(isinstance(mc, tuple))
        self.assertTrue(all(isinstance(k, Meter) for _, k in mc))
        self.assertEqual(len(mc), 1)
        self.assertEqual(MeterChanges(*mc), mc)
        with self.assertRaises(ValueError):
            self.assertEqual(
                MeterChanges(
                    (1, (4, 2, 2)),
                    (0, (4, 2, 2)),
                    (0, (4, 2, 2)),
                ),
                mc,
            )

    def test_tempo_changes(self):
        tc = TempoChanges((0, (120,)))
        self.assertTrue(isinstance(tc, TempoChanges))
        self.assertTrue(isinstance(tc, tuple))
        self.assertTrue(all(isinstance(k, Tempo) for _, k in tc))
        self.assertEqual(len(tc), 1)
        self.assertEqual(TempoChanges(*tc), tc)

    def test_key_changes(self):
        kc = KeyChanges(
            (0, (0, (2, 2, 1, 2, 2, 2))),
        )
        self.assertTrue(isinstance(kc, KeyChanges))
        self.assertTrue(isinstance(kc, tuple))
        self.assertTrue(all(isinstance(k, Key) for _, k in kc))
        self.assertEqual(len(kc), 1)
        self.assertEqual(KeyChanges(*kc), kc)
        self.assertEqual(len(kc), 1)
        self.assertEqual(tuple(sorted(kc)), kc)
        with self.assertRaises(TypeError):
            KeyChanges(
                (0.5, (0, (2, 2, 1, 2, 2, 2))),
            )
        with self.assertRaises(ValueError):
            KeyChanges(
                (-1, (0, (2, 2, 1, 2, 2, 2))),
            )
        with self.assertRaises(ValueError):
            KeyChanges(
                (0, (0, (2, 2, 1, 2, 2, 2, 12))),
            )
        with self.assertRaises(ValueError):
            KeyChanges(
                (0, (0, (2, 2, 1, 2, 2, 2, 12))),
            )
        with self.assertRaises(ValueError):
            KeyChanges(
                (0, (0, (2, 2, 1, 2, 2, 2))),
                (0, (1, (2, 2, 1, 2, 2, 2))),
            )
        with self.assertRaises(ValueError):
            KeyChanges(
                (0, (0, (2, 2, 1, 2, 2, 2))),
                (4, (0, (2, 2, 1, 2, 2, 2))),
            )
        with self.assertRaises(ValueError):
            KeyChanges(
                (0, (0, (2, 2, 1, 2, 2, 2))),
                (0, (0, (2, 2, 1, 2, 2, 2))),
                (1, (0, (2, 2, 1, 2, 2, 2))),
            )

    def test_harmony(self):
        harmony = Harmony(
            (8, (5, (4, 3))),
            (12, (7, (4, 3))),
            (16, (0, (4, 3))),
        )
        self.assertTrue(isinstance(harmony, Harmony))
        self.assertTrue(isinstance(harmony, tuple))
        self.assertTrue(all(isinstance(c, Chord) for _, c in harmony))
        self.assertEqual(len(harmony), 3)
        self.assertEqual(Harmony(*harmony), harmony)

    def test_melody(self):
        melody = Melody(
            (8, 2, (0, 0)),
            (10, 2, (2, 0)),
            (12, 2, (4, 0)),
            (14, 2, (5, 0)),
            (16, 16, (7, 0)),
        )
        self.assertTrue(isinstance(melody, Melody))
        self.assertTrue(isinstance(melody, tuple))
        self.assertTrue(all(isinstance(n, Note) for _, _, n in melody))
        self.assertEqual(len(melody), 5)
        self.assertEqual(Melody(*melody), melody)

    def test_instant_event_list(self):
        # Unsorted
        with self.assertRaises(ValueError):
            _InstantEventList(Meter, (4, (4, 2, 2)), (0, (4, 2, 2)))

        # Duplicate offset
        with self.assertRaises(ValueError):
            _InstantEventList(Meter, (0, (4, 2, 2)), (0, (3, 2, 2)))

        # Consecutive identical events (should raise ValueError)
        with self.assertRaises(ValueError):
            _InstantEventList(Meter, (0, (4, 2, 2)), (4, (4, 2, 2)))

    def test_sustained_event_list(self):
        # Unsorted
        # Note: _SustainedEventList actually sorts input in __new__.
        # But overlapping checks might fail if unsorted? No, it sorts first.
        # But let's check sorting behavior.
        # Actually _InstantEventList also sorts.
        # Wait, the validation logic in _InstantEventList:
        # instant_events = sorted(instant_events, key=lambda ie: ie[0])
        # So it handles unsorted input gracefully?
        # Let's check test_meter_changes failure case for unsorted.
        # `test_meter_changes` has `self.assertEqual(MeterChanges(..., (1, ...), (0, ...)), mc)` which failed with ValueError.
        # Wait, `MeterChanges` inherits from `_DefinedAtStartInstantEventList` which inherits `_InstantEventList`.
        # `_DefinedAtStartInstantEventList` checks `instant_events[0][0] != 0`.
        # If passed `(1, ...), (0, ...)` it sorts to `(0, ...), (1, ...)`?
        # Let's look at `_InstantEventList.__new__`:
        # `instant_events = sorted(instant_events, key=lambda ie: ie[0])`
        # So sorting happens.
        # `_DefinedAtStartInstantEventList` checks `instant_events[0][0] != 0`.
        # So `(1, ...), (0, ...)` sorted becomes `(0, ...), (1, ...)` which passes `!= 0` check.
        # Why did `test_meter_changes` expect ValueError for unsorted input in my memory?
        # Ah, `test_meter_changes` code:
        # with self.assertRaises(ValueError): self.assertEqual(MeterChanges((1, ...), (0, ...), (0, ...)), mc)
        # It has duplicate `(0, ...)`! That's why it raises ValueError (duplicate offsets).

        # So unsorted input is fine as long as no duplicates.
        # Let's verify overlapping logic for sustained events.

        # Zero duration
        with self.assertRaises(ValueError):
            Melody((0, 0, (0, 0)))

        # Overlap
        with self.assertRaises(ValueError):
            Melody((0, 4, (0, 0)), (2, 4, (2, 0))) # Overlap at 2
