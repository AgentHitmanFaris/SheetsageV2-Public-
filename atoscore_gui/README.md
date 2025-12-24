# NC- AtoScore Native UI

Native Windows desktop application for NC- AtoScore music transcription suite.

## Quick Start

### Running the Application

```bash
cd d:/Document/atoscore/atoscore_gui
D:\Document\atoscore\atoscore_Core\python_embeded\python.exe main.py
```

### Development Status

**Current Phase**: Implementation (In Progress)

✅ **Completed**:
- PySide6 installation and setup
- Project folder structure
- Main window with menu bar
- Toolbar with quick actions
- Dark theme stylesheet (#7c3aed purple accents)
- Three-panel layout (placeholder)
- Status bar with GPU/CPU detection

🚧 **In Progress**:
- File input panel widget (left sidebar)
- Transcription log/results view (center panel)
- Audio mixer panel (right panel)

📋 **Planned**:
- Worker threads for async transcription
- Settings dialog
- History browser
- Build script for EXE packaging

## Project Structure

```
newUI/
├── launcher.py              # Application entry point
├── main_window.py           # Main window class
├── requirements.txt         # PySide6 dependencies
├── widgets/                 # Custom UI widgets
│   ├── file_input_panel.py      # Left sidebar (TODO)
│   ├── transcription_view.py    # Center panel (TODO)
│   ├── audio_mixer_panel.py     # Right panel (TODO)
│   ├── settings_dialog.py       # Settings window (TODO)
│   └── history_browser.py       # History view (TODO)
├── workers/                 # Background processing
│   └── transcription_worker.py  # QThread worker (TODO)
├── resources/               # Assets
│   ├── styles.qss          # Dark theme stylesheet
│   └── icons/              # Application icons (TODO)
└── utils/                   # Helper functions
    └── audio_player.py     # Audio playback (TODO)
```

## Backend Integration

The native UI imports backend modules from `../atoscore_Core`:

```python
import sys
sys.path.insert(0, '../atoscore_Core')

from atoscore.basic_pitch_transcription import transcribe_basic_pitch
from atoscore.piano_transcription import transcribe_piano
from atoscore.modules.omnizart_transcription import run_omnizart
# ... etc
```

This allows both UIs (Gradio and Native) to run in parallel without conflicts.

## Testing

### Manual Test
1. Launch the application
2. Verify main window appears
3. Check menu bar (File, Edit, View, Tools, Help)
4. Test "Tools > Check GPU Status"
5. Verify status bar shows GPU/CPU info

### Integration Test (TODO)
```bash
python -m pytest tests/ -v
```

## Building Executable (TODO)

```bash
python build_exe.py
```

This will create a standalone `atoscore.exe` in the `dist/` folder.

## Notes

- **Parallel Development**: This folder is separate from atoscore_Core to allow testing both UIs
- **Migration**: Once stable, this will be moved to `atoscore_Core/atoscore_native/`
- **Dependencies**: Uses the same Python environment as atoscore_Core

