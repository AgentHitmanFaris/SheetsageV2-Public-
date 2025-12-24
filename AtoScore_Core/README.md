# 🎼 Sheet Sage V3: The Ultimate Music Transcription Suite

![Sheet Sage Header](https://img.shields.io/badge/Sheet_Sage-V3-purple?style=for-the-badge&logo=music) 
![GPU](https://img.shields.io/badge/GPU-Accelerated-green?style=for-the-badge&logo=nvidia)
![Status](https://img.shields.io/badge/Status-Stable-blue?style=for-the-badge)

**Sheet Sage V3** is a state-of-the-art, open-source AI Music Transcription System designed for local inference on Windows. It unifies the world's best transcription models into a single, cohesive, and beautiful interface.

Whether you are transcribing complex piano solos, separating vocals from pop songs, or analyzing drum patterns, Sheet Sage V3 provides a modular "Swiss Army Knife" approach to Music Information Retrieval (MIR).

---

## 🚀 Key Features

### 1. **Sheet Sage V3 (Lunaverus CNN)**
*   **The Crown Jewel**: Our custom-trained Convolutional Neural Network (CNN) architecture optimized for "Lunaverus-style" visual MIDI transcription.
*   **High Precision**: Trained on the MAESTRO dataset for pixel-perfect piano transcription.
*   **GPU Accelerated**: Blazing fast inference using CUDA 11+.

### 2. **Omnizart Integration (Advanced)**
*   **Modes**: `Music`, `Chord`, `Drum`, `Vocal`, `Beat`.
*   **Drum Transcription**: Specifically optimized for percussion extraction using U-Net architectures.
*   **Full Control**: Access typically complex CLI commands through a simple GUI.

### 3. **Basic Pitch (Polyphonic)**
*   **Spotify's Technology**: Integrated lightweight instrument-agnostic transcription.
*   **Pitch Bend Support**: Captures vibrato and slides, perfect for guitar and vocals.
*   **Optimized**: Now runs on GPU for faster throughput.

### 4. **Standard Lead Sheet**
*   **Melody + Chords**: The classic workflow that separates vocals (Demucs) and extracts melody (HMM) and chords (Template Matching) for producing readable Lead Sheets.

### 5. **Portable GPU Engine**
*   **Zero-Dependency**: No need to install system-wide CUDA or cuDNN. The project includes a self-contained environment.
*   **Auto-Detection**: Automatically detects your NVIDIA GPU and configures TensorFlow / PyTorch / ONNX Runtime.

---

## 🛠️ Installation & Usage

### Prerequisites
*   **OS**: Windows 10/11
*   **GPU**: NVIDIA GTX 1060 or better recommended (6GB+ VRAM).
*   **Storage**: ~4GB for models and environment.

### Quick Start
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/AgentHitmanFaris/NC-AtoScore.git
    cd NC-AtoScore
    ```
2.  **Run the App**:
    Double-click `run_local.ps1` (or `run_local.bat`).
    *   This will automatically set up the Python environment, check for GPU libraries, and launch the Gradio interface.
3.  **Access**:
    Open your browser to `http://localhost:7860`.

---

## 🎨 User Interface (Gradio)

Sheet Sage V3 features a **Premium Dark-Mode UI** with:
*   **Interactive Audio Mixer**: Separate volume controls for Original, Synth, and Vocals.
*   **Real-time Progress**: Live terminal feedback and status updates during transcription.
*   **Multi-Tab Workflow**: Switch seamlessly between specialized tasks.

---

## 📊 Technical Architecture

Sheet Sage V3 operates on a **Staged Inference Pipeline**:
1.  **Separation (Demucs)**: Isolates sources (Vocals, Drums, Bass) to clean the signal.
2.  **Feature Extraction**: Computes CQT (Constant-Q Transform) or Log-Mel Spectrograms.
3.  **Inference**: 
    *   *Omnizart*: U-Net / DeepLabV3
    *   *Basic Pitch*: Harmonic Stacking CNN
    *   *Lunaverus*: Regressive Onset CNN
4.  **Engraving**: LilyPond converts symbolic MIDI to PDF sheet music.

---

## 📝 Documentation

*   [**GPU Setup Guide**](GPU_SETUP_GUIDE.md): Details on the portable CUDA architecture.
*   [**How To Use**](HowToUse.md): Step-by-step user manual.
*   [**Training Guide**](TRAINING_GUIDE.md): How to train your own models.
*   [**Technical Report**](docs/SheetSage_Technical_Report.html): Deep dive into the methodology.

---

## ❓ FAQ / Troubleshooting

### **Q: I see `ConnectionResetError: [WinError 10054]` in the console. Is something broken?**
**A:** No! This is a **harmless network error** that occurs when:
- You close or refresh the browser tab while audio is playing
- The browser cancels a request (e.g., clicking "Stop" during playback)
- Network interruption during file transfer

**What it does NOT mean:**
- ❌ Your transcription failed
- ❌ Files are corrupted  
- ❌ The app crashed

This is normal behavior for web applications streaming large audio files. You can safely ignore these messages.

### **Q: Audio player shows 0:00 and won't play**
**A:** Try these steps:
1. **Restart the app** using the "🔄 Restart App" button at the top
2. Check that files were generated in the `output/` folder
3. Download the files directly and play them locally

### **Q: Omnizart is slow / crashes**
**A:** Omnizart runs on **CPU only** due to CUDA version compatibility (it needs CUDA 11.0, we use 11.2 for other models). This means:
- ✅ **Stable** but slower (~3-5 minutes per song)
- Works best on songs with **loud, prominent drums** (rock, metal, electronic)
- May not detect subtle percussion in ballads

### **Q: GPU not detected**
**A:** Check:
1. Run `check_gpu_robust.py` to verify CUDA setup
2. Ensure `cuda_libs/` folder exists with DLLs
3. Restart the app after adding CUDA files

---

## 📜 Credits

Developed by **NC-Engineering**.
*   **Powered by**: TensorFlow, PyTorch, Gradio, Librosa, Omnizart, Basic Pitch.

---
*Generated by Antigravity AI*
