# Changelog

All notable changes to NC- AtoScore will be documented in this file.

## [v3.0.0] - 2024-12-24

### Rebranding & Ownership Transfer
- **Complete Rebranding** - Project renamed from "SheetSage" to **NC- AtoScore**
- **New Developer** - Transferred ownership from Muhammad Faris Hakim to **NC-Engineering**
- **Repository Migration** - Moved to `https://github.com/AgentHitmanFaris/NC-AtoScore`
- **Updated Branding** - All UI elements, documentation, and build artifacts reflect new identity
- **Environment Variables** - Renamed from `SHEETSAGE_*` to `ATOSCORE_*` for consistency
- **Cache Migration** - Automatic migration from `.sheetsage` to `.atoscore` directory

### Video File Support
- **Video Transcription** - Extract audio from video files automatically
  - Supported formats: MP4, MKV, AVI, MOV, WebM, WMV, FLV, M4V
  - Uses FFmpeg for high-quality audio extraction
  - Transparent workflow: Open video → Transcribe as normal
- **Automatic Detection** - App identifies video files and extracts audio in background
- **Temp Management** - Extracted audio files are cached and cleaned up automatically

### Transcription Improvements
- **Basic Pitch (Standalone)** - New mode for pure Basic Pitch transcription
  - No beat tracking or harmony analysis
  - Faster processing and simpler output
  - Ideal for quick MIDI conversions
- **Checksum Bypass** - Disabled model file validation for seamless cache migration
- **Beat Tracking Fix** - Resolved `AssertionError` in downbeat detection
  - Normalized downbeat indices to prevent out-of-range errors
  - Added meter safety checks (defaults to 4/4 if unsupported)

### Bug Fixes
- **Asset Download** - Fixed `yt-dlp` path errors after folder rename
  - Updated to use `sys.executable -m yt_dlp` instead of broken `.exe` launcher
  - Ensures future downloads work across directory structure changes
- **Omnizart Drums** - Fixed `ModuleNotFoundError: No module named '_ctypes'`
  - Updated to use embedded Python with all required DLLs
  - Drum transcription now fully functional
- **GUI Imports** - Corrected `from widgets` to `from ui.widgets` throughout UI code
- **Application Icon** - Restored window icon display
  - Icon now appears in title bar, taskbar, and Alt+Tab switcher

### Documentation
- **Professional Updates** - Comprehensive CHANGELOG and README improvements
- **Updated Screenshots** - Reflect NC- AtoScore branding
- **Migration Guide** - Clear documentation for users upgrading from SheetSage

---

## [v0.5.0] - 2025-12-23

### 🎹 Live MIDI & Interactive Editing
- **Live MIDI Playback** - Real-time note playback directly from the editor
  - "Use Live MIDI" toggle in Audio Mixer
  - Instant audio feedback when clicking notes
  - High-frequency scheduler loop for accurate timing
- **Interactive Editing** - Hear changes instantly while dragging/resizing notes
- **View Toggle** - Dedicated button to switch between Piano Piano Roll and Drum Editor
- **Persistent Metadata** - Always-visible display for BPM, Key, and Time Signature

### 🐛 Fixed
- **Startup Crash** - Fixed `AttributeError` in AudioMixerPanel initialization order
- **FluidSynth Driver Error** - Added robust driver search (WASAPI/DSound fallback) for Windows
- **Editor Signals** - Fixed missing signals for note previews and data updates
- **Drum Synthesis** - Fixed crash when synthesizing empty drum tracks

### ⚡ Improvements
- **Project Loading** - Unified file loader accepts both audio and `.sage` projects
- **Auto-Cleanup** - Aggressive temporary file deletion on exit
- **Vocal Separation** - Enabled Demucs separation for Basic Pitch mode

---

## [v0.4.0] - 2025-12-22

### 🎨 Major UI Redesign - AnthemScore-Inspired Interface

#### Added
- **Native UI Application** - Built with PySide6 (Qt) for professional desktop experience
- **AnthemScore-Inspired Design** - Clean, dark theme with blue accents (#2196f3)
- **Dialog-Based Workflow** - Open → Settings Dialog → Transcribe (cleaner UX)
- **Transcription Settings Dialog** - All options in one focused popup
  - File selection with instant display
  - Mode selection (Lead Sheet, Piano, Basic Pitch, Drums, Lunaverus)
  - Processing options (Vocal separation, PDF generation)
  - Time range settings (full song or section)
  - Display settings (spectrogram, resolution, time step)
- **Piano Roll Viewer** - Real-time visualization with spectrogram background
- **Audio Mixer Panel** - Synchronized playback with independent volume controls
- **2-Panel Layout** - Sidebar (controls) + Main area (piano roll)

#### Changed
- Simplified sidebar to single "Open" button for cleaner interface
- Removed redundant toolbar (actions now in menu bar and sidebar)
- Increased sidebar width (380-480px) for better readability
- Updated color scheme from purple (#7c3aed) to blue (#2196f3)
- Streamlined file input workflow - removed bulky drop zone

#### Fixed
- **Basic Pitch MIDI Generation Error** - Fixed `[Errno 13] Permission denied` by passing correct file path instead of directory
- **Lunaverus Import Error** - Renamed `run_inference` to `run_lunaverus` with backward compatibility alias
- **Squashed UI Elements** - Adjusted panel widths and spacing for proper content display
- **Missing Button References** - Removed references to deprecated UI elements

#### Technical Improvements
- Clean separation of concerns (Dialog for settings, Panel for layout)
- Proper signal/slot connections for Qt event handling
- Improved file path handling for cross-platform compatibility
- Better error handling and user feedback

---

## [v0.3.3] - 2024-12-16

### Added
- **History Tab** - Browse and reload previous transcription projects
  - Organized by song name and timestamp
  - One-click restore of full mixer state and piano roll
- **Secure File Caching** - `temp_playback` folder for web player access

### Fixed
- **Audio Playback 404 Errors** - Implemented secure file caching system
- **Audio Truncation** - Fixed 30-second playback limit
- **Restart Loops** - Improved app restart stability
- **Vocals Track Muting** - Default vocals to 0% volume for clarity

### Changed
- Improved "Restart App" functionality
- Added "No audio file provided" safety warning

---

## [v0.3.0] - 2024-12-15

### Added
- **Multi-Track Audio Mixer** - Interactive web-based preview
  - Original audio, synthesized MIDI, separated vocals
  - Independent volume controls
  - Synchronized playback
- **Vocal Separation** - Integrated Demucs for melody isolation
- **GPU Acceleration** - CUDA 12.1 support for faster transcription

### Changed
- Upgraded to PyTorch 2.8.0
- Improved model caching and temporary file handling
- Better error messages and status updates

---

## [v0.2.0] - 2024-12-10

### Added
- **Piano Transcription Mode** - ByteDance's piano model integration
- **Basic Pitch Mode** - Spotify's polyphonic transcription
- **Lead Sheet Generation** - PDF output with LilyPond
- **MIDI Synthesis** - FluidSynth audio preview

### Changed
- Switched to Gradio web interface
- Embedded Python environment for easier deployment

---

## [v0.1.0] - 2024-12-01

### Added
- Initial release
- Basic audio to MIDI transcription
- Command-line interface
- Sheet Sage V2 model integration
