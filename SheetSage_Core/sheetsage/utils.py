import gzip
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import tempfile
import warnings
from functools import lru_cache
from io import BytesIO

import audioread
import librosa
import numpy as np
from PIL import Image
from scipy.io.wavfile import write as wavwrite


def compute_checksum(
    path_or_bytes, algorithm="sha256", gunzip=False, chunk_size=1024 * 1024
):
    """Computes checksum of target path or bytes.

    Args:
        path_or_bytes (pathlib.Path or bytes): Location or bytes of file to compute checksum for.
        algorithm (str, optional): Hash algorithm (from :func:`hashlib.algorithms_available`); default ``sha256``.
        gunzip (bool, optional): If true, decompress before computing checksum.
        chunk_size (int, optional): Chunk size for iterating through file.

    Returns:
        str: Hex representation of checksum.

    Raises:
        FileNotFoundError: Unknown path.
        IsADirectoryError: Path is a directory.
        ValueError: Unknown algorithm.
    """
    if algorithm not in hashlib.algorithms_guaranteed or algorithm.startswith("shake"):
        raise ValueError("Unknown algorithm")
    computed = hashlib.new(algorithm)
    if isinstance(path_or_bytes, bytes):
        computed.update(path_or_bytes)
    else:
        open_fn = gzip.open if gunzip else open
        with open_fn(path_or_bytes, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                computed.update(data)
    return computed.hexdigest()


def run_cmd_sync(cmd, cwd=None, interactive=False, timeout=None):
    """Runs a console command synchronously and returns the results.

    Args:
        cmd (str): The command to execute.
        cwd (pathlib.Path, optional): The working directory in which to execute the command.
        interactive (bool, optional): If set, run command interactively and pipe all output to console.
        timeout (float, optional): If specified, kills process and throws error after this many seconds.

    Returns:
        tuple or int:
            If interactive is False: (Process exit status code, Standard output, Standard error).
            If interactive is True: Process exit status code.

    Raises:
        FileNotFoundError: Unknown command.
        NotADirectoryError: Specified working directory is not a directory.
        subprocess.TimeoutExpired: Specified timeout expired.
    """
    args = cmd
    if isinstance(cmd, str):
        if len(cmd.strip()) == 0:
            raise FileNotFoundError()
        # On Windows, shlex.split treats backslashes as escapes.
        # We replace them with double backslashes to preserve them.
        if os.name == "nt":
            cmd = cmd.replace("\\", "\\\\")
        args = shlex.split(cmd)
    elif isinstance(cmd, list):
         if len(cmd) == 0:
              raise FileNotFoundError()
    else:
         # Unknown type
         raise FileNotFoundError()

    kwargs = {}
    if not interactive:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    err = None
    with subprocess.Popen(args, cwd=cwd, **kwargs) as p:
        try:
            p_res = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as e:
            err = e
        p.kill()

    if err is not None:
        raise err

    result = p.returncode

    if not interactive:
        stdout, stderr = [s.decode("utf-8").strip() for s in p_res]
        result = (result, stdout, stderr)

    return result


_RETRIEVE_AUDIO_CMD_TEMPLATE = """
yt-dlp \
    --no-cache-dir \
    --no-continue \
    --no-playlist \
    --format bestaudio/best \
    {other} \
    {url}
"""


@lru_cache(maxsize=1)
def retrieve_audio_bytes(
    url,
    return_name=False,
    max_filesize_mb=None,
    max_duration_seconds=None,
    timeout=60.0,
):
    """Retrieves encoded audio (as raw bytes) from specified URL.

    Args:
        url (str): The URL to retrieve from.
        return_name (bool): If True, return the retrieved file name.
        max_filesize_mb (int, optional): Maximum allowed filesize in MB.
        max_duration_seconds (float, optional): Maximum allowed duration in seconds.
        timeout (float): Max amount of time to wait before throwing an error.

    Returns:
        bytes or tuple:
            The raw bytes of the encoded audio file.
            If return_name is True, returns (audio_bytes, filename).

    Raises:
        subprocess.TimeoutExpired: Specified timeout expired.
        ValueError: Video too large or too long.
        Exception: Error during retrieval.
    """
    with tempfile.TemporaryDirectory() as d:
        if max_duration_seconds is not None:
            status, stdout, stderr = run_cmd_sync(
                cmd=_RETRIEVE_AUDIO_CMD_TEMPLATE.format(
                    url=url.strip(), other="--dump-json"
                ),
                cwd=d,
                timeout=timeout,
            )
            try:
                assert status == 0
                metadata = json.loads(stdout)
                duration = float(metadata["duration"])
            except:
                raise Exception(f"Failed to retrieve duration from {url}:\n{stderr}")
            if duration > max_duration_seconds:
                raise ValueError(
                    f"Specified url is too long ({duration} > {max_duration_seconds})."
                )

        assert len(list(pathlib.Path(d).iterdir())) == 0
        status, stdout, stderr = run_cmd_sync(
            cmd=_RETRIEVE_AUDIO_CMD_TEMPLATE.format(
                url=url.strip(),
                other=""
                if max_filesize_mb is None
                else f"--max-filesize {max_filesize_mb}m",
            ),
            cwd=d,
            timeout=timeout,
        )
        if max_filesize_mb is not None and "File is larger than max" in stdout:
            raise ValueError("Specified url is too large.")
        paths = list(pathlib.Path(d).iterdir())
        if status != 0 or len(paths) == 0:
            raise Exception(f"Failed to retrieve from {url}:\n{stderr}\n{stdout}")
        assert len(paths) == 1
        path = paths[0]
        with open(path, "rb") as f:
            audio_bytes = f.read()
        if return_name:
            result = (audio_bytes, path.name)
        else:
            result = audio_bytes
        return result


def decode_audio(
    path_or_bytes,
    sr=None,
    offset=0.0,
    duration=None,
    mono=False,
    normalize=False,
    res_type="kaiser_best",
):
    """Decodes encoded audio from path or raw bytes.

    Args:
        path_or_bytes (pathlib.Path, str, or bytes): The filepath or raw bytes to decode.
        sr (int, optional): If specified, resample audio to this sample rate.
        offset (float, optional): Decode audio starting from this timestamp in seconds.
        duration (float, optional): Decode at most this many audio in seconds.
        mono (bool, optional): If True, average multichannel audio to mono.
        normalize (bool, optional): If True, normalize audio to max(abs(audio)) == 1.0.
        res_type (str, optional): The resampling algorithm to use (see `librosa.load` documentation).

    Returns:
        tuple: (sample_rate (int), audio_data (np.ndarray)).
            Audio data is a NumPy array of shape [nsamps, nch] with float32 dtype.

    Raises:
        FileNotFoundError: Unknown file.
        RuntimeError: Unknown file format.
    """
    if isinstance(path_or_bytes, bytes):
        path = BytesIO(path_or_bytes)
    else:
        path = path_or_bytes

    # Decode audio file
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audio, sr = librosa.load(
                path,
                sr=sr,
                mono=mono,
                offset=offset,
                duration=duration,
                res_type=res_type,
            )
    except audioread.exceptions.NoBackendError as e:
        raise RuntimeError("Unknown audio format") from e

    # Check output and rearrange to [nsamps, nch]
    assert isinstance(sr, int)
    assert audio.dtype == np.float32
    assert audio.ndim in [1, 2]
    if audio.ndim == 1:
        audio = audio[np.newaxis, :]
    assert audio.shape[0] > 0
    audio = np.swapaxes(audio, 0, 1)
    audio = np.asfortranarray(audio)

    # Normalize
    if normalize and audio.shape[0] > 0:
        norm_factor = np.abs(audio).max()
        if norm_factor > 0:
            audio /= norm_factor

    return sr, audio


def encode_audio(path, sr, audio, bitexact=False, timeout=60.0):
    """Encodes raw audio array into different file formats using FFmpeg.

    Args:
        path (pathlib.Path or str): Destination filepath (where the extension determines the codec).
        sr (int): The sample rate of the audio.
        audio (np.ndarray): A NumPy array of the audio (shape [nsamps, nch], dtype float32).
        bitexact (bool, optional): If True, ensure reproducible checksums of output file (only on FFmpeg 4+).
        timeout (float, optional): Maximum amount of time to wait for encoding.

    Raises:
        subprocess.TimeoutExpired: Specified timeout expired.
        Exception: FFmpeg threw an error while encoding.
    """
    f_fd, f_name = tempfile.mkstemp(suffix=".wav")
    try:
        # wavwrite takes a filename or a file object. If we give it filename, it opens it.
        # Since we have fd open from mkstemp, we should close it first or use os.fdopen
        # But wavwrite might not like the raw fd? It takes "string or open file handle".
        # Let's close fd and let wavwrite open by name.
        os.close(f_fd)
        wavwrite(f_name, sr, audio)
        cmd = ["ffmpeg", "-v", "error", "-i", f_name, "-y"]
        if bitexact:
            cmd.append("-bitexact")
        cmd.append(str(path))
        status, stdout, stderr = run_cmd_sync(cmd, timeout=timeout)
        if status != 0:
            raise Exception(f"FFmpeg failed: {stderr}")
        assert pathlib.Path(path).is_file()
    finally:
        if os.path.exists(f_name):
            os.remove(f_name)


def get_approximate_audio_length(path, timeout=10):
    """Retrieves the approximate length of an audio file.

    Args:
        path (str or pathlib.Path): Path to the audio file.
        timeout (int, optional): Timeout in seconds.

    Returns:
        float: Duration of the audio in seconds.

    Raises:
        Exception: If FFmpeg fails.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-i",
        str(path),
        "-show_format",
        "-show_streams",
        "-print_format",
        "json",
    ]
    status, stdout, stderr = run_cmd_sync(
        cmd,
        timeout=timeout,
    )
    try:
        assert status == 0
        assert len(stderr) == 0
    except:
        raise Exception(f"FFmpeg failed: {stderr}")
    d = json.loads(stdout)
    duration = float(d["format"]["duration"])
    return duration


_LILYPOND_ENGRAVE_TEMPLATE = """
lilypond \
        -s \
        {args} \
        --{out_format} \
        -o {out_path} \
        {in_path}
""".strip()


def engrave(
    lilypond,
    out_format="png",
    transparent=True,
    trim=True,
    hide_footer=True,
    args=None,
    timeout=60,
):
    """
    Renders LilyPond markup into an image or PDF.

    Args:
        lilypond (str): The LilyPond source code.
        out_format (str, optional): Output format, either "png" or "pdf".
        transparent (bool, optional): If True, makes the background transparent (PNG only).
        trim (bool, optional): If True, crops the image to content (PNG only).
        hide_footer (bool, optional): If True, removes the default LilyPond footer.
        args (str, optional): Additional arguments for the lilypond command.
        timeout (int, optional): Timeout in seconds.

    Returns:
        bytes: The content of the generated file.

    Raises:
        ValueError: If `out_format` is invalid.
        Exception: If lilypond compilation fails or no output is generated.
    """
    if out_format not in ["png", "pdf"]:
        raise ValueError()
    if args is not None and not isinstance(args, str):
        raise ValueError()

    # Adjust lilypond
    if hide_footer:
        lilypond += "\n\\header { tagline = ##f }"

    # Engrave
    with tempfile.TemporaryDirectory() as d:
        # Create cmd
        in_path = pathlib.Path(d, "in.ly")
        with open(in_path, "w") as f:
            f.write(lilypond)
        args = "" if args is None else args
        if out_format != "pdf":
            args += " -dpixmap-format=pngalpha"
        cmd = _LILYPOND_ENGRAVE_TEMPLATE.format(
            args=args,
            out_format=out_format,
            out_path=pathlib.Path(d, "out"),
            in_path=in_path,
        )

        # Run cmd
        status, stdout, stderr = run_cmd_sync(cmd, timeout=timeout)
        if status != 0:
            raise Exception(f"Failed to engrave ({status}): {stderr}")

        # Load output pages
        out_paths = sorted(
            [p for p in pathlib.Path(d).glob(f"out*.{out_format}") if p.is_file()]
        )
        if len(out_paths) == 0:
            raise Exception("No output")
        assert len(out_paths) == 1 or out_format == "png"
        pages = []
        for p in out_paths:
            with open(p, "rb") as f:
                pages.append(f.read())

    # Post processes
    if out_format == "pdf":
        assert len(out_paths) == 1
        result_bytes = pages[0]
    else:

        def _png_to_image(png_bytes):
            return Image.open(BytesIO(png_bytes))

        def _image_to_png(im):
            bio = BytesIO()
            im.save(bio, format="png")
            return bio.getvalue()

        def _concatenate(pages_bytes):
            pages = [_png_to_image(p) for p in pages_bytes]
            cat_width = max([p.width for p in pages])
            cat_height = sum([p.height for p in pages])
            cat = Image.new("RGB", (cat_width, cat_height))
            h = 0
            for p in pages:
                cat.paste(p, (0, h))
                h += p.height
            return _image_to_png(cat)

        def _trim(page_bytes):
            im = _png_to_image(page_bytes)
            bbox = im.getbbox()
            if bbox is not None:
                im = im.crop(bbox)
            return _image_to_png(im)

        def _remove_transparency(page_bytes):
            im = _png_to_image(page_bytes).convert("RGBA")
            background = Image.new("RGBA", im.size, (255, 255, 255))
            im = Image.alpha_composite(background, im)
            return _image_to_png(im)

        if len(pages) == 1:
            result_bytes = pages[0]
        else:
            result_bytes = _concatenate(pages)

        if trim:
            result_bytes = _trim(result_bytes)
        if not transparent:
            result_bytes = _remove_transparency(result_bytes)

    return result_bytes
