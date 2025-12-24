import json
import logging
import os
import pathlib
import urllib.request
import subprocess # For yt-dlp
import shlex # For yt-dlp

from . import CACHE_DIR, LIB_DIR
from .utils import compute_checksum

_DEFAULT_CHUNK_SIZE = 1024 * 1024
_ASSETS = None


def _init_assets():
    """
    Initializes the assets dictionary by loading asset metadata from JSON files.

    This function scans the library directory for asset JSON definitions,
    validates the paths and checksums, and populates the global `_ASSETS` dictionary.
    It should only be called once.

    Raises:
        Exception: If the function is called more than once.
        AssertionError: If an asset definition is missing a checksum, has an invalid path,
                        or contains a duplicate path.
    """
    global _ASSETS
    if _ASSETS is not None:
        raise Exception("Should only run this once")

    _ASSETS = {}
    asset_paths = set()
    for json_path in sorted(pathlib.Path(LIB_DIR, "assets").rglob("*.json")):
        with open(json_path, "r") as f:
            d = json.load(f)
        for tag, asset in d.items():
            if "checksum" not in asset:
                raise AssertionError("Missing checksum")
            try:
                asset["path"] = pathlib.PurePosixPath(asset["path"].strip())
            except:
                raise AssertionError("Invalid path")
            if asset["path"] in asset_paths:
                raise AssertionError("Duplicate path")
            asset_paths.add(asset["path"])
            asset["path_abs"] = pathlib.Path(CACHE_DIR, asset["path"])
        _ASSETS.update(d)


_init_assets()


def get_asset_tags():
    """
    Retrieves the set of all available asset tags.

    Returns:
        set: A set of strings representing the unique tags for all managed assets.
    """
    return set(_ASSETS.keys())


def _download_with_ytdlp(url, dest_path, filename, timeout=300):
    """
    Downloads a specific file from a MEGA.nz URL using yt-dlp.
    """
    from .config_manager import load_config
    config = load_config()
    yt_dlp_path = pathlib.Path(config.get("yt_dlp_path", ""))
    
    if not yt_dlp_path.exists():
         yt_dlp_path = pathlib.Path("yt-dlp") # Fallback to system path
    cmd = f"{shlex.quote(str(yt_dlp_path))} --no-cache-dir --output {shlex.quote(str(dest_path))} --match-filter \"filename = '{filename}'\" {shlex.quote(url)}"
    logging.info(f"Downloading with yt-dlp: {cmd}")
    try:
        # Popen without shell=True for security, shlex.split to handle spaces
        process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=timeout)
        if process.returncode != 0:
            logging.error(f"yt-dlp stdout: {stdout}")
            logging.error(f"yt-dlp stderr: {stderr}")
            raise Exception(f"yt-dlp download failed with exit code {process.returncode}")
        logging.info(f"yt-dlp stdout: {stdout}")
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        logging.error(f"yt-dlp timed out. stdout: {stdout}, stderr: {stderr}")
        raise
    except Exception as e:
        logging.error(f"Error during yt-dlp download: {e}")
        raise

def _download(url, dest_path, filename, chunk_size=_DEFAULT_CHUNK_SIZE):
    """
    Downloads a file from a URL to a destination path, handling MEGA.nz links via yt-dlp.

    Args:
        url (str): The URL to download from.
        dest_path (pathlib.Path or str): The file path where the downloaded content will be saved.
        filename (str): The expected filename of the asset in case of MEGA download.
        chunk_size (int): The size of chunks to read from the stream in bytes.
    """
    if url.startswith("https://mega.nz/"):
        _download_with_ytdlp(url, dest_path, filename)
    else:
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        with open(dest_path, "wb") as f:
            r = urllib.request.urlopen(req)
            while True:
                chunk = r.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)


def retrieve_asset(tag, delete_wrong=False, chunk_size=_DEFAULT_CHUNK_SIZE, log=True):
    """
    Attempts to acquire and/or verify existence of a tagged asset in the cache.

    If the asset does not exist locally, it attempts to download it. It also performs checksum verification
    to ensure file integrity.

    Args:
        tag (str): The tag identifier for the asset.
        delete_wrong (bool): If True, deletes the local file if the checksum verification fails,
                             allowing a re-download.
        chunk_size (int): The chunk size used for reading files during checksum computation and download.
        log (bool): If True, logs verification and download progress.

    Returns:
        pathlib.Path: The absolute file path for the verified asset.

    Raises:
        ValueError: If the asset tag is invalid.
        Exception: If the asset is missing and cannot be downloaded, or if verification fails.
    """
    # Retrieve asset
    if tag not in _ASSETS:
        raise ValueError()
    asset = _ASSETS[tag]
    path = asset["path_abs"]
    checksum = asset["checksum"]
    if log:
        logging.info(f"Verifying asset: {tag}")
        logging.info(f"Asset location: {path}")

    # Create parent directory
    if not path.parent.is_dir():
        if log:
            logging.info(f"Creating parent: {path.parent}")
        path.parent.mkdir(parents=True)

    def verify():
        assert path.is_file()
        if checksum is not None:
            if len(checksum) == 32:
                algorithm = "md5"
            elif len(checksum) == 40:
                algorithm = "sha1"
            elif len(checksum) == 64:
                algorithm = "sha256"
            else:
                raise AssertionError("Unknown checksum algorithm")
            computed = compute_checksum(
                path, algorithm=algorithm, chunk_size=chunk_size
            )
            if computed != checksum:
                raise Exception(f"File {path} has wrong checksum.")

    # Delete incorrect files
    already_verified = False
    if delete_wrong and path.is_file():
        try:
            verify()
            already_verified = True
        except Exception:
            logging.warning(f"Deleting file with bad checksum: {path}")
            path.unlink()

    # Attempt to download
    if not path.is_file():
        url = asset.get("url")
        if url is None:
            raise Exception("File is missing and cannot be downloaded")
        if log:
            logging.info(f"Downloading from: {url}")
        try:
            _download(url, path, path.name) # Pass filename here
        except Exception as e:
            if path.is_file():
                path.unlink()
            raise Exception(f"Download failed: {e}")
    assert path.is_file()

    # Ensure file integrity
    if not already_verified:
        verify()
    if log:
        logging.info(f"Verified!")

    return path


def task(t, delete_wrong=False):
    logging.info("-" * 80)
    try:
        retrieve_asset(t, delete_wrong=delete_wrong)
    except Exception as e:
        logging.error(e)
        raise e

if __name__ == "__main__":
    import multiprocessing
    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument("startswith", nargs="?")
    parser.add_argument("--delete_wrong", action="store_true", dest="delete_wrong")
    parser.add_argument("--num_parallel", "-n", type=int)

    parser.set_defaults(startswith=None, num_parallel=1, delete_wrong=False)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    tags = sorted(list(get_asset_tags()))
    if args.startswith is not None:
        tags = [t for t in tags if t.startswith(args.startswith.strip().upper())]

    with multiprocessing.Pool(args.num_parallel) as p:
        p.starmap(task, [(t, args.delete_wrong) for t in tags])
