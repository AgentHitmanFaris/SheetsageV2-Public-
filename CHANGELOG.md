# Changelog

All notable changes to this project will be documented in this file.

## [v0.3.0] - 2025-12-16

### Added
- **Omnizart Re-enabled**: Successfully restored **Omnizart** support for high-quality piano transcription. Dependencies (PyTorch 1.9, NumPy 1.19) are now handled correctly in the setup script.
- **Settings Tab**: Added a persistent "Settings" tab to the UI for configuring the SoundFont path.
- **Cancel Button**: Added a "Cancel" button to all transcription tabs to stop long-running processes safely.
- **Librosa Fallback**: Implemented a robust fallback to **Librosa** for beat tracking if `madmom` fails to compile on Windows.
- **Madmom Fixes**: Patched the Windows setup process to correctly download Python headers, allowing `madmom` to compile from source.

### Changed
- **Demucs Integration**: Improved "Separate Vocals" workflow. The separated vocal stem is now explicitly fed into the melody detection model, significantly improving accuracy for pop songs.
- **Jukebox Removed**: Completely removed the **OpenAI Jukebox** integration to reduce bloat, lower VRAM requirements, and resolve dependency conflicts with the restored Omnizart engine.
- **Dependency Overhaul**: Downgraded NumPy, SciPy, and Matplotlib to versions compatible with Omnizart's strict requirements.

## [v0.2.1] - 2025-12-15

### Added
- **Hybrid Basic Pitch Workflow**: "Spotify Basic Pitch" tab now uses a hybrid approach. It combines **Basic Pitch** for high-quality note detection with **Sheet Sage** infrastructure (Grid, Harmony, Key) to generate full Lead Sheets (PDF, Ly, MIDI).
- **Vocal Separation**: Integrated **Demucs** for vocal separation. Users can now choose to separate vocals before transcription or inspect the separated stems.
- **Todo List**: Added to README for better project tracking.

### Fixed
- **Lead Sheet Validation**: Fixed `ValueError: Change at onset X is not on a downbeat` by implementing strict quantization for harmony detection.
- **Basic Pitch Arguments**: Fixed invalid argument call in Basic Pitch integration.

### Removed
- **Omnizart**: Temporarily removed Omnizart integration from the UI and codebase due to persistent installation and dependency conflicts on Windows.
- **Cleanup**: Removed unused temporary files and scripts.

## [v0.2.0] - 2025-12-14

### Added
- **New Transcription Models**: Integrated Spotify's **Basic Pitch** and **Omnizart** for diverse transcription needs.
    - Added "Spotify Basic Pitch" tab for lightweight, instrument-agnostic transcription.
    - Added "Omnizart" tab for comprehensive music transcription (Music Piano V2).
- **Piano Transcription with Pedals**: Integrated ByteDance's piano transcription model (polyphonic) for high-quality piano MIDI generation.
    - Added a new "Piano Transcription (Polyphonic)" tab in the Web UI.
    - Model weights are automatically downloaded to a portable local `cache/` directory.
    - Supports full MIDI output with pedal events and audio synthesis/mixing.
- **Jukebox Support**: Fully integrated Jukebox 5b model for high-quality feature extraction.
- **Portable Cache**: Models are now stored in a local `cache/` directory, making the installation portable.
- **Advanced Audio Preview**: Added a multi-tab output interface:
    - **Mixed Overlay**: Hear your transcription played over the original audio.
    - **Synthesized**: Hear the transcription alone.
    - **Original Segment**: Hear the isolated audio chunk.
- **Mixed Audio Download**: The mixed overlay audio is now automatically generated and available for download (`output_mixed.wav`).
- **Piano Roll**: Added visual piano roll to Gradio interface.

### Fixed
- Resolved `FutureWarning` and pathing issues with Jukebox model loading.
- Fixed Jukebox download logic to correctly identify local files in the portable cache.
- Cleaned up repository by removing temporary debug scripts.

### Changed
- Refactored `decode_audio` to use `BytesIO` for in-memory audio decoding, removing unnecessary temporary file creation.
- Updated `launch_gradio.py` to automatically configure `JUKEBOX_CACHE_DIR` to the local project folder.
- Updated `README.md` with new features and manual model setup instructions.
