import json
import logging
import os
import pathlib
import tempfile
from enum import Enum
from functools import lru_cache as cache

import numpy as np
import torch
import validators
from scipy.special import softmax

from .align import create_beat_to_time_fn
from .assets import retrieve_asset
from .beat_track import beatnet_beat_track
from .modules import EncOnlyTransducer, IdentityEncoder, TransformerEncoder
from .representations import Handcrafted
from .theory import (
    Chord,
    Harmony,
    KeyChanges,
    LeadSheet,
    Melody,
    MeterChanges,
    Note,
    TempoChanges,
    estimate_key_changes,
)
from .utils import decode_audio, retrieve_audio_bytes


class InputFeats(Enum):
    """
    Enum representing input feature types.
    """
    HANDCRAFTED = 0


class Task(Enum):
    """
    Enum representing transcription tasks.
    """
    MELODY = 0
    HARMONY = 1


class Model(Enum):
    """
    Enum representing model architectures.
    """
    LINEAR = 0
    TRANSFORMER = 1


class Status(Enum):
    """
    Enum representing the status of the transcription process.
    """
    FETCHING_AUDIO = 0
    DETECTING_BEATS = 1
    EXTRACTING_FEATURES = 2
    TRANSCRIBING = 3
    FORMATTING = 4
    DONE = 5


_INPUT_TO_FRAME_RATE = {
    InputFeats.HANDCRAFTED: 16000 / 512,
}
_INPUT_TO_DIM = {
    InputFeats.HANDCRAFTED: 229,
}
_CHUNK_DURATION_EDGE = 23.75
_TERTIARIES_PER_BEAT = 4
_MELODY_PITCH_MIN = 21
_HARMONY_FAMILIES = ["", "m", "m7", "7", "maj7", "sus", "dim", "aug"]
_FAMILY_TO_INTERVALS = {
    "": (4, 3),
    "m": (3, 4),
    "m7": (3, 4, 3),
    "7": (4, 3, 3),
    "maj7": (4, 3, 4),
    "sus": (5, 2),
    "dim": (3, 3),
    "aug": (4, 4),
}
_TASK_TO_VOCAB_SIZE = {Task.MELODY: 89, Task.HARMONY: 97}
_MAX_TERTIARIES_PER_CHUNK = 384


@cache()
def _init_extractor(input_feats):
    """
    Initializes and caches feature extractors.

    Args:
        input_feats (InputFeats): The type of input features to extract.

    Returns:
        FeatureExtractor: An instance of the requested feature extractor.

    Raises:
        ValueError: If input_feats is invalid.
    """
    if input_feats == InputFeats.HANDCRAFTED:
        extractor = Handcrafted()
    else:
        raise ValueError()
    return extractor


@cache()
def _init_model(task, input_feats, model):
    """
    Initializes and caches the transcription model.

    Args:
        task (Task): The transcription task (MELODY or HARMONY).
        input_feats (InputFeats): The input feature type the model expects.
        model (Model): The model architecture.

    Returns:
        torch.nn.Module: The initialized model loaded with pretrained weights.

    Raises:
        NotImplementedError: If Model.LINEAR is requested.
        ValueError: If configuration is invalid.
    """
    if model == Model.LINEAR:
        # NOTE: Just need to catalogue these configs / weights
        raise NotImplementedError()

    asset_prefix = f"atoscore_V02_{input_feats.name}_{task.name}"
    with open(retrieve_asset(f"{asset_prefix}_CFG", log=False), "r") as f:
        cfg = json.load(f)
    assert cfg["src_max_len"] == _MAX_TERTIARIES_PER_CHUNK

    src_dim = _INPUT_TO_DIM[input_feats]
    output_dim = _TASK_TO_VOCAB_SIZE[task]

    if cfg["model"] == "probe":
        model = EncOnlyTransducer(
            output_dim,
            src_emb_mode="identity",
            src_vocab_size=None,
            src_dim=src_dim,
            src_emb_dim=None,
            src_pos_emb=False,
            src_dropout_p=0.0,
            enc_cls=IdentityEncoder,
            enc_kwargs={},
        )
    elif cfg["model"] == "transformer":
        model = EncOnlyTransducer(
            output_dim,
            src_emb_mode="project",
            src_vocab_size=None,
            src_dim=src_dim,
            src_emb_dim=512,
            src_pos_emb="pos_emb" in cfg["hacks"],
            src_dropout_p=0.1,
            enc_cls=TransformerEncoder,
            enc_kwargs={
                "model_dim": 512,
                "num_heads": 8,
                "num_layers": 4 if "4layers" in cfg["hacks"] else 6,
                "feedforward_dim": 2048,
                "dropout_p": 0.1,
            },
        )
    else:
        raise ValueError()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.load_state_dict(
        torch.load(
            retrieve_asset(f"{asset_prefix}_MODEL", log=False), map_location=device
        )
    )
    model.eval()
    return model


