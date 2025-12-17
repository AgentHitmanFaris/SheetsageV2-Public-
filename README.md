# Sheet Sage - Audio to Lead Sheet Transcription V2

Sheet Sage is an AI-powered tool that transcribes music audio into lead sheets (melody + chords) and MIDI files. It leverages multiple state-of-the-art models to provide high-quality transcriptions for various use cases.

## Key Features

*   **Lead Sheet Transcription**: Converts songs into a PDF lead sheet with melody, chords, and lyrics (if lyrics processing is added in future). Uses **Sheet Sage V2** for structure/harmony and **Spotify Basic Pitch** for melody.
*   **Polyphonic Piano Transcription**: Uses ByteDance's **Piano Transcription with Pedals** model to transcribe complex piano performances into accurate MIDI.
*   **Melody & Pitch Bend Support**: Captures expressive nuances like pitch bends and polyphony when using the Basic Pitch mode.
*   **Vocal Separation**: Integrated **Demucs** support to isolate vocals before transcription for cleaner melody detection.
*   **GPU Acceleration**: Fully supports NVIDIA GPUs for fast inference using CUDA 12.1 and ONNX Runtime.

## Installation & Setup

### Prerequisites
*   **Windows 10/11** (Currently optimized for Windows)
*   **NVIDIA GPU** (Recommended for reasonable speed, though CPU is supported)
*   **Git** installed and available in PATH.

### One-Click Setup
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/AgentHitmanFaris/sheetsageV2.git
    cd sheetsageV2
    ```

2.  **Run the Setup Script**:
    Double-click or run `setup_local.bat` in a terminal.
    ```powershell
    .setup_local.bat
    ```
    This script will:
    *   Download a portable Python 3.11 environment.
    *   Install all Python dependencies (including PyTorch with CUDA support).
    *   Download necessary system tools (FFmpeg, FluidSynth, LilyPond) into the project folder.
    *   **Note**: The setup might take a while as it downloads large machine learning models.

## Usage

### Launching the Interface
Double-click `run_local.bat` to start the web interface.
```powershell
.run_local.bat
```
The interface will open automatically in your browser at `http://127.0.0.1:7860`.

### Transcription Modes

1.  **Lead Sheet (Standard)**:
    *   Best for: Pop songs, jazz standards, or any track where you want a simplified "Melody + Chords" lead sheet.
    *   Options: Enable "Separate Vocals" for better melody accuracy on full mixes.

2.  **Piano (Polyphonic)**:
    *   Best for: Solo piano recordings.
    *   Output: A highly detailed MIDI file capturing all notes and pedal usage.

3.  **Basic Pitch (Polyphonic)**:
    *   Best for: Getting raw, expressive MIDI (including pitch bends) from any instrument.
    *   Output: MIDI files (both quantized for sheet music and raw for DAW usage).

## Troubleshooting

*   **Transcription is slow**: Ensure your GPU is detected. The startup log should say "Hardware Detected: GPU". If not, reinstall PyTorch with CUDA support.
*   **"Stuck" at start**: The first run downloads/loads large models (Demucs, Basic Pitch). Check the console window for progress.
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
