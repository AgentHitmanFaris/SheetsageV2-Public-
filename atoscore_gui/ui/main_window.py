"""
Main Window for SheetSage Native UI
Implements the primary application window with menu bar, toolbar, and three-panel layout
"""

import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QSplitter,
    QMessageBox, QLabel, QScrollArea, QFileDialog
)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QSize


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NC- AtoScore - Music Transcription Suite")
        self.setMinimumSize(1400, 800)
        
        # Transcription state
        self.current_worker = None
        self.current_config = None
        
        # Project state (temp/saved)
        self.current_project_path = None  # Path to current .sage if saved
        self.current_output_dir = None    # Current working output directory
        self.is_project_saved = False     # Has user explicitly saved?
        self.temp_projects = []           # List of temp project dirs to cleanup
        
        # Temp folder for unsaved projects
        self.temp_base = os.path.join(os.path.dirname(__file__), '..', '..', 'AtoScore_Core', 'temp_projects')
        os.makedirs(self.temp_base, exist_ok=True)
        
        # Initialize UI components
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        self._setup_shortcuts()
        
        # GPU/CPU status check
        self._update_hardware_status()
    
    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Audio File...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip("Open an audio file for transcription")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        open_project_action = QAction("📦 Open &Project (.sage)...", self)
        open_project_action.setShortcut("Ctrl+Shift+O")
        open_project_action.setStatusTip("Open a saved SheetSage project file")
        open_project_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        batch_action = QAction("📁 &Batch Transcribe...", self)
        batch_action.setShortcut("Ctrl+B")
        batch_action.setStatusTip("Transcribe multiple audio files")
        batch_action.triggered.connect(self._on_batch_transcribe)
        file_menu.addAction(batch_action)
        
        export_xml_action = QAction("🎼 &Export to MusicXML...", self)
        export_xml_action.setShortcut("Ctrl+E")
        export_xml_action.setStatusTip("Export transcription to MusicXML for MuseScore/Finale/Sibelius")
        export_xml_action.triggered.connect(self._on_export_musicxml)
        file_menu.addAction(export_xml_action)
        
        open_notation_action = QAction("🎹 &Open in Notation Software", self)
        open_notation_action.setShortcut("Ctrl+Shift+E")
        open_notation_action.setStatusTip("Export and open directly in your notation software")
        open_notation_action.triggered.connect(self._on_open_in_notation)
        file_menu.addAction(open_notation_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.setStatusTip("Configure application settings")
        settings_action.triggered.connect(self._on_settings)
        edit_menu.addAction(settings_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        history_action = QAction("&History Browser", self)
        history_action.setShortcut("Ctrl+H")
        history_action.setStatusTip("View transcription history")
        history_action.triggered.connect(self._on_history)
        view_menu.addAction(history_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        check_gpu_action = QAction("Check &GPU Status", self)
        check_gpu_action.setStatusTip("Check GPU hardware status")
        check_gpu_action.triggered.connect(self._on_check_gpu)
        tools_menu.addAction(check_gpu_action)
        
        tools_menu.addSeparator()
        
        compress_action = QAction("📦 &Compress Output Folder...", self)
        compress_action.setStatusTip("Compress an output folder to save storage")
        compress_action.triggered.connect(self._on_compress_output)
        tools_menu.addAction(compress_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        docs_action = QAction("&Documentation", self)
        docs_action.setStatusTip("View user documentation")
        docs_action.triggered.connect(self._on_docs)
        help_menu.addAction(docs_action)
        
        shortcuts_action = QAction("⌨️ &Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.setStatusTip("View keyboard shortcuts")
        shortcuts_action.triggered.connect(self._on_shortcuts_help)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About NC- AtoScore", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # Open File action
        open_action = QAction("Open", self)
        open_action.setStatusTip("Open audio file")
        open_action.triggered.connect(self._on_open_file)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # Transcribe action
        transcribe_action = QAction("Transcribe", self)
        transcribe_action.setStatusTip("Start transcription")
        transcribe_action.triggered.connect(self._on_transcribe)
        toolbar.addAction(transcribe_action)
        
        toolbar.addSeparator()
        
        # History action
        history_action = QAction("History", self)
        history_action.setStatusTip("View history")
        history_action.triggered.connect(self._on_history)
        toolbar.addAction(history_action)
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.setStatusTip("Configure settings")
        settings_action.triggered.connect(self._on_settings)
        toolbar.addAction(settings_action)
    
    def _create_central_widget(self):
        """Create central widget with Sidebar and Piano Roll layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        
        # === Left Sidebar with Scroll Area ===
        # Create scroll area for sidebar content
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        sidebar_scroll.setFrameShape(QScrollArea.NoFrame)
        
        # Sidebar content widget
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(1)
        
        # File Input Section
        from ui.widgets.file_input_panel import FileInputPanel
        self.file_input_panel = FileInputPanel()
        self.file_input_panel.file_selected.connect(self._on_file_selected)
        self.file_input_panel.project_loaded.connect(self._on_project_file_selected)
        self.file_input_panel.transcribe_requested.connect(self._on_transcribe_requested)
        self.file_input_panel.save_requested.connect(self._save_project_as)
        # Add margins for Sidebar look
        self.file_input_panel.setContentsMargins(4, 4, 4, 4)
        sidebar_layout.addWidget(self.file_input_panel)
        
        # Audio Mixer Section
        from ui.widgets.audio_mixer_panel import AudioMixerPanel
        self.audio_mixer = AudioMixerPanel()
        self.audio_mixer.playback_started.connect(self._on_playback_started)
        self.audio_mixer.playback_stopped.connect(self._on_playback_stopped)
        self.audio_mixer.playback_position_changed.connect(self._on_playback_position_changed)
        self.audio_mixer.setContentsMargins(4, 4, 4, 4)
        sidebar_layout.addWidget(self.audio_mixer)
        
        # Add stretch at bottom
        sidebar_layout.addStretch()
        
        # Set the content widget to scroll area
        sidebar_scroll.setWidget(sidebar_widget)
        
        # Add scroll area to splitter
        sidebar_scroll.setMinimumWidth(380)
        sidebar_scroll.setMaximumWidth(480)
        splitter.addWidget(sidebar_scroll)
        
        # === Center Panel (TranscriptionView) ===
        from ui.widgets.transcription_view import TranscriptionView
        self.transcription_view = TranscriptionView()
        self.transcription_view.file_download_requested.connect(self._on_file_download)
        self.transcription_view.midi_saved.connect(self._on_midi_saved)
        # Live MIDI connections
        self.transcription_view.live_notes_changed.connect(self.audio_mixer.set_live_notes)
        self.transcription_view.note_preview_request.connect(self.audio_mixer.preview_note)
        splitter.addWidget(self.transcription_view)
        
        # Set initial splitter sizes (Sidebar 28%, Main 72%)
        splitter.setSizes([400, 1000])
        splitter.setCollapsible(0, True)
        
        main_layout.addWidget(splitter)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Progress bar (hidden by default)
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)
        
        # Hardware status label (permanent widget)
        self.hardware_label = QLabel("Initializing...")
        self.statusbar.addPermanentWidget(self.hardware_label)
        
        # Show ready message
        self.statusbar.showMessage("Ready", 3000)
    
    def _update_hardware_status(self):
        """Check and display GPU/CPU status"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                self.hardware_label.setText(f"🎮 GPU: {gpu_name}")
                self.hardware_label.setStatusTip("GPU acceleration enabled")
            else:
                self.hardware_label.setText("💻 CPU Mode")
                self.hardware_label.setStatusTip("Running on CPU")
        except ImportError:
            self.hardware_label.setText("⚠️ Hardware check failed")
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for power users"""
        # File shortcuts
        # Ctrl+O is already in menu, but add explicit shortcut
        open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_shortcut.activated.connect(self._on_open_file)
        
        # Ctrl+S - Save MIDI (if in piano roll)
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._on_save_midi)
        
        # Ctrl+Q - Quit
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.close)
        
        # Edit shortcuts
        # Ctrl+Z - Undo
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._on_undo)
        
        # Ctrl+Y - Redo
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self._on_redo)
        
        # Delete - Delete selected note
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._on_delete_note)
        
        # Playback shortcuts
        # Space - Play/Pause
        play_pause_shortcut = QShortcut(QKeySequence("Space"), self)
        play_pause_shortcut.activated.connect(self._on_play_pause)
        
        # Shift+Space - Stop
        stop_shortcut = QShortcut(QKeySequence("Shift+Space"), self)
        stop_shortcut.activated.connect(self._on_stop_playback)
        
        # Home - Jump to start
        home_shortcut = QShortcut(QKeySequence("Home"), self)
        home_shortcut.activated.connect(self._on_jump_to_start)
        
        # View shortcuts
        # Ctrl++ - Zoom in
        zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in_shortcut.activated.connect(self._on_zoom_in)
        
        # Ctrl+= - Also zoom in (for keyboards without numpad)
        zoom_in_alt_shortcut = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_alt_shortcut.activated.connect(self._on_zoom_in)
        
        # Ctrl+- - Zoom out
        zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out_shortcut.activated.connect(self._on_zoom_out)
        
        # F1 is set in menu action, not as separate shortcut
        
        # Ctrl+H - History (already in menu)
        history_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        history_shortcut.activated.connect(self._on_history)
    
    def _on_save_midi(self):
        """Save project as .sage file (Ctrl+S)"""
        if not self.current_output_dir:
            # No current project to save
            QMessageBox.information(
                self,
                "Nothing to Save",
                "Please transcribe an audio file first."
            )
            return
        
        self._save_project_as()
    
    def _save_project_as(self):
        """Save current project as .sage file to user-selected location"""
        if not self.current_output_dir:
            return False
        
        # Suggest filename
        default_name = os.path.basename(self.current_output_dir) + ".sage"
        
        from widgets.settings_dialog import SettingsDialog
        settings = SettingsDialog.load_settings_from_file()
        output_dir = settings.get('output_dir', os.path.join(os.getcwd(), 'output'))
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            os.path.join(output_dir, default_name),
            "SheetSage Projects (*.sage);;All Files (*.*)"
        )
        
        if not save_path:
            return False
        
        # Ensure .sage extension
        if not save_path.endswith('.sage'):
            save_path += '.sage'
        
        self.statusbar.showMessage("Saving project...", 0)
        
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'AtoScore_Core'))
            from atoscore.project_bundle import create_project_bundle
            
            # First save any MIDI edits
            # First save any MIDI edits silently to the temp folder
            if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
                piano_roll = self.transcription_view.piano_roll
                # Find the MIDI file in the current temp output dir
                midi_name = "output.mid"
                if piano_roll.current_midi_path:
                    midi_name = os.path.basename(piano_roll.current_midi_path)
                
                temp_midi_path = os.path.join(self.current_output_dir, midi_name)
                piano_roll.save_midi(filepath=temp_midi_path)
            
            # Create bundle
            bundle_path = create_project_bundle(
                self.current_output_dir,
                bundle_name=os.path.splitext(os.path.basename(save_path))[0],
                format='mp3',
                quality='high',
                delete_originals=False  # Keep originals in case user keeps working
            )
            
            if bundle_path:
                # Move bundle to user's chosen location if different
                if os.path.dirname(bundle_path) != os.path.dirname(save_path):
                    import shutil
                    shutil.move(bundle_path, save_path)
                    bundle_path = save_path
                
                # Update state
                self.current_project_path = bundle_path
                self.is_project_saved = True
                
                # We KEEP this folder in self.temp_projects so it gets cleaned up on app exit.
                # The user has the .sage file now, so the loose files are disposable.
                if self.current_output_dir not in self.temp_projects:
                    self.temp_projects.append(self.current_output_dir)
                
                size_mb = os.path.getsize(bundle_path) / (1024 * 1024)

                self.statusbar.showMessage(f"Project saved: {os.path.basename(bundle_path)} ({size_mb:.1f} MB)", 5000)
                self.transcription_view.log_success(f"Saved: {os.path.basename(bundle_path)}")
                
                return True
            else:
                QMessageBox.warning(self, "Save Failed", "Failed to create project bundle.")
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{str(e)}")
            self.statusbar.showMessage("Save failed", 3000)
            return False
    
    def _on_undo(self):
        """Undo last action in piano roll"""
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            undo_stack = self.transcription_view.piano_roll.undo_stack
            if undo_stack.canUndo():
                undo_stack.undo()
                self.statusbar.showMessage("Undo", 1000)
            else:
                self.statusbar.showMessage("Nothing to undo", 1000)
        else:
            self.statusbar.showMessage("Open a MIDI file first", 1000)
    
    def _on_redo(self):
        """Redo last action in piano roll"""
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            undo_stack = self.transcription_view.piano_roll.undo_stack
            if undo_stack.canRedo():
                undo_stack.redo()
                self.statusbar.showMessage("Redo", 1000)
            else:
                self.statusbar.showMessage("Nothing to redo", 1000)
        else:
            self.statusbar.showMessage("Open a MIDI file first", 1000)
    
    def _on_delete_note(self):
        """Delete selected note in piano roll"""
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            canvas = self.transcription_view.piano_roll.canvas
            if canvas.selected_note_idx is not None:
                note = canvas.notes[canvas.selected_note_idx]
                canvas.notes.pop(canvas.selected_note_idx)
                canvas.selected_note_idx = None
                canvas.update()
                self.statusbar.showMessage("Note deleted", 1000)
    
    def _on_play_pause(self):
        """Toggle play/pause"""
        if hasattr(self, 'audio_mixer'):
            # Check if playing by looking at any player state
            if self.audio_mixer._players:
                master_name = self.audio_mixer._master_track
                if master_name and master_name in self.audio_mixer._players:
                    from PySide6.QtMultimedia import QMediaPlayer
                    player = self.audio_mixer._players[master_name]['player']
                    if player.playbackState() == QMediaPlayer.PlayingState:
                        self.audio_mixer._on_pause()
                    else:
                        self.audio_mixer._on_play()
    
    def _on_stop_playback(self):
        """Stop playback"""
        if hasattr(self, 'audio_mixer'):
            self.audio_mixer._on_stop()
    
    def _on_jump_to_start(self):
        """Jump to start of audio"""
        if hasattr(self, 'audio_mixer'):
            self.audio_mixer._on_seek(0)
            self.statusbar.showMessage("Jumped to start", 1000)
    
    def _on_zoom_in(self):
        """Zoom in on piano roll"""
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            self.transcription_view.piano_roll.zoom_in()
    
    def _on_zoom_out(self):
        """Zoom out on piano roll"""
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            self.transcription_view.piano_roll.zoom_out()
    
    def _on_shortcuts_help(self):
        """Show keyboard shortcuts help dialog"""
        shortcuts_text = """
<h2>⌨️ Keyboard Shortcuts</h2>

<h3>File</h3>
<table>
<tr><td><b>Ctrl+O</b></td><td>Open audio file</td></tr>
<tr><td><b>Ctrl+Shift+O</b></td><td>Open project (.sage)</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save edited MIDI</td></tr>
<tr><td><b>Ctrl+B</b></td><td>Batch transcribe</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Export to MusicXML</td></tr>
<tr><td><b>Ctrl+Shift+E</b></td><td>Open in notation software</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Quit application</td></tr>
</table>

<h3>Edit</h3>
<table>
<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
<tr><td><b>Delete</b></td><td>Delete selected note</td></tr>
</table>

<h3>Playback</h3>
<table>
<tr><td><b>Space</b></td><td>Play / Pause</td></tr>
<tr><td><b>Shift+Space</b></td><td>Stop</td></tr>
<tr><td><b>Home</b></td><td>Jump to start</td></tr>
</table>

<h3>View</h3>
<table>
<tr><td><b>Ctrl++</b></td><td>Zoom in</td></tr>
<tr><td><b>Ctrl+-</b></td><td>Zoom out</td></tr>
<tr><td><b>Ctrl+Scroll</b></td><td>Zoom in/out</td></tr>
</table>

<h3>Other</h3>
<table>
<tr><td><b>Ctrl+H</b></td><td>History browser</td></tr>
<tr><td><b>F1</b></td><td>Show this help</td></tr>
</table>
"""
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts_text)
    
    def _on_batch_transcribe(self):
        """Open batch transcription dialog"""
        from ui.widgets.batch_processing_dialog import BatchProcessingDialog
        dialog = BatchProcessingDialog(self)
        dialog.exec()
    
    def _on_export_musicxml(self):
        """Open MusicXML export dialog"""
        from ui.widgets.musicxml_export_dialog import MusicXMLExportDialog
        
        # Get current MIDI path and notes from piano roll if available
        midi_path = None
        notes = None
        
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            piano_roll = self.transcription_view.piano_roll
            midi_path = piano_roll.current_midi_path
            notes = piano_roll.notes
        
        # Also check if we have a result from last transcription
        if not midi_path and hasattr(self, 'current_result') and self.current_result:
            midi_path = self.current_result.get('midi_path')
        
        if not midi_path and not notes:
            QMessageBox.information(
                self,
                "No Data",
                "Please transcribe an audio file first, or open a MIDI file to export."
            )
            return
        
        dialog = MusicXMLExportDialog(midi_path=midi_path, notes=notes, parent=self)
        dialog.export_completed.connect(lambda p: self.statusbar.showMessage(f"Exported: {p}", 5000))
        dialog.exec()
    
    def _on_compress_output(self):
        """Compress an output folder to save storage"""
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        
        # Ask for folder to compress
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder to Compress",
            os.path.join(os.getcwd(), '..', 'AtoScore_Core', 'output')
        )
        
        if not folder:
            return
        
        # Check if folder contains audio files
        has_audio = any(
            f.endswith('.wav') for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))
        )
        
        if not has_audio:
            QMessageBox.warning(
                self,
                "No Audio Files",
                "The selected folder doesn't contain any WAV files to compress."
            )
            return
        
        # Ask for compression format
        formats = ['MP3 (High Quality - 85% smaller)', 'FLAC (Lossless - 50% smaller)', 'OGG (High Quality - 85% smaller)']
        format_choice, ok = QInputDialog.getItem(
            self,
            "Select Compression Format",
            "Choose audio compression format:",
            formats,
            0,
            False
        )
        
        if not ok:
            return
        
        # Map to format code
        format_map = {'MP3': 'mp3', 'FLAC': 'flac', 'OGG': 'ogg'}
        format_code = 'mp3'
        for key in format_map:
            if key in format_choice:
                format_code = format_map[key]
                break
        
        self.statusbar.showMessage("Compressing output folder...", 0)
        
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'AtoScore_Core'))
            from atoscore.project_bundle import create_project_bundle
            
            bundle_path = create_project_bundle(
                folder,
                format=format_code,
                quality='high',
                delete_originals=True
            )
            
            if bundle_path:
                # Get file size
                size_mb = os.path.getsize(bundle_path) / (1024 * 1024)
                QMessageBox.information(
                    self,
                    "Compression Complete",
                    f"✅ Output compressed successfully!\n\n"
                    f"Bundle: {os.path.basename(bundle_path)}\n"
                    f"Size: {size_mb:.1f} MB"
                )
                self.statusbar.showMessage(f"Compressed to {size_mb:.1f} MB", 5000)
            else:
                QMessageBox.warning(self, "Compression Failed", "Failed to create compressed bundle.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Compression failed:\n{str(e)}")
            self.statusbar.showMessage("Compression failed", 3000)
    
    def _on_open_in_notation(self):
        """Export and open directly in notation software"""
        import subprocess
        import tempfile
        from ui.widgets.settings_dialog import SettingsDialog
        
        # Load settings to get notation software path
        settings = SettingsDialog.load_settings_from_file()
        notation_path = settings.get('notation_software', '')
        notation_name = settings.get('notation_name', 'MuseScore')
        
        if not notation_path or not os.path.exists(notation_path):
            reply = QMessageBox.question(
                self,
                "Notation Software Not Configured",
                "No notation software is configured.\n\n"
                "Would you like to configure it now in Settings?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._on_settings()
            return
        
        # Get current MIDI path
        midi_path = None
        notes = None
        
        if hasattr(self, 'transcription_view') and hasattr(self.transcription_view, 'piano_roll'):
            piano_roll = self.transcription_view.piano_roll
            midi_path = piano_roll.current_midi_path
            notes = piano_roll.notes
        
        if not midi_path and hasattr(self, 'current_result') and self.current_result:
            midi_path = self.current_result.get('midi_path')
        
        if not midi_path and not notes:
            QMessageBox.information(
                self,
                "No Data",
                "Please transcribe an audio file first, or open a MIDI file."
            )
            return
        
        self.statusbar.showMessage(f"Exporting to {notation_name}...", 0)
        
        try:
            from ui.widgets.musicxml_export_dialog import convert_midi_to_musicxml, convert_notes_to_musicxml
            
            # Create temp file for MusicXML
            temp_dir = tempfile.gettempdir()
            
            # Use original filename if available
            if midi_path:
                basename = os.path.splitext(os.path.basename(midi_path))[0]
            else:
                basename = "transcription"
            
            output_path = os.path.join(temp_dir, f"{basename}.musicxml")
            
            # Export
            if midi_path and os.path.exists(midi_path):
                convert_midi_to_musicxml(midi_path, output_path, title=basename)
            elif notes:
                convert_notes_to_musicxml(notes, output_path, title=basename)
            
            if os.path.exists(output_path):
                # Open in notation software
                subprocess.Popen([notation_path, output_path])
                self.statusbar.showMessage(f"Opened in {notation_name}", 3000)
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to create MusicXML file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open in notation software:\n{str(e)}")
            self.statusbar.showMessage("Failed to open", 3000)
    
    def _on_open_project(self):
        """Open a .sage project bundle"""
        # Check for unsaved changes first
        if not self._check_unsaved_changes():
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SheetSage Project",
            os.path.join(os.getcwd(), '..', 'AtoScore_Core', 'output'),
            "SheetSage Projects (*.sage);;All Files (*.*)"
        )
        
        if file_path:
            self._load_project_bundle(file_path)

    def _load_project_bundle(self, file_path):
        """Load a .sage project from file path"""
        self.statusbar.showMessage(f"Loading project: {os.path.basename(file_path)}...", 0)
        
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'AtoScore_Core'))
            from atoscore.project_bundle import extract_project_bundle, get_bundle_info
            
            # Get bundle info first
            info = get_bundle_info(file_path)
            
            # Extract to temp directory alongside the .sage file
            output_dir = os.path.splitext(file_path)[0] + "_extracted"
            
            # Extract
            extracted = extract_project_bundle(file_path, output_dir, convert_to_wav=True)
            
            self.transcription_view.log_success(f"Loaded project: {os.path.basename(file_path)}")
            
            # Update state
            self.current_output_dir = output_dir
            if output_dir not in self.temp_projects:
                self.temp_projects.append(output_dir) # Track for cleanup on exit
            self.current_project_path = file_path
            self.is_project_saved = True
            
            # Load MIDI into piano roll
            midi_path = extracted.get('midi')
            if midi_path and os.path.exists(midi_path):
                # Check for audio file for waveform
                audio_for_waveform = None
                # Prefer original, then vocals, then synth
                if extracted.get('original'): audio_for_waveform = extracted.get('original')
                elif extracted.get('vocals'): audio_for_waveform = extracted.get('vocals')

                self.transcription_view.set_piano_roll_data(midi_path, audio_for_waveform)
                self.transcription_view.add_output_file(midi_path)
            
            # Load audio tracks into mixer
            audio_tracks = {}
            audio_dir = os.path.join(output_dir, 'audio')
            if os.path.exists(audio_dir):
                for audio_file in os.listdir(audio_dir):
                    audio_path = os.path.join(audio_dir, audio_file)
                    name = os.path.splitext(audio_file)[0].replace('_', ' ').title()
                    audio_tracks[name] = audio_path
                    self.transcription_view.add_output_file(audio_path)
            
            if audio_tracks:
                self.audio_mixer.load_audio_tracks(audio_tracks)
            
            # Load PDF
            pdf_path = extracted.get('pdf')
            if pdf_path and os.path.exists(pdf_path):
                self.transcription_view.add_output_file(pdf_path)
            
            # Show info
            savings = info.get('savings_percent', 0) if info else 0
            original_mb = info.get('original_size_mb', 0) if info else 0
            compressed_mb = info.get('compressed_size_mb', 0) if info else 0
            
            self.statusbar.showMessage(
                f"Project loaded! (Saved {savings:.0f}% - {original_mb:.1f}MB → {compressed_mb:.1f}MB)", 
                5000
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")
            self.statusbar.showMessage("Failed to load project", 3000)
    
    # Action handlers (placeholders)
    def _on_project_file_selected(self, file_path):
        """Handle project file selected from Input Panel"""
        # Prompt for unsaved changes since we are loading a new project
        if self._check_unsaved_changes():
            self._load_project_bundle(file_path)

    def _on_file_selected(self, file_path):
        """Handle file selection from input panel"""
        self.statusbar.showMessage(f"File selected: {os.path.basename(file_path)}", 5000)
    
    def _cleanup_single_temp_project(self, path):
        """Cleanup specific temp project directory"""
        if path and os.path.exists(path) and os.path.isdir(path):
            try:
                import shutil
                shutil.rmtree(path)
                if path in self.temp_projects:
                    self.temp_projects.remove(path)
                print(f"Cleaned up temp project: {path}")
            except Exception as e:
                print(f"Failed to cleanup temp project {path}: {e}")

    def _check_unsaved_changes(self):
        """Check for unsaved changes and prompt user.
        Returns True if safe to proceed (Saved, Discarded, or No Changes).
        Returns False if Cancelled.
        """
        if self.current_output_dir and not self.is_project_saved:
            reply = QMessageBox.question(
                self,
                "Unsaved Project",
                "You have an unsaved project open. Would you like to save it before starting a new one?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                if self._save_project_as():
                    return True
                else:
                    return False # Failed to save = Cancel
            elif reply == QMessageBox.Cancel:
                return False
            elif reply == QMessageBox.Discard:
                # User specifically asked to DISCARD changes
                # Clean up the temp directory immediately
                self._cleanup_single_temp_project(self.current_output_dir)
                return True
        
        return True

    def _on_transcribe_requested(self, config):
        """Handle transcription request"""
        # Check for unsaved changes first
        if not self._check_unsaved_changes():
            return
            
        mode = config.get('mode', 'Unknown')
        filename = os.path.basename(config.get('audio_file', ''))
        
        # Store config
        self.current_config = config
        
        # Reset project state (new transcription = new unsaved project)
        self.is_project_saved = False
        self.current_project_path = None
        
        # Create temp output directory for this transcription
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = os.path.splitext(filename)[0][:50]  # Limit filename length
        temp_output_dir = os.path.join(self.temp_base, f"{basename}_{timestamp}")
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Track this temp project
        self.current_output_dir = temp_output_dir
        self.temp_projects.append(temp_output_dir)
        
        # Override output dir in config to use temp
        config['output_dir'] = temp_output_dir
        
        # Update UI
        self.statusbar.showMessage(f"Starting {mode} transcription for {filename}...", 0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Log to transcription view
        self.transcription_view.log_progress(f"Starting {mode} transcription...")
        self.transcription_view.log_info(f"File: {filename}")
        self.transcription_view.log_info(f"Separate Vocals: {config.get('separate_vocals', False)}")
        self.transcription_view.log_info(f"Generate PDF: {config.get('generate_pdf', False)}")
        self.transcription_view.log_info(f"Output: temp folder (press Ctrl+S to save)")
        
        # Clear previous results
        self.transcription_view.clear_output_files()
        self.audio_mixer.clear_audio()
        
        # Create and start worker
        from workers.transcription_worker import TranscriptionWorker
        self.current_worker = TranscriptionWorker(config)
        self.current_worker.progress_update.connect(self._on_transcription_progress)
        self.current_worker.progress_percent.connect(self._on_transcription_percent)
        self.current_worker.transcription_finished.connect(self._on_transcription_finished)
        self.current_worker.finished.connect(self._on_worker_thread_finished) # Native QThread finished
        self.current_worker.error.connect(self._on_transcription_error)
        self.current_worker.start()
    
    def _on_transcription_progress(self, message):
        """Handle progress message from worker"""
        self.transcription_view.log_progress(message)
    
    def _on_worker_thread_finished(self):
        """Cleanup worker reference when thread actually exits"""
        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None
    
    def _on_transcription_percent(self, percent):
        """Handle progress percentage from worker"""
        self.progress_bar.setValue(percent)
    
    def _on_transcription_finished(self, result):
        """Handle transcription completion"""
        # Reset UI
        self.progress_bar.setVisible(False)
        # Worker cleanup handled by _on_worker_thread_finished via native finished signal
        
        mode = result.get('mode', 'Unknown')
        
        # Format metadata string
        meta = result.get('metadata', {})
        meta_str = ""
        if meta:
            parts = []
            if 'bpm' in meta: parts.append(f"Tempo: {meta['bpm']} BPM")
            if 'meter' in meta: parts.append(f"Time: {meta['meter']}")
            if 'key' in meta: parts.append(f"Key: {meta['key']}")
            if parts:
                meta_str = f"\n📊 {' | '.join(parts)}"
        
        # Update persistent metadata display
        self.transcription_view.set_song_metadata(
            bpm=meta.get('bpm'),
            key=meta.get('key'),
            time_sig=meta.get('meter')
        )
                
        self.transcription_view.log_success(f"{mode} transcription completed!{meta_str}")
        
        status_msg = f"Transcription completed!"
        if 'bpm' in meta and 'key' in meta:
            status_msg += f" ({meta['bpm']} BPM, {meta['key']})"
        self.statusbar.showMessage(status_msg, 8000)
        
        # Add output files
        if result.get('midi_path'):
            self.transcription_view.add_output_file(result['midi_path'])
        if result.get('pdf_path'):
            self.transcription_view.add_output_file(result['pdf_path'])
        if result.get('synth_path'):
            self.transcription_view.add_output_file(result['synth_path'])
        if result.get('mixed_path'):
            self.transcription_view.add_output_file(result['mixed_path'])
        
        # Load piano roll
        # Load piano roll
        if result.get('midi_path'):
            audio_path = result.get('original_path') or self.current_config.get('audio_file')
            is_drum = (self.current_config.get('mode') == "Drums (Omnizart)")
            self.transcription_view.set_piano_roll_data(result['midi_path'], audio_path, is_drum=is_drum)
        
        # Load audio mixer
        audio_tracks = {}
        if result.get('original_path'):
            audio_tracks['Original'] = result['original_path']
        if result.get('synth_path'):
            audio_tracks['Synthesized'] = result['synth_path']
        if result.get('vocals_path'):
            audio_tracks['Vocals'] = result['vocals_path']
        
        if audio_tracks:
            self.audio_mixer.load_audio_tracks(audio_tracks)
            
        # Update state immediately and track for cleanup
        if result.get('output_dir'):
            self.current_output_dir = result['output_dir']
            self.is_project_saved = False
            self.is_project_modified = True # It's a new transcription
            
            # Track for cleanup on exit (unless saved to .sage later which keeps tracking it)
            if self.current_output_dir not in self.temp_projects:
                self.temp_projects.append(self.current_output_dir)
            
            if hasattr(self, 'file_input_panel'):
                self.file_input_panel.enable_save_button(True)
    
    def _on_transcription_error(self, error_message):
        """Handle transcription error"""
        self.progress_bar.setVisible(False)
        if hasattr(self.file_input_panel, 'transcribe_btn'):
            self.file_input_panel.transcribe_btn.setEnabled(True)
        # Worker cleanup handled by _on_worker_thread_finished
        
        self.transcription_view.log_error(f"Transcription failed: {error_message}")
        self.statusbar.showMessage("Transcription failed", 5000)
        
        QMessageBox.critical(self, "Transcription Error", 
                           f"Transcription failed:\n\n{error_message}")
    
    def _on_cancel_transcription(self):
        """Handle transcription cancellation"""
        if self.current_worker and self.current_worker.isRunning():
            self.transcription_view.log_warning("Cancelling transcription...")
            self.current_worker.cancel()
            self.current_worker.wait()
            
            self.progress_bar.setVisible(False)
            # Worker cleanup handled by _on_worker_thread_finished
            
            self.transcription_view.log_warning("Transcription cancelled by user")
            self.statusbar.showMessage("Transcription cancelled", 3000)
    
    def _on_file_download(self, file_path):
        """Handle file download request"""
        self.statusbar.showMessage(f"Downloaded: {os.path.basename(file_path)}", 3000)

    def _on_midi_saved(self, midi_path):
        """Handle MIDI saved event - resynthesize audio"""
        self.statusbar.showMessage("Re-synthesizing audio from edited MIDI...", 0)
        self.transcription_view.log_progress("Re-synthesizing audio from edits...")
        
        # Run in background to avoid freezing UI
        # For now, running synchronously for simplicity, but should be threaded
        try:
            from sheetsage.audio_utils import synthesize_midi
            
            # Determine output wav path (overwrite synth.wav or create new)
            output_dir = os.path.dirname(midi_path)
            synth_path = os.path.join(output_dir, 'synth_edited.wav')
            
            # Synthesize
            synthesize_midi(midi_path, synth_path)
            
            if os.path.exists(synth_path):
                self.transcription_view.log_success("Audio re-synthesized successfully")
                self.statusbar.showMessage("Audio re-synthesized", 3000)
                
                # Add to file list if new
                self.transcription_view.add_output_file(synth_path)
                
                # Reload in mixer
                self.audio_mixer.load_track("Synthesized", synth_path)
                self.transcription_view.log_info(f"Loaded new audio: {os.path.basename(synth_path)}")
            else:
                raise Exception("Output file not created")
                
        except Exception as e:
            self.transcription_view.log_error(f"Re-synthesis failed: {e}")
            self.statusbar.showMessage("Re-synthesis failed", 5000)
            
    def _on_playback_started(self):
        """Handle audio playback started"""
        self.statusbar.showMessage("Playing audio...", 0)
    
    def _on_playback_stopped(self):
        """Handle audio playback stopped"""
        self.statusbar.showMessage("Playback stopped", 3000)
    
    def _on_playback_stopped(self):
        """Handle audio playback stopped"""
        self.statusbar.showMessage("Playback stopped", 3000)
    
    def _on_playback_position_changed(self, position_ms):
        """Handle audio playback position changed"""
        if hasattr(self, 'transcription_view'):
            # Convert ms to seconds
            seconds = position_ms / 1000.0
            self.transcription_view.set_playback_time(seconds)
    
    def _on_open_file(self):
        """Handle open file action"""
        # Trigger the file input panel's browse dialog
        if hasattr(self, 'file_input_panel'):
            self.file_input_panel._on_open_clicked()
    
    def _on_transcribe(self):
        """Handle transcribe action"""
        QMessageBox.information(self, "Transcribe", "Transcription will start here")
    
    def _on_settings(self):
        """Handle settings action"""
        from widgets.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, self._get_current_settings())
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
    
    def _get_current_settings(self):
        """Get current application settings"""
        # Load from file or return defaults
        from widgets.settings_dialog import SettingsDialog
        return SettingsDialog.load_settings_from_file()
    
    def _on_settings_saved(self, settings):
        """Handle settings saved"""
        self.statusbar.showMessage("Settings saved successfully", 3000)
        self.transcription_view.log_success("Settings updated")
    
    def _on_history(self):
        """Handle history action"""
        from widgets.history_browser import HistoryBrowser
        from widgets.settings_dialog import SettingsDialog
        import os
        
        # Get output directory from settings
        settings = SettingsDialog.load_settings_from_file()
        output_dir = settings.get('output_dir', os.path.join(os.getcwd(), 'output'))
        
        # Show history browser
        dialog = HistoryBrowser(output_dir, self)
        dialog.project_selected.connect(self._on_history_project_loaded)
        dialog.exec()
    
    def _on_history_project_loaded(self, project_data):
        """Handle loading a project from history"""
        mode = project_data.get('mode', 'Unknown')
        self.transcription_view.log_info(f"Loaded project: {mode}")
        self.statusbar.showMessage(f"Loaded {mode} project from history", 5000)
        
        # Clear previous
        self.transcription_view.clear_output_files()
        
        # Add files
        if project_data.get('midi_path'):
            self.transcription_view.add_output_file(project_data['midi_path'])
        if project_data.get('pdf_path'):
            self.transcription_view.add_output_file(project_data['pdf_path'])
        if project_data.get('synth_path'):
            self.transcription_view.add_output_file(project_data['synth_path'])
        if project_data.get('mixed_path'):
            self.transcription_view.add_output_file(project_data['mixed_path'])
        
        # Load piano roll
        if project_data.get('midi_path'):
            audio_path = project_data.get('original_path')
            is_drum = ("Drum" in mode)
            self.transcription_view.set_piano_roll_data(project_data['midi_path'], audio_path, is_drum=is_drum)
            
            # Update metadata display
            meta = project_data.get('metadata', {})
            self.transcription_view.set_song_metadata(
                bpm=meta.get('bpm'),
                key=meta.get('key'),
                time_sig=meta.get('meter')
            )
        
        # Load audio mixer
        audio_tracks = {}
        if project_data.get('original_path'):
            audio_tracks['Original'] = project_data['original_path']
        if project_data.get('synth_path'):
            audio_tracks['Synthesized'] = project_data['synth_path']
        if project_data.get('vocals_path'):
            audio_tracks['Vocals'] = project_data['vocals_path']
        
        if audio_tracks:
            self.audio_mixer.load_audio_tracks(audio_tracks)
    
    def _on_check_gpu(self):
        """Handle check GPU action"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                msg = f"GPU Detected: {gpu_name}\nVRAM: {vram:.1f} GB"
            else:
                msg = "No GPU detected. Running on CPU."
            QMessageBox.information(self, "GPU Status", msg)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to check GPU: {e}")
    
    def _on_docs(self):
        """Handle documentation action"""
        QMessageBox.information(self, "Documentation", "Documentation will open here")
    
    def _on_about(self):
        """Handle about action"""
        QMessageBox.about(
            self,
            "About Sheet Sage",
            "<h2>Sheet Sage V3</h2>"
            "<p>AI Music Transcription Suite for Windows</p>"
            "<p>Version 3.0.0</p>"
            "<p>Developed by Muhammad Faris Hakim</p>"
            "<p>Powered by TensorFlow, PyTorch, Gradio, Librosa, Omnizart, Basic Pitch</p>"
        )
    
    def closeEvent(self, event):
        """Handle app close - prompt to save unsaved projects and cleanup temp"""
        # Check if there's unsaved work
        if self.current_output_dir and not self.is_project_saved:
            reply = QMessageBox.question(
                self,
                "Unsaved Project",
                "You have unsaved work. Would you like to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                if self._save_project_as():
                    # Saved successfully, continue close
                    pass
                else:
                    # Save cancelled, don't close
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
            # Discard - continue to cleanup
        
        # Cleanup temp projects
        self._cleanup_temp_projects()
        
        event.accept()
    
    def _cleanup_temp_projects(self):
        """Delete all temp project directories"""
        # Unload audio to release file locks on Windows
        if hasattr(self, 'audio_mixer'):
            self.audio_mixer.clear_audio()
            
        import shutil
        
        # Clean tracked temp projects
        for temp_dir in self.temp_projects:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Failed to cleanup temp: {e}")
        
        # Also clean old temp projects (older than 1 day)
        if os.path.exists(self.temp_base):
            import time
            now = time.time()
            one_day = 24 * 60 * 60
            
            for folder in os.listdir(self.temp_base):
                folder_path = os.path.join(self.temp_base, folder)
                if os.path.isdir(folder_path):
                    try:
                        mtime = os.path.getmtime(folder_path)
                        if now - mtime > one_day:
                            shutil.rmtree(folder_path)
                    except:
                        pass