def _closest_idx(x, l):
    assert len(l) > 0
    return int(np.argmin([abs(li - x) for li in l]) + 1e-6)


def _beat_tracking_with_hints(
    audio_path_or_bytes,
    segment_start_hint,
    segment_end_hint,
    segment_hints_are_downbeats,
    beats_per_measure_hint,
    beats_per_minute_hint,
    beat_detection_padding,
    legacy_behavior,
):
    # Decode a segment of the audio
    beat_detection_start = 0.0 if segment_start_hint is None else segment_start_hint
    beat_detection_start = max(beat_detection_start - beat_detection_padding, 0.0)
    beat_detection_end = None if segment_end_hint is None else segment_end_hint
    beat_detection_end = (
        None
        if beat_detection_end is None
        else beat_detection_end + beat_detection_padding
    )
    if legacy_behavior:
        l = segment_start_hint - beat_detection_padding
        r = segment_start_hint + _CHUNK_DURATION_EDGE + beat_detection_padding
        sr, audio = decode_audio(audio_path_or_bytes)
        audio_duration = audio.shape[0] / sr
        l, r = [round(t * sr) for t in (l, r)]
        l = max(0, l)
        r = min(audio.shape[0], r)
        assert r > l
        audio = audio[l:r]
    else:
        sr, audio = decode_audio(
            audio_path_or_bytes,
            offset=beat_detection_start,
            duration=None
            if beat_detection_end is None
            else beat_detection_end - beat_detection_start,
        )

    # Run beat detection on segment
    first_downbeat_idx, beats_per_measure, beats = beatnet_beat_track(
        sr,
        audio,
        beats_per_bar=beats_per_measure_hint
        if beats_per_measure_hint is not None
        else [3, 4],
        beats_per_minute_hint=beats_per_minute_hint,
    )
    if first_downbeat_idx is None or beats_per_measure is None or len(beats) == 0:
        raise ValueError("Audio too short to detect time signature")
    assert first_downbeat_idx >= 0 and first_downbeat_idx < beats_per_measure
    assert beats_per_measure in [3, 4]
    beats = [beat_detection_start + t for t in beats]
    downbeats = [
        t for i, t in enumerate(beats) if i % beats_per_measure == first_downbeat_idx
    ]
    assert len(beats) > 0
    assert len(downbeats) > 0

    # Convert beats into tertiary (sixteenth note) timestamps
    # NOTE: Yes, this is super ugly, but sometimes you gotta do what you gotta do
    beat_to_time_fn = create_beat_to_time_fn(list(range(len(beats))), beats)
    tertiaries = np.arange(0, len(beats) - 1 + 1e-6, 1 / _TERTIARIES_PER_BEAT)
    assert tertiaries.shape[0] == (len(beats) - 1) * _TERTIARIES_PER_BEAT + 1
    tertiaries_centered = tertiaries - (1 / _TERTIARIES_PER_BEAT) / 2
    tertiaries_times = beat_to_time_fn(tertiaries_centered)
    tertiaries_times = np.maximum(tertiaries_times, 0.0)
    tertiaries_times = np.minimum(tertiaries_times, beats[-1])

    # Find first downbeat of the song from optional hint
    if segment_start_hint is None:
        segment_start = downbeats[0]
    else:
        if segment_hints_are_downbeats:
            segment_start = segment_start_hint
        else:
            segment_start = downbeats[_closest_idx(segment_start_hint, downbeats)]
    segment_start_downbeat = _closest_idx(segment_start, beats)
    downbeats = [
        t
        for i, t in enumerate(beats)
        if i % beats_per_measure == segment_start_downbeat % beats_per_measure
    ]

    # Find last downbeat of the song from optional hint
    if segment_end_hint is None:
        segment_end = downbeats[-1]
    else:
        if segment_hints_are_downbeats:
            segment_end = segment_end_hint
        else:
            segment_end = downbeats[_closest_idx(segment_end_hint, downbeats)]
    segment_end_beat = _closest_idx(segment_end, beats)
    if segment_end_beat == segment_start_downbeat:
        raise ValueError("Specified segment is too short (<1 measure).")

    # NOTE on naming conventions: segment_start_downbeat *is* an (internally-consistent)
    # downbeat, but segment_end_beat may not be (if segment_hints_are_downbeats is true
    # and user specifies an inaccurate timestamp).

    if legacy_behavior:
        beats = beats[segment_start_downbeat:]

        beat_to_time_fn = create_beat_to_time_fn(list(range(len(beats))), beats)
        tertiaries = np.arange(0, len(beats) + 1e-6, 1 / _TERTIARIES_PER_BEAT)
        assert tertiaries.shape[0] > 0
        tertiaries -= (1 / _TERTIARIES_PER_BEAT) / 2
        tertiaries_times = beat_to_time_fn(tertiaries)
        tertiaries_times = np.maximum(tertiaries_times, 0.0)
        tertiaries_times = np.minimum(tertiaries_times, audio_duration)
        segment_offset = tertiaries_times[0]
        tertiaries_times = [
            t
            for t in tertiaries_times
            if t < segment_offset + _CHUNK_DURATION_EDGE
        ]
        segment_duration = tertiaries_times[-1] - segment_offset
        tertiaries = (
            np.arange(len(tertiaries_times)) * (1 / _TERTIARIES_PER_BEAT)
        ).tolist()

        segment_end_beat = (
            segment_start_downbeat + len(tertiaries) / _TERTIARIES_PER_BEAT
        )
        if abs(segment_end_beat - round(segment_end_beat)) < 1e-6:
            segment_end_beat = round(segment_end_beat)
        else:
            segment_end_beat = int(np.ceil(segment_end_beat) + 1e-6)
        tertiaries = np.array(tertiaries)
        tertiaries_times = np.array(tertiaries_times)

    return (
        beats_per_measure,
        list(range(len(beats))),
        beats,
        tertiaries,
        tertiaries_times,
        segment_start_downbeat,
        segment_end_beat,
    )


