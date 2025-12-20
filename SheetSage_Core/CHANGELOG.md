# Changelog

All notable changes to this project will be documented in this file.

## [v3.0.0] - 2025-12-20

### Major Release: SheetSage V3 "Lunaverus" & Unified Architecture

This major release transforms Sheet Sage into a unified MIR (Music Information Retrieval) workstation, integrating the new **Lunaverus CNN**, restoring **Omnizart** with GPU acceleration, and polishing the entire experience.

### New Features
- **SheetSage V3 (Lunaverus CNN)**:
    - Integrated a custom-trained CNN model optimized for visual-first piano transcription.
    - Achieves high-resolution onboarding/offset detection.
    - Fully GPU-accelerated via Portable CUDA.
- **Omnizart Integration (Advanced)**:
    - Added dedicated tab for Omnizart.
    - Supports **Music**, **Chord**, **Drum**, **Vocal**, **Beat**, and **Vocal Contour** modes.
    - Specifically optimized specifically for **Drum Transcription** with MIDI output.
- **Basic Pitch (Polyphonic) on GPU**:
    - Unlocked GPU acceleration for Spotify's Basic Pitch model by removing CPU-forced environment variables.
    - Now runs significantly faster on CUDA devices.
- **Portable GPU Engine**:
    - Implemented a "Zero-Install" GPU strategy.
    - Automatically manages CUDA 11.2 and cuDNN 8.1 DLLs within the project folder.
    - `run_local.ps1` dynamically configures the PATH, so **system-wide CUDA installation is NOT required**.

### Improved
- **Real-Time Feedback**:
    - All transcription modes (Omnizart, Basic Pitch, SheetSage, Piano) now stream live logs to the **Gradio Progress Bar**.
    - Added a **Terminal Timer** thread to show elapsed time in the console, preventing "is it frozen?" anxiety.
- **Gradio Interface**:
    - Polished Dark Mode UI.
    - Unified tab layout.
    - Added "Advanced Settings" accordions to declutter the interface.

### Fixed
- **Omnizart Crashes**: Fixed `ZeroDivisionError` and `IndexError` when Omnizart produced empty MIDI files.
- **Synthesis**: Fixed `fluidsynth` DLL loading issues on Windows.
- **Beat Tracking**: Fixed `madmom` compilation issues by properly installing VS C++ headers via `fix_omnizart_headers.ps1`.

## [v0.3.4] - 2025-12-19

### Improved
- **Model Efficiency**: Optimized model inference for better performance on consumer GPUs (e.g., GTX 1060 6GB).
    - **VRAM Reduction**: Implemented Automatic Mixed Precision (AMP) using `torch.amp.autocast("cuda")` in `sheetsage/infer.py` to significantly reduce VRAM usage during inference.
    - **Compute Optimization**: Enabled `batch_first=True` for `TransformerEncoder` in `sheetsage/modules/modules.py` to improve memory access patterns and inference speed on CUDA devices.

## [v0.3.3] - 2025-12-18

### Fixed
- **In-Place Restart**: Fixed the application restart logic. The "Restart App" button now correctly reloads the server within the same terminal window without spawning detached processes or closing the connection prematurely.
- **Audio Playback Truncation**: Resolved an issue where the web mixer would sometimes play only the first 30 seconds of an uploaded song. The player now forces the use of the fully processed, standardized WAV file from the server to ensure full-length playback.

## [v0.3.2] - 2025-12-18

### Changed
- **Jukebox Cleanup**: Removed all remaining code, comments, and CLI arguments related to OpenAI Jukebox from `infer.py`, `gradio_app.py`, and `README.md`.
- **Refactoring**: Renamed `madmom` function to `librosa_beat_track` in `beat_track.py` to accurately reflect the underlying library.
- **Code Quality**: Removed duplicate logic and redundant status updates in `gradio_app.py`.
- **LilyPond**: Updated the LilyPond template version from 2.18.2 to **2.24.3**.

### Improved
- **Clean Restart**: The "Restart App" function now fully detaches the new process and closes the old one cleanly, launching a new terminal window.
- **Auto-Refresh**: The web interface now automatically refreshes when the application validates that the server has restarted, removing the need for manual page reloads.

### Added
- **UI Upgrade**: Overhauled the **Multi-Track Mixer** with a professional "AnthemScore-style" Dark Mode interface.
    - Features explicit sync controls, time display, and color-coded tracks (Original=Blue, Synth=Yellow, Vocals=Red).
- **Configuration**: Added `yt_dlp_path` and `output_dir` to the global configuration.
    - `yt-dlp` path is now configurable and used consistently across the app.
    - All transcription outputs (Lead Sheet, Piano, Basic Pitch, Demucs) now respect the configured `output_dir`.

### Fixed
- **HTML Mixer**: Fixed a race condition where the "Play" button wouldn't work on first load. Implemented a robust polling mechanism to ensure the audio player is fully initialized before attaching controls.
- **Basic Pitch Bug**: Fixed an issue where `create_mix` was being called twice during Basic Pitch transcription.

## [v0.3.1] - 2025-12-17

### Added
- **Multi-Track Audio Mixer**: Replaced separate audio tabs with a single, interactive **HTML5 Audio Mixer**.
    - **Features**: Simultaneous synchronized playback, individual volume sliders for Original, Synthesized, and Vocals, and a unified seek bar.
    - **Fix**: Handles filenames with spaces correctly via URL encoding.
- **Stop Button**: Added a dedicated **"Stop / Cancel"** button to the UI to immediately interrupt long-running transcription processes.
- **Basic Pitch Mixer**: Basic Pitch mode now supports the full audio mixer, allowing you to blend the original track with the generated MIDI.

### Changed
- **UI Improvements**: Simplified "Basic Pitch" tab by hiding advanced settings by default.
- **Return Signatures**: Unified the return values of all transcription functions to support the new Mixer interface.


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
