import gzip
import json
import os
import pathlib
import shutil
import tempfile
from enum import Enum
from io import BytesIO

import pretty_midi

from .align import create_beat_to_time_fn
from .assets import retrieve_asset

_TICKS_PER_SECOND = 4096
_QUANTIZE = lambda t: round(t * _TICKS_PER_SECOND) / _TICKS_PER_SECOND
_SEGMENT_MIDI_PITCH = 75


class Split(Enum):
    """Enumeration representing data splits."""
    TRAIN = 0
    VALID = 1
    TEST = 2


class HooktheoryConfig(Enum):
    """Enumeration representing Hooktheory configurations."""
    MELODY_TRANSCRIPTION = 0


class HooktheoryAlignment(Enum):
    """Enumeration representing Hooktheory alignment types."""
    USER = 0
    REFINED = 1


class Note:
    """
    Represents a musical note with onset, pitch, and optional offset.
    """
    def __init__(self, onset, pitch, offset=None):
        """
        Initializes a Note object.

        Args:
            onset (float): The start time of the note in seconds.
            pitch (int): The MIDI pitch of the note (0-127).
            offset (float, optional): The end time of the note in seconds. Defaults to None.

        Raises:
            TypeError: If types of arguments are incorrect.
            ValueError: If onset is negative, offset is before onset, or pitch is out of range.
        """
        if not isinstance(onset, float):
            raise TypeError()
        if not isinstance(pitch, int):
            raise TypeError()
        if offset is not None and not isinstance(offset, float):
            raise TypeError()
        if onset < 0:
            raise ValueError("Onset is negative")
        if offset is not None and offset <= onset:
            raise ValueError("Offset is before onset")
        if pitch < 0 or pitch >= 128:
            raise ValueError("Pitch is outside of MIDI range")
        self.onset = _QUANTIZE(onset)
        self.pitch = pitch
        self.offset = None if offset is None else _QUANTIZE(offset)