def _split_into_chunks(
    tertiaries_times,
    measures_per_chunk,
    beats_per_measure,
    segment_start_downbeat,
    segment_end_beat,
    avoid_chunking_if_possible,
    legacy_behavior,
):
    chunks = []

    if legacy_behavior:
        chunk_slice = slice(None, None)
        chunk_tertiaries_times = tertiaries_times[chunk_slice]
        duration = chunk_tertiaries_times[-1] - chunk_tertiaries_times[0]
        assert duration > 0 and duration <= _CHUNK_DURATION_EDGE
        chunks.append(chunk_slice)
    else:
        beats_per_chunk = beats_per_measure * measures_per_chunk
        if avoid_chunking_if_possible:
            chunk_start_tertiary = segment_start_downbeat * _TERTIARIES_PER_BEAT
            chunk_end_tertiary = (segment_end_beat * _TERTIARIES_PER_BEAT) + 1
            chunk_slice = slice(chunk_start_tertiary, chunk_end_tertiary)
            chunk_tertiaries_times = tertiaries_times[chunk_slice]
            duration = chunk_tertiaries_times[-1] - chunk_tertiaries_times[0]
            if duration <= _CHUNK_DURATION_EDGE:
                beats_per_chunk = segment_end_beat

        for b in range(segment_start_downbeat, segment_end_beat, beats_per_chunk):
            chunk_start_tertiary = b * _TERTIARIES_PER_BEAT
            chunk_end_tertiary = ((b + beats_per_chunk) * _TERTIARIES_PER_BEAT) + 1
            chunk_end_tertiary = min(
                chunk_end_tertiary, (segment_end_beat * _TERTIARIES_PER_BEAT) + 1
            )
            assert chunk_end_tertiary <= tertiaries_times.shape[0]
            chunk_slice = slice(chunk_start_tertiary, chunk_end_tertiary)
            chunk_tertiaries_times = tertiaries_times[chunk_slice]
            duration = chunk_tertiaries_times[-1] - chunk_tertiaries_times[0]
            assert duration > 0
            if duration > _CHUNK_DURATION_EDGE:
                raise NotImplementedError(
                    "Dynamic chunking not implemented. Try halving measures_per_chunk."
                )
            chunks.append(chunk_slice)

    return chunks


