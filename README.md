# Sheet Sage V3 - Professional Audio Transcription

![Sheet Sage Logo](ic_logo.png)

**Sheet Sage** is a professional AI-powered audio transcription tool that converts music into lead sheets, MIDI files, and sheet music. Built with state-of-the-art machine learning models and featuring a sleek, native desktop interface.

## ✨ Key Features

### 🎵 Multiple Transcription Modes
- **Lead Sheet (Standard)** - Melody + Chords + Key + Tempo detection
- **Piano (Polyphonic)** - Full piano transcription with pedal detection
- **Basic Pitch (Polyphonic)** - Spotify's model with pitch bend support
- **Drums (Omnizart)** - Drum kit transcription
- **SheetSage V3 (Lunaverus)** - Custom CNN trained on MAESTRO dataset

### 🎨 Professional Native UI
- **AnthemScore-Inspired Design** - Clean, modern dark theme
- **Dialog-Based Workflow** - Intuitive: Open → Configure → Transcribe
- **Real-Time Piano Roll** - Visualize notes with spectrogram background
- **Audio Mixer** - Synchronized playback with independent volume controls
- **Live Progress Tracking** - See transcription status in real-time

### 🚀 Advanced Features
- **Vocal Separation** - Integrated Demucs for cleaner melody extraction
- **GPU Acceleration** - CUDA-optimized for fast processing
- **Sheet Music Export** - Professional PDF generation via LilyPond
- **MIDI Synthesis** - High-quality audio preview with FluidSynth
- **Batch Processing** - Queue multiple files (future feature)

## 📦 Installation

### Prerequisites
- **Windows 10/11** (Primary platform)
- **NVIDIA GPU** (Recommended for faster processing)
- **Git** (for cloning repository)

### One-Click Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/AgentHitmanFaris/sheetsageV2.git
   cd sheetsageV2
   ```

2. **Run Setup**
   ```bash
   setup_local.bat
   ```
   
   This automatically:
   - Downloads embedded Python 3.11
   - Installs PyTorch 2.8.0 with CUDA 12.1
   - Fetches all AI models
   - Configures system tools (FFmpeg, FluidSynth, LilyPond)

## 🎯 Usage

### Launch Application
```bash
run_local.bat
```

The native UI will open automatically with a clean interface.

### Workflow

1. **Click "📂 Open..."** to select your audio file
2. **Configure Settings** in the popup dialog:
   - Choose transcription mode
   - Enable/disable vocal separation
   - Set time range (full song or section)
   - Adjust display settings
3. **Click "✓ Start Transcription"**
4. **View Results** in the piano roll and log panel
5. **Play Back** using the audio mixer

### Transcription Modes Explained

| Mode | Best For | Output | Processing Time |
|------|----------|--------|----------------|
| **Lead Sheet** | Pop, Jazz, Standards | Melody + Chords PDF | ~2 min |
| **Piano** | Solo Piano | Detailed MIDI + Pedals | ~1 min |
| **Basic Pitch** | All Instruments | Polyphonic MIDI | ~1 min |
| **Drums** | Drum Tracks | Drum MIDI | ~2 min |
| **Lunaverus** | Classical Piano | High-Accuracy MIDI | ~1 min |

*Times based on 3-minute song with GTX 1060 GPU*

## 🏗️ Architecture

### Technology Stack
- **Frontend**: PySide6 (Qt for Python)
- **Backend**: Python 3.11 Embedded
- **Audio Processing**: librosa, FFmpeg
- **AI Models**:
  - Sheet Sage V2 (Harmony/Structure)
  - Spotify Basic Pitch (Melody/Polyphony)
  - Demucs (Vocal Separation)
  - ByteDance Piano Transcription
  - Omnizart (Drums)
  - Lunaverus CNN (Custom Model)
- **Rendering**: LilyPond (Notation), FluidSynth (Audio)

### Project Structure
```
sheetsageV2/
├── SheetSage_Core/          # Core transcription engine
│   ├── sheetsage/           # Python package
│   ├── scripts/             # Inference scripts
│   ├── libs/                # Bundled tools (LilyPond, FluidSynth)
│   └── cache/               # Model cache
├── sheetsage_gui/           # Native Qt application (Restructured)
├── static/                  # Project assets (banner, etc.)
│   ├── widgets/             # UI components
│   ├── workers/             # Background processing
│   └── resources/           # Styles, icons
└── static/                  # Web assets (legacy)
```

## 🐛 Troubleshooting

### Common Issues

**GPU Not Detected**
- Verify CUDA installation: `nvidia-smi`
- Check PyTorch: `python -c "import torch; print(torch.cuda.is_available())"`

**Permission Denied Errors**
- Run as Administrator (Windows)
- Check antivirus isn't blocking file writes

**Slow Transcription**
- Ensure GPU mode is enabled
- Close other GPU-intensive applications
- Try shorter audio segments first

**Missing Dependencies**
- Re-run `setup_local.bat`
- Check internet connection
- Manual install: `pip install -r SheetSage_Core/requirements.txt`

### Recent Fixes (v0.5.0)
- ✅ **Live MIDI Playback** - Real-time feedback during editing
- ✅ **Interactive Editing** - Hear notes as you move them
- ✅ **Improved Stability** - Fixed audio driver and crash issues
- ✅ **Data Persistence** - Always-on metadata and reliable saving

## 🗺️ Roadmap

- [ ] macOS/Linux support
- [ ] Real-time transcription (live input)
- [ ] Batch processing queue
- [ ] Custom model training UI
- [ ] Audio effects (reverb, EQ)
- [ ] Export to MusicXML
- [ ] Cloud model hosting

## 📝 License

MIT License - See [LICENSE](LICENSE) for details

**Note**: Individual AI models may have separate licenses. Check model documentation for commercial usage restrictions.

## 🙏 Acknowledgments

- **Spotify** - Basic Pitch model
- **ByteDance** - Piano Transcription model
- **Meta/Facebook** - Demucs source separation
- **Music-and-Culture-Technology-Lab** - Omnizart
- **LilyPond Project** - Music engraving
- **AnthemScore** - UI design inspiration

## 📧 Contact

- **GitHub**: [AgentHitmanFaris/sheetsageV2](https://github.com/AgentHitmanFaris/sheetsageV2)
- **Issues**: [Report bugs here](https://github.com/AgentHitmanFaris/sheetsageV2/issues)

---

**Version**: 0.5.0  
**Last Updated**: December 23, 2025  
**Status**: Active Development