class MelodyTranscriptionExample:
    """
    Represents a melody transcription example including the audio segment and melody notes.
    """
    def __init__(self, segment_start, segment_end, melody, uid=None, audio_tag=None):
        """
        Initializes a MelodyTranscriptionExample.

        Args:
            segment_start (float): Start time of the segment in seconds.
            segment_end (float): End time of the segment in seconds.
            melody (list[Note]): List of Note objects representing the melody.
            uid (str, optional): Unique identifier for the example. Defaults to None.
            audio_tag (str, optional): Tag identifying the audio source. Defaults to None.

        Raises:
            TypeError: If argument types are incorrect.
            ValueError: If time ranges are invalid or melody notes are not strictly monophonic/within segment.
        """
        if not isinstance(segment_start, float):
            raise TypeError()
        if not isinstance(segment_end, float):
            raise TypeError()
        if not all(isinstance(n, Note) for n in melody):
            raise TypeError()
        if segment_start < 0:
            raise ValueError("Segment start is negative")
        if segment_end <= segment_start:
            raise ValueError("Segment end before segment start")

        segment_start = _QUANTIZE(segment_start)
        segment_end = _QUANTIZE(segment_end)

        melody = sorted(melody, key=lambda n: (n.onset, n.pitch, n.offset))
        if any((n.onset < segment_start or n.onset > segment_end) for n in melody):
            raise ValueError("Onset outside of segment range")
        if any(
            n.offset is not None
            and (n.offset < segment_start or n.offset > segment_end)
            for n in melody
        ):
            raise ValueError("Offset outside of segment range")
        for i in range(len(melody) - 1):
            if melody[i].onset == melody[i + 1].onset:
                raise ValueError("Simultaneous onsets detected")
            if melody[i].offset is not None and melody[i].offset > melody[i + 1].onset:
                raise ValueError("Notes are not monophonic")

        self.segment_start = segment_start
        self.segment_end = segment_end
        self.melody = melody
        self.uid = uid
        self.audio_tag = audio_tag

    @classmethod
    def from_midi(
        cls, midi, segment_start=None, segment_end=None, uid=None, audio_tag=None
    ):
        """
        Creates a MelodyTranscriptionExample from a MIDI object or file.

        Args:
            midi (pretty_midi.PrettyMIDI or str or pathlib.Path or bytes): The MIDI data or file path.
            segment_start (float, optional): Start of the segment. If None, inferred from special drum notes.
            segment_end (float, optional): End of the segment. If None, inferred from special drum notes.
            uid (str, optional): Unique identifier.
            audio_tag (str, optional): Audio tag.

        Returns:
            MelodyTranscriptionExample: The created example.

        Raises:
            ValueError: If segment boundaries cannot be determined.
        """
        midi = as_pretty_midi(midi)
        segment = []
        melody = []
        for i in midi.instruments:
            for n in i.notes:
                if i.is_drum and n.pitch == _SEGMENT_MIDI_PITCH:
                    segment.append(n.start)
                elif not i.is_drum:
                    melody.append(Note(onset=n.start, pitch=n.pitch, offset=n.end))

        if segment_start is None or segment_end is None:
            if len(segment) != 2:
                raise ValueError("Unknown segment")
            segment_start, segment_end = sorted(segment)

        return cls(
            segment_start=segment_start,
            segment_end=segment_end,
            melody=melody,
            uid=uid,
            audio_tag=audio_tag,
        )

    def to_midi(self, velocity=100):
        """
        Converts the example back to a MIDI file (bytes).

        Args:
            velocity (int): MIDI velocity for the notes. Defaults to 100.

        Returns:
            bytes: The binary content of the MIDI file.
        """
        midi = pretty_midi.PrettyMIDI(resolution=_TICKS_PER_SECOND, initial_tempo=60.0)

        segment = pretty_midi.Instrument(0, is_drum=True, name="SEGMENT")
        for t in [self.segment_start, self.segment_end]:
            segment.notes.append(
                pretty_midi.Note(
                    start=t,
                    end=t + (1 / _TICKS_PER_SECOND),
                    pitch=_SEGMENT_MIDI_PITCH,
                    velocity=127,
                )
            )

        melody = pretty_midi.Instrument(0, name="MELODY")
        for i, n in enumerate(self.melody):
            offset = n.offset
            if offset is None:
                try:
                    offset = self.melody[i + 1].onset
                except IndexError:
                    offset = n.onset + 1
            melody.notes.append(
                pretty_midi.Note(
                    start=n.onset, end=offset, pitch=n.pitch, velocity=velocity
                )
            )

        midi.instruments = [segment, melody]

        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        try:
            midi.write(temp_path)
            with open(temp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


_CONFIG_TO_TAGS = {
    HooktheoryConfig.MELODY_TRANSCRIPTION: {
        "require": ["AUDIO_AVAILABLE", "MELODY"],
        # NOTE: Tempo changes are weird on Hooktheory and likely imply a bad alignment
        "deny": ["TEMPO_CHANGES"],
    },
}


def as_pretty_midi(midi):
    """
    Converts input into a pretty_midi.PrettyMIDI object.

    Args:
        midi (bytes, str, pathlib.Path, or pretty_midi.PrettyMIDI): Input MIDI data or path.

    Returns:
        pretty_midi.PrettyMIDI: The parsed MIDI object.

    Raises:
        TypeError: If the input type is not supported.
    """
    if isinstance(midi, bytes):
        midi = pretty_midi.PrettyMIDI(BytesIO(midi))
    elif isinstance(midi, str) or isinstance(midi, pathlib.Path):
        midi = pretty_midi.PrettyMIDI(str(midi))
    elif isinstance(midi, pretty_midi.PrettyMIDI):
        pass
    else:
        raise TypeError()
    return midi


def load_hooktheory_raw(
    config=HooktheoryConfig.MELODY_TRANSCRIPTION,
    alignment=HooktheoryAlignment.REFINED,
    additional_required_tags=[],
    additional_denied_tags=[],
):
    """
    Loads and filters the raw Hooktheory dataset.

    Args:
        config (HooktheoryConfig or str): Configuration for filtering the dataset.
        alignment (HooktheoryAlignment or str): The alignment type required.
        additional_required_tags (list): Additional tags that must be present.
        additional_denied_tags (list): Additional tags that must not be present.

    Returns:
        dict: A dictionary containing the filtered Hooktheory data.

    Raises:
        ValueError: If an invalid tag is requested or found.
    """
    if isinstance(config, str):
        config = HooktheoryConfig[config.upper().strip()]
    if isinstance(alignment, str):
        alignment = HooktheoryAlignment[alignment.upper().strip()]

    # Build required tags list
    require = _CONFIG_TO_TAGS[config]["require"]
    require = require + additional_required_tags
    if alignment is not None:
        require.append(
            "USER_ALIGNMENT"
            if alignment == HooktheoryAlignment.USER
            else "REFINED_ALIGNMENT"
        )

    # Build denied tags list
    deny = _CONFIG_TO_TAGS[config]["deny"]
    deny = deny + additional_denied_tags

    # Load dataset
    with gzip.open(retrieve_asset("HOOKTHEORY"), "r") as f:
        hooktheory = json.load(f)

    # Check tags
    all_tags = set()
    for attrs in hooktheory.values():
        for tag in attrs["tags"]:
            all_tags.add(tag)
    for tag in require + deny:
        if tag not in all_tags:
            raise ValueError(f"Invalid tag: {tag}")

    # Filter dataset
    hooktheory = {
        k: v
        for k, v in hooktheory.items()
        if all(tag in v["tags"] for tag in require)
        and all(tag not in v["tags"] for tag in deny)
    }

    return hooktheory


def iter_archive(archive_path):
    """
    Iterates over MIDI files in a compressed archive, yielding MelodyTranscriptionExamples.

    Args:
        archive_path (str or pathlib.Path): Path to the archive file.

    Yields:
        MelodyTranscriptionExample: An example parsed from each MIDI file in the archive.

    Raises:
        ValueError: If duplicate UIDs are found in the archive.
    """
    with tempfile.TemporaryDirectory() as d:
        shutil.unpack_archive(str(archive_path), d)
        midi_paths = list(pathlib.Path(d).glob("*.mid*"))
        uids = [p.stem for p in midi_paths]
        if len(set(uids)) != len(uids):
            raise ValueError("Duplicate UID")
        for p in sorted(midi_paths):
            yield MelodyTranscriptionExample.from_midi(p, uid=p.stem)


def iter_rwc_ryy(vox_only=False):
    """
    Iterates over the RWC RYY dataset examples.

    Args:
        vox_only (bool): If True, iterates over the vocal-only dataset.

    Yields:
        MelodyTranscriptionExample: An example from the dataset.
    """
    asset_tag = "RWC_RYYVOX_MIDI" if vox_only else "RWC_RYY_MIDI"
    for e in iter_archive(retrieve_asset(asset_tag)):
        e.audio_tag = f"RWC_AUDIO_{e.uid}"
        yield e


def iter_hooktheory(
    alignment=HooktheoryAlignment.REFINED,
    split=None,
    default_octave=4,
    tqdm=lambda x: x,
    **kwargs,
):
    """
    Iterates over Hooktheory examples.

    Args:
        alignment (HooktheoryAlignment or str): Alignment type to use.
        split (Split or str, optional): Dataset split to iterate over (TRAIN, VALID, TEST).
        default_octave (int): Default octave for pitch calculation.
        tqdm (callable): Progress bar function.
        **kwargs: Additional arguments passed to `load_hooktheory_raw` (unused here but allowed).

    Yields:
        MelodyTranscriptionExample: An example from Hooktheory.
    """
    if isinstance(alignment, str):
        alignment = HooktheoryAlignment[alignment.upper().strip()]
    if isinstance(split, str):
        split = Split[split.upper().strip()]

    hooktheory_raw = load_hooktheory_raw(
        config=HooktheoryConfig.MELODY_TRANSCRIPTION, alignment=alignment
    )
    if split is not None:
        hooktheory_raw = {
            k: v for k, v in hooktheory_raw.items() if v["split"] == split.name
        }

    for uid, attrs in tqdm(hooktheory_raw.items()):
        youtube_id = attrs["youtube"]["id"]
        assert youtube_id is not None

        alignment_ = attrs["alignment"][alignment.name.lower()]
        assert alignment_ is not None and len(alignment_["times"]) >= 2
        beat_to_time = create_beat_to_time_fn(alignment_["beats"], alignment_["times"])
        segment_start = float(beat_to_time(0))
        segment_end = float(beat_to_time(attrs["annotations"]["num_beats"]))

        melody = attrs["annotations"]["melody"]
        assert melody is not None and len(melody) > 0
        melody = [
            Note(
                onset=float(beat_to_time(n["onset"])),
                pitch=(1 + default_octave + n["octave"]) * 12 + n["pitch_class"],
                offset=float(beat_to_time(n["offset"])),
            )
            for n in melody
        ]

        yield MelodyTranscriptionExample(
            uid=uid,
            audio_tag=f"YOUTUBE_{youtube_id}",
            segment_start=segment_start,
            segment_end=segment_end,
            melody=melody,
        )