def _extract_features(
    audio_path_or_bytes, input_feats, tertiaries_times, chunks_tertiaries, tqdm
):
    tertiary_diff_frames = np.diff(tertiaries_times) * _INPUT_TO_FRAME_RATE[input_feats]
    if np.any(tertiary_diff_frames.astype(np.int64) == 0):
        raise ValueError("Tempo too fast for beat-informed feature resampling")

    extractor = _init_extractor(input_feats)

    moments = None
    if input_feats == InputFeats.HANDCRAFTED:
        moments = np.load(
            retrieve_asset(f"atoscore_V02_{input_feats.name}_MOMENTS", log=False)
        )

    audio_path = None
    temp_path = None
    try:
        if isinstance(audio_path_or_bytes, bytes):
            fd, temp_path = tempfile.mkstemp()
            with os.fdopen(fd, "wb") as f:
                f.write(audio_path_or_bytes)
            audio_path = temp_path
        else:
            audio_path = audio_path_or_bytes

        for chunk_slice in tqdm(chunks_tertiaries):
            chunk_tertiaries_times = tertiaries_times[chunk_slice]
            offset = chunk_tertiaries_times[0]
            duration = chunk_tertiaries_times[-1] - offset
            assert duration <= _CHUNK_DURATION_EDGE
            try:
                fr, feats = extractor(audio_path, offset=offset, duration=duration)
            except Exception as e:
                logging.error(f"Error extracting features from {audio_path} at offset {offset} duration {duration}: {e}")
                raise e
            # Vectorized beat resampling (~6x faster than loop)
            # Calculate sample indices for each tertiary
            indices = ((chunk_tertiaries_times - offset) * fr).astype(np.int64)
            # Ensure indices are valid and calculate segment lengths
            lengths = np.diff(indices)
            if np.any(lengths <= 0):
                # Fallback or strict check - original code asserted e > s
                raise ValueError("Beat intervals too small for resampling")

            # Use reduceat to compute sums over intervals [indices[i]:indices[i+1]]
            # We slice [:-1] because reduceat includes the last segment from indices[-1] to end
            beat_sums = np.add.reduceat(feats, indices, axis=0)[:-1]

            # Compute means
            beat_resampled = beat_sums / lengths[:, np.newaxis]

            # Normalize handcrafted features (after beat resampling)
            if moments is not None:
                beat_resampled -= moments[0]
                beat_resampled /= moments[1]

            yield beat_resampled
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logging.warning(f"Failed to remove temporary file {temp_path}: {e}")


def _transcribe_chunks(
    melody_features, harmony_features, input_feats, detect_melody, detect_harmony
):
    melody_logits = None
    harmony_logits = None
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    BATCH_SIZE = 32

    melody_model = None
    if detect_melody:
        if melody_features is None:
            raise ValueError("Melody features required for detection")
        melody_model = _init_model(Task.MELODY, input_feats, Model.TRANSFORMER)
        melody_logits = []

    harmony_model = None
    if detect_harmony:
        if harmony_features is None:
            raise ValueError("Harmony features required for detection")
        harmony_model = _init_model(Task.HARMONY, input_feats, Model.TRANSFORMER)
        harmony_logits = []

    def batch_generator(gen, batch_size):
        batch = []
        for item in gen:
            batch.append(item)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    # Helper to process a single batch
    def process_batch(model, logits_list, batch_chunks, device):
        curr_batch_size = len(batch_chunks)
        # Optimize: Pad only to the max length in the current batch
        max_len = max([c.shape[0] for c in batch_chunks])
        batch_src = np.zeros(
            (
                max_len,
                curr_batch_size,
                batch_chunks[0].shape[1],
            ),
            dtype=np.float32,
        )
        batch_src_len = np.zeros(curr_batch_size, dtype=np.int64)

        for j, src in enumerate(batch_chunks):
            l = src.shape[0]
            batch_src[:l, j, :] = src
            batch_src_len[j] = l

        batch_src = torch.from_numpy(batch_src).to(device)
        batch_src_len = torch.from_numpy(batch_src_len).to(device)

        with torch.inference_mode():
            if device.type == "cuda":
                with torch.amp.autocast("cuda"):
                    batch_logits = model(batch_src, batch_src_len, None, None)
            else:
                batch_logits = model(batch_src, batch_src_len, None, None)

        batch_logits_np = batch_logits.float().cpu().numpy()
        for j in range(curr_batch_size):
            logits_list.append(batch_logits_np[: batch_src_len[j], j])

    # Case 1: Single source (or same generator)
    single_source = (melody_features is harmony_features) and (melody_features is not None)

    if single_source:
        for batch_chunks in batch_generator(melody_features, BATCH_SIZE):
            if detect_melody:
                process_batch(melody_model, melody_logits, batch_chunks, device)
            if detect_harmony:
                process_batch(harmony_model, harmony_logits, batch_chunks, device)
    else:
        # Case 2: Separate sources
        gen_m = batch_generator(melody_features, BATCH_SIZE) if detect_melody else None
        gen_h = batch_generator(harmony_features, BATCH_SIZE) if detect_harmony else None

        if detect_melody and detect_harmony:
            for batch_m, batch_h in zip(gen_m, gen_h):
                process_batch(melody_model, melody_logits, batch_m, device)
                process_batch(harmony_model, harmony_logits, batch_h, device)
        elif detect_melody:
            for batch_m in gen_m:
                process_batch(melody_model, melody_logits, batch_m, device)
        elif detect_harmony:
            for batch_h in gen_h:
                process_batch(harmony_model, harmony_logits, batch_h, device)

    return melody_logits, harmony_logits


