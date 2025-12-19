# Sheet Sage - Audio to Lead Sheet Transcription V2

Sheet Sage is an AI-powered tool that transcribes music audio into lead sheets (melody + chords) and MIDI files. It leverages multiple state-of-the-art models to provide high-quality transcriptions for various use cases.

## Key Features

*   **Lead Sheet Transcription**: Converts songs into a PDF lead sheet with melody, chords, and lyrics (if lyrics processing is added in future). Uses **Sheet Sage V2** for structure/harmony and **Spotify Basic Pitch** for melody.
*   **Polyphonic Piano Transcription**: Uses ByteDance's **Piano Transcription with Pedals** model to transcribe complex piano performances into accurate MIDI.
*   **Melody & Pitch Bend Support**: Captures expressive nuances like pitch bends and polyphony when using the Basic Pitch mode.
*   **Vocal Separation**: Integrated **Demucs** support to isolate vocals before transcription for cleaner melody detection.
*   **Multi-Track Mixer**: Interactive web-based audio mixer to preview results, seamlessly blending between Original Audio, Synthesized MIDI, and Separated Vocals.
*   **GPU Acceleration**: Fully supports NVIDIA GPUs for fast inference using CUDA 12.1 and ONNX Runtime.

## Installation & Setup

Sheet Sage depends on a few heavy-weight libraries (PyTorch 2.x, FluidSynth, LilyPond, FFmpeg).
We provide a **One-Click Setup Script** to handle everything automatically.

### Prerequisites
*   **Windows 10/11** (Currently optimized for Windows)
*   **NVIDIA GPU** (Highly Recommended for fast transcription)
*   **Git** installed and available in PATH.
*   *Note: Python is embedded and managed automatically by the setup script.*

### One-Click Setup
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/AgentHitmanFaris/sheetsageV2.git
    cd sheetsageV2
    ```

2.  **Run the Setup Script**:
    Double-click or run `setup_local.bat` in a terminal.
    ```powershell
    ./setup_local.bat
    ```
    This script will:
    *   Download a portable Python 3.11 environment.
    *   Install all Python dependencies (including PyTorch 2.8.0 with CUDA 12.1).
    *   Download necessary system tools (FFmpeg, FluidSynth, LilyPond) into the project folder.
    *   **Note**: The setup might take a while as it downloads large machine learning models.

## Usage

### Launching the Interface
Double-click `run_local.bat` to start the web interface.
```powershell
./run_local.bat
```
The interface will open automatically in your browser at `http://127.0.0.1:7860`.

### Transcription Modes

1.  **Lead Sheet (Standard)**:
    *   Best for: Pop songs, jazz standards, or any track where you want a simplified "Melody + Chords" lead sheet.
    *   Options: Enable "Separate Vocals" for better melody accuracy on full mixes.

2.  **Piano (Polyphonic)**:
    *   Best for: Solo piano recordings.
    *   Output: A highly detailed MIDI file capturing all notes and pedal usage.

    *   Best for: Getting raw, expressive MIDI (including pitch bends) from any instrument.
    *   Output: MIDI files (both quantized for sheet music and raw for DAW usage).

### New Features (v0.3.3)
*   **History Tab**: Easily browse and reload previous transcription projects.
    *   Organized by **Song Name** and **Timestamp**.
    *   One-click restore of the full mixer state and piano roll.

## Troubleshooting & Recent Fixes (v0.3.3+)

### Solved Issues
*   **Audio Playback 404 Errors**: Resolved by implementing a secure file caching system (`temp_playback` folder). The application now safely copies files for the web player to access, bypassing complex Windows path permission issues.
*   **Audio Truncation**: Fixed an issue where only the first 30 seconds of audio would play. The mixer now correctly loads the full processed audio file.
*   **Restart Loops**: Improved the "Restart App" stability. It now performs an in-place restart without opening multiple browser tabs.
    *   *Note*: If the app hangs during restart, you may need to manually refresh the page (F5).

### Common Questions
*   **"No audio file provided" Warning**: The application will now warn you if you try to transcribe without uploading a file. This is a safety feature to prevent crashes.
*   **Vocals Track is Muted**: In the "Preview" mixer, the **Vocals** track is loaded but set to **0% volume** by default. This is intentional to let you hear the transcription clearly. You can unmute it manually.
*   **Slow Transcription**: Ensure your GPU is detected. Check the console log for "Hardware Detected: GPU".
*   **Missing Dependencies**: If `setup_local.bat` fails, try running it again or check your internet connection.

## Architecture

*   **Frontend**: Gradio (Web UI)
*   **Backend**: Python 3.11 (Embedded)
*   **Models**:
    *   Sheet Sage V2 (Transformer-based Harmony/Beat Tracking)
    *   Spotify Basic Pitch (Melody/Polyphonic Transcription)
    *   Demucs (Source Separation)
    *   ByteDance Piano Transcription (Piano MIDI)
*   **Rendering**: LilyPond (Sheet Music), FluidSynth (Audio Preview)

## License

[MIT License](LICENSE) (Check individual model licenses for commercial usage)
