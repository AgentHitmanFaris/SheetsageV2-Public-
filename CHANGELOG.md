# Changelog

All notable changes to Sheet Sage will be documented in this file.

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