def _format_lead_sheet(
    melody_logits,
    harmony_logits,
    beats_per_measure,
    beats,
    beats_times,
    segment_start_downbeat,
    segment_end_beat,
    total_num_tertiary,
    melody_threshold=None,
    harmony_threshold=None,
):
    def decode(logits, threshold=None):
        if threshold is None:
            preds = np.argmax(logits, axis=-1)
        else:
            probs_nonnull = 1 - softmax(logits, axis=-1)[:, 0]
            preds_nonnull = 1 + np.argmax(logits[:, 1:], axis=-1)
            preds = np.where(probs_nonnull >= threshold, preds_nonnull, 0)
        return preds

    # Decode melody
    if melody_logits is None:
        melody = Melody()
    else:
        melody_logits = np.concatenate(melody_logits, axis=0)
        assert melody_logits.shape[0] == total_num_tertiary
        melody_preds = decode(melody_logits, threshold=melody_threshold)
        melody_onsets = []
        for o, p in enumerate(melody_preds):
            if p != 0:
                assert p >= 1
                p -= 1
                p = (p + _MELODY_PITCH_MIN).tolist()
                melody_onsets.append((o, Note(p % 12, p // 12)))
        melody = []
        for i, (o, n) in enumerate(melody_onsets):
            if i + 1 < len(melody_onsets):
                d = melody_onsets[i + 1][0] - o
            else:
                d = total_num_tertiary - o
            melody.append((o, d, n))
        melody = Melody(*melody)

    # Decode harmony - QUANTIZED TO DOWNBEATS (MEASURES)
    if harmony_logits is None:
        harmony = Harmony()
    else:
        harmony_logits = np.concatenate(harmony_logits, axis=0)
        assert harmony_logits.shape[0] == total_num_tertiary
        harmony_preds = decode(harmony_logits, threshold=harmony_threshold)
        
        harmony = []
        last_chord = None
        
        # Calculate tertiary_per_group (measure length)
        # Meter is hardcoded to (beats_per_measure, 2, 2) later in the function, so we use that.
        tertiary_per_group = beats_per_measure * 4 # 3*4=12 or 4*4=16
        
        for m_start in range(0, total_num_tertiary, tertiary_per_group):
            m_end = min(m_start + tertiary_per_group, total_num_tertiary)
            
            # Get predictions for this measure
            measure_preds = harmony_preds[m_start:m_end]
            if len(measure_preds) == 0: continue

            # Vote for the chord in this measure
            # Filter out 0 (No Chord) if we want? No, 0 is a valid state (Silence).
            counts = np.bincount(measure_preds)
            c = np.argmax(counts)
            
            if c != 0:
                assert c >= 1
                c -= 1
                # c is index in vocabulary
                idx = c
                # Reconstruct chord tuple/object locally to check for change
                # Mapping logic from original code:
                # c = c // len(_HARMONY_FAMILIES), _HARMONY_FAMILIES[...]
                fam_idx = idx % len(_HARMONY_FAMILIES)
                root_idx = idx // len(_HARMONY_FAMILIES)
                
                c_tuple = (
                    root_idx,
                    _HARMONY_FAMILIES[fam_idx],
                )
                chord = Chord(c_tuple[0], _FAMILY_TO_INTERVALS[c_tuple[1]])
                
                if chord != last_chord:
                    harmony.append((m_start, chord))
                last_chord = chord
            else:
                # No Chord / Silence
                chord = None
                if chord != last_chord:
                     harmony.append((m_start, None)) # Explicit N.C.
                last_chord = chord
                
        harmony = Harmony(*harmony)

    # Extract tempo
    measures_bps = []
    for b in range(segment_start_downbeat, segment_end_beat, beats_per_measure):
        m0_time = beats_times[b]
        try:
            mp1_time = beats_times[b + beats_per_measure]
        except IndexError:
            break
        assert mp1_time >= m0_time
        if mp1_time > m0_time:
            bps = beats_per_measure / (mp1_time - m0_time)
            measures_bps.append(bps)
    if len(measures_bps) > 0:
        beats_per_second = np.median(measures_bps)
    else:
        beats_per_second = 2

    meter_changes = MeterChanges((0, (beats_per_measure, 2, 2)))
    tempo_changes = TempoChanges((0, (round(beats_per_second * 60),)))
    try:
        key_changes = estimate_key_changes(meter_changes, harmony, melody)
    except:
        # NOTE: C major by default
        key_changes = KeyChanges((0, (0, (2, 2, 1, 2, 2, 2))))
    lead_sheet = LeadSheet(
        meter_changes, tempo_changes, key_changes, harmony, melody, total_num_tertiary
    )

    assert beats[0] == 0
    segment_beats = [b - segment_start_downbeat for b in beats]

    return lead_sheet, segment_beats, beats_times


def atoscore(
    audio_path_bytes_or_url,
    audio_path_melody=None,
    audio_path_harmony=None,
    segment_start_hint=None,
    segment_end_hint=None,
    measures_per_chunk=8,
    segment_hints_are_downbeats=False,
    beats_per_measure_hint=None,
    beats_per_minute_hint=None,
    detect_melody=True,
    detect_harmony=True,
    melody_threshold=None,
    harmony_threshold=None,
    beat_detection_padding=15.0,
    avoid_chunking_if_possible=True,
    legacy_behavior=False,
    status_change_callback=lambda s: logging.info(s.name),
    return_intermediaries=False,
    tqdm=lambda x: x,
):
    """Main driver function for Sheet Sage: music audio -> lead sheet.

    Parameters
    ----------
    audio_path_bytes_or_url : :class:`pathlib.Path`, bytes, or str
       The filepath, raw bytes, or string URL of the audio to transcribe.
    audio_path_melody : :class:`pathlib.Path`, bytes, or str (optional)
       Specific audio source for melody transcription (e.g., separated vocals).
    audio_path_harmony : :class:`pathlib.Path`, bytes, or str (optional)
       Specific audio source for harmony transcription (e.g., separated backing track).
    segment_start_hint : float or None
       Approximate timestamp of start downbeat (to transcribe a segment of the audio).
    segment_end_hint : float or None
       Approximate timestamp of end downbeat (to transcribe a segment of the audio).
    measures_per_chunk : int
       The number of measures which Sheet Sage transcribes at a time (for best results,
       set to phrase length).
    segment_hints_are_downbeats: bool
       If True, overrides downbeat detection using the specified segment hints (note
       that the hints must be *very* precise for this to work as intended).
    beats_per_measure_hint : int or None
       If specified, overrides time signature detection (4 for "4/4" or 3 for "3/4").
    beats_per_minute_hint : int or None
       If specified, helps the beat detector find the right tempo. Useful if detected
       tempo is a factor of 2 off from real tempo.
    detect_melody : bool
       If False, skips melody transcription.
    detect_harmony : bool
       If False, skips chord recognition.
    melody_threshold : float
       If specified, overrides default melody threshold (0-1, lower for more notes.)
    harmony_threshold : float
       If specified, overrides default harmony threshold (0-1, lower for more chords.)
    beat_detection_padding : float
       Amount of audio padding to use when running beat detection on segment.
    avoid_chunking_if_possible : bool
       If False, uses chunking even for segments shorter than training length.
    legacy_behavior : bool
       If True, ignores segment_end_hint and transcribes exactly one max-length chunk.
    status_change_callback : Callable
       If specified, calls this method upon changes in `Status`.
    return_intermediaries : bool
       If True, returns intermediate high-level results.
    tqdm : Callable
       Progress bar function.

    Returns
    -------
    :class:`atoscore.LeadSheet`
       The generated lead sheet.
    list
       List of segment beat indices.
    list
       List of beat timestamps.
    """
    # Check values
    if segment_start_hint is not None and segment_start_hint < 0:
        raise ValueError("Segment start hint cannot be negative")
    if segment_end_hint is not None and segment_end_hint < 0:
        raise ValueError("Segment end hint cannot be negative")
    if (
        segment_start_hint is not None
        and segment_end_hint is not None
        and segment_end_hint <= segment_start_hint
    ):
        raise ValueError("Segment end hint should be greater than start hint")
    if measures_per_chunk <= 0:
        raise ValueError("Invalid measures per chunk specified")
    if measures_per_chunk > 32:
        raise ValueError("Sheet Sage can only transcribe up to 32 measures per chunk")
    if measures_per_chunk > 24:
        if beats_per_measure_hint == 4:
            raise ValueError("For 4/4 time, max measures per chunk is 24")
    if beats_per_measure_hint is not None and beats_per_measure_hint not in [3, 4]:
        raise ValueError(
            "Currently, Sheet Sage only supports 4/4 and 3/4 time signatures"
        )
    if beat_detection_padding < 0:
        raise ValueError("Beat detection padding cannot be negative")
    input_feats = InputFeats.HANDCRAFTED

    # Disambiguate between URL and file path for string inputs and retrieve URL
    audio_path_or_bytes = audio_path_bytes_or_url
    if isinstance(audio_path_bytes_or_url, str):
        if validators.url(audio_path_bytes_or_url):
            status_change_callback(Status.FETCHING_AUDIO)
            logging.info(f"Retrieving audio from {audio_path_bytes_or_url}")
            audio_path_or_bytes = retrieve_audio_bytes(audio_path_bytes_or_url)
        else:
            logging.info(f"Loading audio from {audio_path_bytes_or_url}")
            audio_path_or_bytes = pathlib.Path(audio_path_bytes_or_url).resolve()
    if (
        isinstance(audio_path_or_bytes, pathlib.Path)
        and not audio_path_or_bytes.exists()
    ):
        raise FileNotFoundError(audio_path_or_bytes)

    # Defaults for specific paths
    if audio_path_melody is None:
        audio_path_melody = audio_path_or_bytes
    if audio_path_harmony is None:
        audio_path_harmony = audio_path_or_bytes

    # Run beat detection
    status_change_callback(Status.DETECTING_BEATS)
    (
        beats_per_measure,
        beats,
        beats_times,
        tertiaries,
        tertiaries_times,
        segment_start_downbeat,
        segment_end_beat,
    ) = _beat_tracking_with_hints(
        audio_path_or_bytes,
        segment_start_hint,
        segment_end_hint,
        segment_hints_are_downbeats,
        beats_per_measure_hint,
        beats_per_minute_hint,
        beat_detection_padding,
        legacy_behavior,
    )

    # Identify suitable chunks for running through transcription model
    if beats_per_measure * measures_per_chunk > 96:
        raise ValueError(
            f"Measures per chunk {measures_per_chunk} is too high for {beats_per_measure}/4 time signature (max beats per chunk is 96)"
        )

    chunks_tertiaries = _split_into_chunks(
        tertiaries_times,
        measures_per_chunk,
        beats_per_measure,
        segment_start_downbeat,
        segment_end_beat,
        avoid_chunking_if_possible,
        legacy_behavior,
    )

    # Extract features
    status_change_callback(Status.EXTRACTING_FEATURES)
    
    # Determine unique inputs to extract features from
    unique_inputs = []
    if detect_melody:
        unique_inputs.append(audio_path_melody)
    if detect_harmony:
        is_duplicate = False
        for inp in unique_inputs:
            if inp is audio_path_harmony or inp == audio_path_harmony:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_inputs.append(audio_path_harmony)

    features_map = {}
    for inp in unique_inputs:
        feats = _extract_features(
            inp, input_feats, tertiaries_times, chunks_tertiaries, tqdm
        )
        # We need a robust way to map back since 'inp' might be unhashable (if list, though unlikely here)
        # But here inputs are likely paths (Path/str) or bytes. All hashable.
        features_map[inp] = feats

    melody_features = features_map[audio_path_melody] if detect_melody else None
    harmony_features = features_map[audio_path_harmony] if detect_harmony else None

    # Transcribe chunks
    status_change_callback(Status.TRANSCRIBING)
    melody_logits, harmony_logits = _transcribe_chunks(
        melody_features, harmony_features, input_feats, detect_melody, detect_harmony
    )

    # Create lead sheet
    status_change_callback(Status.FORMATTING)
    total_num_tertiary = 0
    if melody_logits is not None:
        total_num_tertiary = sum([c.shape[0] for c in melody_logits])
    elif harmony_logits is not None:
        total_num_tertiary = sum([c.shape[0] for c in harmony_logits])

    lead_sheet, segment_beats, segment_beats_times = _format_lead_sheet(
        melody_logits,
        harmony_logits,
        beats_per_measure,
        beats,
        beats_times,
        segment_start_downbeat,
        segment_end_beat,
        total_num_tertiary,
        melody_threshold=melody_threshold,
        harmony_threshold=harmony_threshold,
    )

    status_change_callback(Status.DONE)
    result = lead_sheet, segment_beats, segment_beats_times
    if return_intermediaries:
        result = result + (chunks_tertiaries, melody_logits, harmony_logits)
    return result


if __name__ == "__main__":
    import pathlib
    import uuid
    from argparse import ArgumentParser

    from tqdm import tqdm

    from .utils import engrave

    parser = ArgumentParser()

    parser.add_argument(
        "audio_path_or_url",
        type=str,
        help="The filepath or URL of the audio to transcribe.",
    )
    parser.add_argument(
        "-s",
        "--segment_start_hint",
        type=float,
        help="Approximate timestamp of start downbeat (to transcribe a segment of the audio).",
    )
    parser.add_argument(
        "-e",
        "--segment_end_hint",
        type=float,
        help="Approximate timestamp of end downbeat (to transcribe a segment of the audio).",
    )
    parser.add_argument(
        "-t",
        "--title",
        type=str,
        help="Title of the song.",
    )
    parser.add_argument(
        "-a",
        "--artist",
        type=str,
        help="Name of the artist or composer.",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=str,
        help="Directory to save the output files (lead sheet PDF, synchronized MIDI, etc.).",
    )
    parser.add_argument(
        "--measures_per_chunk",
        type=int,
        help="The number of measures which Sheet Sage transcribes at a time (for best results, set to phrase length).",
    )
    parser.add_argument(
        "--segment_hints_are_downbeats",
        action="store_true",
        help="If set, overrides downbeat detection using the specified segment hints (note that the hints must be *very* precise for this to work as intended).",
    )
    parser.add_argument(
        "--beats_per_measure",
        type=int,
        choices=[3, 4],
        help="If specified, overrides time signature detection (4 for '4/4' or 3 for '3/4').",
    )
    parser.add_argument(
        "--beats_per_minute_hint",
        type=int,
        help="If specified, helps the beat detector find the right tempo. Useful if detected tempo is a factor of 2 off from real tempo.",
    )
    parser.add_argument(
        "--melody_threshold",
        type=float,
        help="If specified, overrides default melody threshold (0-1, lower for more notes.)",
    )
    parser.add_argument(
        "--harmony_threshold",
        type=float,
        help="If specified, overrides default harmony threshold (0-1, lower for more chords.)",
    )
    parser.add_argument(
        "--skip_melody",
        action="store_false",
        dest="detect_melody",
        help="If set, skips melody transcription.",
    )
    parser.add_argument(
        "--skip_harmony",
        action="store_false",
        dest="detect_harmony",
        help="If set, skips chord recognition.",
    )
    parser.add_argument(
        "--legacy_behavior",
        action="store_true",
        dest="legacy_behavior",
        help="If set, ignores segment_end_hint and transcribes exactly one max-length chunk.",
    )

    parser.set_defaults(
        segment_start_hint=None,
        segment_end_hint=None,
        title=None,
        artist=None,
        output_dir="./output",
        measures_per_chunk=8,
        segment_hints_are_downbeats=False,
        beats_per_measure=None,
        beats_per_minute_hint=None,
        melody_threshold=None,
        harmony_threshold=None,
        detect_melody=True,
        detect_harmony=True,
        legacy_behavior=False,
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    lead_sheet, segment_beats, segment_beats_times = atoscore(
        args.audio_path_or_url,
        segment_start_hint=args.segment_start_hint,
        segment_end_hint=args.segment_end_hint,
        measures_per_chunk=args.measures_per_chunk,
        segment_hints_are_downbeats=args.segment_hints_are_downbeats,
        beats_per_measure_hint=args.beats_per_measure,
        beats_per_minute_hint=args.beats_per_minute_hint,
        detect_melody=args.detect_melody,
        detect_harmony=args.detect_harmony,
        melody_threshold=args.melody_threshold,
        harmony_threshold=args.harmony_threshold,
        legacy_behavior=args.legacy_behavior,
        tqdm=tqdm,
    )

    # Create output directory
    output_dir = pathlib.Path(args.output_dir).resolve()
    if output_dir == pathlib.Path("./output").resolve():
        uuid = uuid.uuid4().hex
        output_dir = pathlib.Path(output_dir, uuid)
    logging.info(f"Writing to {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write lead sheet
    lily = lead_sheet.as_lily(artist=args.artist, title=args.title)
    with open(pathlib.Path(output_dir, "output.ly"), "w") as f:
        f.write(lily)
    with open(pathlib.Path(output_dir, "output.pdf"), "wb") as f:
        f.write(
            engrave(
                lily, out_format="pdf", transparent=False, trim=False, hide_footer=False
            )
        )

    # Write MIDI
    with open(pathlib.Path(output_dir, "output.midi"), "wb") as f:
        f.write(
            lead_sheet.as_midi(
                pulse_to_time_fn=create_beat_to_time_fn(
                    segment_beats, segment_beats_times
                )
            )
        )
