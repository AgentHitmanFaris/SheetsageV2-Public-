import json
import os
import pathlib

DEFAULT_CONFIG = {
    "soundfont_path": os.path.join(os.getcwd(), "soundfont", "MS Basic.sf3"),
    "yt_dlp_path": os.path.join(os.getcwd(), "python_embeded", "Scripts", "yt-dlp.exe"),
    "output_dir": os.path.join(os.getcwd(), "output")
}

CONFIG_FILE = pathlib.Path(os.getcwd()) / ".atoscore_config.json"

def load_config():
    """Loads configuration from a JSON file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        # Merge with defaults to ensure all keys are present
        return {**DEFAULT_CONFIG, **config}
    return DEFAULT_CONFIG

def save_config(config):
    """Saves configuration to a JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# Initialize global configuration instance
current_config = load_config()
