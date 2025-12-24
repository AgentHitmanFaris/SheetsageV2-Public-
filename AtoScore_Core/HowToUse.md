# How to Use Sheet Sage

This guide explains how to use the Sheet Sage Gradio interface to transcribe audio files into sheet music.

## Interface Overview

The interface is divided into two main columns: **Input** (left) and **Output** (right).

### 1. Transcription Methods (Tabs)

Sheet Sage now offers three distinct transcription modes via tabs:

1.  **Piano Transcription (Polyphonic)**:
    *   **Best For**: Solo piano performances (classical, jazz, etc.).
    *   **Features**: Detects complex polyphony and pedal usage.
    *   **Model**: ByteDance Piano Transcription.

2.  **Spotify Basic Pitch**:
    *   **Best For**: General music where you want accurate melody detection combined with a professional Lead Sheet format.
    *   **Features**: Hybrid workflow. Uses **Basic Pitch** for note detection (very sensitive) and **Sheet Sage** for structural analysis (chords, measures, time signature). Generates PDF/MIDI/Audio.


3.  **atoscore V3 (Lunaverus)**:
    *   **Best For**: Premium Piano transcriptions requiring "Lunaverus-style" visual accuracy.
    *   **Features**: Uses a custom-trained CNN on the MAESTRO dataset. Optimized for GPU.

4.  **Omnizart (Advanced)**:
    *   **Best For**: Specific instruments like **Drums**, **Chords**, or **Vocals**.
    *   **Features**: Access to the full Omnizart suite (Music, Chord, Drum, Vocal, Beat). Excellent for percussion.

5.  **Lead Sheet (Melody + Chords)**:
    *   **Best For**: Songs with vocals or distinct melody lines where you want a simpler melody + chord chart.
    *   **Features**: The classic Sheet Sage V2 experience. Detects melody and harmony separately.

### 2. Input Section

Each tab has its own input section.

#### Lead Sheet (Standard) Tab

*   **Audio Source**:
    *   **Upload Audio**: Click the upload box or drag and drop an audio file.
    *   **Audio URL**: Paste a direct link to an audio file.

*   **Advanced Settings**:
    Click on **"Advanced Settings"** to expand the configuration options.
    *   **Start Time (s) / End Time (s)**: Transcribe a specific segment.
    *   **Detect Melody / Harmony**: Toggle specific tasks.
    *   **Separate Vocals (Demucs)**: Isolate vocals before transcription (recommended for pop/rock songs).
    *   **Melody / Harmony Threshold**: Adjust sensitivity (0.0 - 1.0).
    *   **Beats Per Measure / BPM Hint**: Help the AI detect the correct grid.
    *   **Measures Per Chunk**: Processing window size.

### 3. Transcribing

Once you have set your inputs:
1.  Click the primary **"Transcribe"** button for your chosen tab.
2.  Wait for the process to complete.
    *   **Standard Mode**: Progress bar will show steps like "Detecting Beats," "Extracting Features," etc.
    *   **Basic Pitch**: Progress bar will show "Analyzing Audio Structure" and then "Transcribing Melody."

### 4. Output Section

After processing is finished:

*   **Status**: This box will show "Transcription successful!" or display any error messages if something went wrong.
*   **Download Results**:
    *   **output.pdf**: The engraved sheet music.
    *   **output.midi**: The MIDI file of the transcription, which you can play in any MIDI player or DAW.
    *   **output.ly**: The LilyPond source file used to generate the PDF.

### 5. Audio Preview (Multi-Track Mixer)

The new **Multi-Track Mixer** allows you to audit the transcription accuracy in real-time.

*   **Play/Pause**: Controls all tracks simultaneously.
*   **Original**: Volume slider for the source audio.
*   **Synth**: Volume slider for the generated piano/MIDI audio.
*   **Vocals**: (If "Separate Vocals" was used) Volume slider for the isolated vocal track.

Use the sliders to create your own mix (e.g., mute the original to hear only the notes, or blend them to check alignment).

## Troubleshooting Tips

*   **"Segment end hint should be greater than start"**: Ensure your End Time is strictly larger than your Start Time. If you want to transcribe to the end, leave End Time empty.
*   **Beat Tracking Issues**: If the beats seem off, try providing a **BPM Hint**.
*   **Transcription Failed**: Check the console window for detailed error logs.

