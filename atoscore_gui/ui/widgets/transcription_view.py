"""
Transcription View Widget
Center panel with tabs for logs, results, and output files
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QListWidget, QListWidgetItem, QPushButton,
    QLabel, QSplitter, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat
import os


class TranscriptionView(QWidget):
    """Center panel for displaying transcription logs, results, and files"""
    
    # Signals
    file_download_requested = Signal(str)  # Emits file path to download
    midi_saved = Signal(str)  # Emits path to saved MIDI file
    live_notes_changed = Signal(list, bool) # notes, is_drum
    note_preview_request = Signal(int, bool) # pitch, is_drum
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._output_files = []
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        
        # === LOG TAB ===
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        log_layout.setContentsMargins(8, 8, 8, 8)
        
        # Log console (colored text)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        log_layout.addWidget(self.log_console)
        
        # Clear log button
        clear_btn = QPushButton("🗑️ Clear Log")
        clear_btn.setProperty("class", "secondary")
        clear_btn.clicked.connect(self.log_console.clear)
        log_layout.addWidget(clear_btn)
        
        self.tabs.addTab(self.log_tab, "📋 Transcription Log")
        
        # === RESULTS TAB ===
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        # View Controls
        view_controls = QHBoxLayout()
        
        # Metadata Labels
        self.bpm_label = QLabel("Tempo: --")
        self.key_label = QLabel("Key: --")
        self.time_sig_label = QLabel("Time: --")
        
        # Style labels
        label_style = """
            QLabel {
                background-color: #2a2a2a;
                color: #e0e0e0;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid #3d3d3d;
            }
        """
        for lbl in [self.bpm_label, self.key_label, self.time_sig_label]:
            lbl.setStyleSheet(label_style)
            view_controls.addWidget(lbl)
        
        view_controls.addStretch()
        self.toggle_view_btn = QPushButton("🥁 Switch to Drum View")
        self.toggle_view_btn.setCheckable(True)
        self.toggle_view_btn.clicked.connect(self._on_toggle_view)
        view_controls.addWidget(self.toggle_view_btn)
        results_layout.addLayout(view_controls)
        
        # Piano roll visualization
        # Piano roll visualization
        from ui.widgets.piano_roll_editor import PianoRollEditor
        self.piano_roll = PianoRollEditor()
        self.piano_roll.note_added.connect(self._on_note_added)
        self.piano_roll.note_removed.connect(self._on_note_removed)
        self.piano_roll.note_modified.connect(self._on_note_modified)
        self.piano_roll.midi_saved.connect(self.midi_saved)
        # Live MIDI connections
        self.piano_roll.note_preview.connect(lambda p: self.note_preview_request.emit(p, False))
        self.piano_roll.note_added.connect(lambda *a: self._update_live_notes(False))
        self.piano_roll.note_removed.connect(lambda *a: self._update_live_notes(False))
        self.piano_roll.note_modified.connect(lambda *a: self._update_live_notes(False))
        
        results_layout.addWidget(self.piano_roll)
        
        # Drum roll visualization (hidden by default)
        from ui.widgets.drum_roll_editor import DrumRollEditor
        self.drum_roll = DrumRollEditor()
        self.drum_roll.setVisible(False)
        self.drum_roll.note_added.connect(self._on_note_added)
        self.drum_roll.note_removed.connect(self._on_note_removed)
        self.drum_roll.note_modified.connect(self._on_note_modified)
        self.drum_roll.midi_saved.connect(self.midi_saved)
        # Live MIDI connections
        self.drum_roll.note_preview.connect(lambda p: self.note_preview_request.emit(p, True))
        self.drum_roll.note_added.connect(lambda *a: self._update_live_notes(True))
        self.drum_roll.note_removed.connect(lambda *a: self._update_live_notes(True))
        self.drum_roll.note_modified.connect(lambda *a: self._update_live_notes(True))
        
        results_layout.addWidget(self.drum_roll)
        
        # Info label
        self.results_info = QLabel("No transcription results yet. Start a transcription to see the piano roll visualization.")
        self.results_info.setAlignment(Qt.AlignCenter)
        self.results_info.setStyleSheet("color: #999; padding: 20px;")
        self.results_info.setWordWrap(True)
        results_layout.addWidget(self.results_info)
        
        self.tabs.addTab(self.results_tab, "📊 Results")
        
        # === FILES TAB ===
        self.files_tab = QWidget()
        files_layout = QVBoxLayout(self.files_tab)
        files_layout.setContentsMargins(8, 8, 8, 8)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3b3b3b;
            }
            QListWidget::item:hover {
                background-color: #3b3b3b;
            }
        """)
        files_layout.addWidget(self.file_list)
        
        # File actions
        file_actions = QHBoxLayout()
        
        open_folder_btn = QPushButton("📂 Open Output Folder")
        open_folder_btn.clicked.connect(self._on_open_output_folder)
        file_actions.addWidget(open_folder_btn)
        
        download_selected_btn = QPushButton("💾 Download Selected")
        download_selected_btn.clicked.connect(self._on_download_selected)
        file_actions.addWidget(download_selected_btn)
        
        files_layout.addLayout(file_actions)
        
        self.tabs.addTab(self.files_tab, "📁 Output Files")
        
        layout.addWidget(self.tabs)
        
        # Initial welcome message
        self.log_info("Welcome to Sheet Sage Native UI!")
        self.log_info("Select an audio file and click Transcribe to begin.")
    
    def log_info(self, message: str):
        """Add info message to log (white text)"""
        self._append_log(message, QColor(255, 255, 255))
    
    def log_success(self, message: str):
        """Add success message to log (green text)"""
        self._append_log(f"✓ {message}", QColor(0, 255, 100))
    
    def log_warning(self, message: str):
        """Add warning message to log (yellow text)"""
        self._append_log(f"⚠ {message}", QColor(255, 200, 0))
    
    def log_error(self, message: str):
        """Add error message to log (red text)"""
        self._append_log(f"✗ {message}", QColor(255, 100, 100))
    
    def log_progress(self, message: str):
        """Add progress message to log (purple text)"""
        self._append_log(f"⟳ {message}", QColor(124, 58, 237))
    
    def _append_log(self, message: str, color: QColor):
        """Append colored message to log console"""
        cursor = self.log_console.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Set text format
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        
        cursor.insertText(f"{message}\n", fmt)
        
        # Auto-scroll to bottom
        self.log_console.setTextCursor(cursor)
        self.log_console.ensureCursorVisible()
    
    def set_piano_roll_data(self, midi_path: str, audio_path: str = None, is_drum: bool = False):
        """Load and display MIDI file in piano roll or drum roll"""
        try:
            # Auto-detect drums from filename if not specified
            if not is_drum and "drums" in os.path.basename(midi_path).lower():
                is_drum = True
                
            if is_drum:
                self.piano_roll.setVisible(False)
                self.drum_roll.setVisible(True)
                self.drum_roll.load_midi(midi_path)
                self.toggle_view_btn.setChecked(True)
                self.toggle_view_btn.setText("🎹 Switch to Piano Roll")
                # Drum editor doesn't support spectrogram yet
                self.log_success(f"Drum Editor loaded for percussion track")
                self._update_live_notes(True)
            else:
                self.drum_roll.setVisible(False)
                self.piano_roll.setVisible(True)
                self.piano_roll.load_midi(midi_path)
                self.toggle_view_btn.setChecked(False)
                self.toggle_view_btn.setText("🥁 Switch to Drum View")
                if audio_path and os.path.exists(audio_path):
                    self.piano_roll.load_spectrogram(audio_path)
                self.log_success(f"Piano Role visualization updated")
                self._update_live_notes(False)
                
            self.results_info.hide()
        except Exception as e:
            self.log_error(f"Failed to visualize MIDI: {e}")
            self.results_info.setText(f"Failed to load visualization: {e}")
            self.results_info.show()
            
    def set_playback_time(self, seconds: float):
        """Update playback position"""
        if self.piano_roll.isVisible():
            self.piano_roll.set_playback_position(seconds)
        if self.drum_roll.isVisible():
            self.drum_roll.set_playback_position(seconds)

    def _update_live_notes(self, is_drum):
        """Send current notes to mixer for live playback"""
        editor = self.drum_roll if is_drum else self.piano_roll
        if hasattr(editor, 'notes'):
            self.live_notes_changed.emit(editor.notes, is_drum)
            
    def _on_toggle_view(self, checked):
        """Toggle between Piano Roll and Drum View"""
        is_drum = checked
        if is_drum:
            self.piano_roll.setVisible(False)
            self.drum_roll.setVisible(True)
            self.toggle_view_btn.setText("🎹 Switch to Piano Roll")
            # Sync data if possible (though format differs)
            if self.piano_roll.current_midi_path:
                 self.drum_roll.load_midi(self.piano_roll.current_midi_path)
            self._update_live_notes(True)
        else:
            self.drum_roll.setVisible(False)
            self.piano_roll.setVisible(True)
            self.toggle_view_btn.setText("🥁 Switch to Drum View")
            if hasattr(self.drum_roll, 'current_midi_path') and self.drum_roll.current_midi_path:
                 self.piano_roll.load_midi(self.drum_roll.current_midi_path)
            self._update_live_notes(False)
            
    def _update_live_notes(self, is_drum):
        """Send current notes to mixer for live playback"""
        editor = self.drum_roll if is_drum else self.piano_roll
        if hasattr(editor, 'notes'):
            self.live_notes_changed.emit(editor.notes, is_drum)
    
    def set_song_metadata(self, bpm=None, key=None, time_sig=None):
        """Update song metadata display"""
        if bpm:
            self.bpm_label.setText(f"Tempo: {bpm}")
            self.bpm_label.setStyleSheet(self.bpm_label.styleSheet().replace("#2a2a2a", "#2a2a2a")) # Ensure visible
            self.bpm_label.show()
        else:
            self.bpm_label.hide()
            
        if key:
            self.key_label.setText(f"Key: {key}")
            self.key_label.show()
        else:
            self.key_label.hide()
            
        if time_sig:
            self.time_sig_label.setText(f"Time: {time_sig}")
            self.time_sig_label.show()
        else:
            self.time_sig_label.hide()
            
    def _on_note_added(self, pitch, start, duration):
        """Handle manual note addition"""
        self.log_info(f"Note added: Pitch {pitch}, Start {start:.2f}s, Duration {duration:.2f}s")
    
    def _on_note_removed(self, pitch, start):
        """Handle note removal"""
        self.log_info(f"Note removed: Pitch {pitch}, Start {start:.2f}s")
    
    def _on_note_modified(self, pitch, old_start, new_start, duration):
        """Handle note modification"""
        self.log_info(f"Note moved: Pitch {pitch}, {old_start:.2f}s → {new_start:.2f}s")
    
    def add_output_file(self, file_path: str):
        """Add file to output files list"""
        if not os.path.exists(file_path):
            return
        
        self._output_files.append(file_path)
        
        # Create list item
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        size_str = self._format_file_size(file_size)
        
        # Determine icon based on extension
        ext = os.path.splitext(filename)[1].lower()
        icon_map = {
            '.midi': '🎹', '.mid': '🎹',
            '.pdf': '📄',
            '.wav': '🔊', '.mp3': '🔊',
            '.ly': '📝'
        }
        icon = icon_map.get(ext, '📄')
        
        item_text = f"{icon}  {filename}  ({size_str})"
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, file_path)  # Store full path in item data
        self.file_list.addItem(item)
        
        self.log_info(f"Added output file: {filename}")
    
    def clear_output_files(self):
        """Clear the output files list"""
        self._output_files.clear()
        self.file_list.clear()
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _on_open_output_folder(self):
        """Open the output folder in file explorer"""
        if not self._output_files:
            QMessageBox.information(self, "No Files", "No output files to show yet.")
            return
        
        # Get folder of first file
        folder = os.path.dirname(self._output_files[0])
        os.startfile(folder)  # Windows-specific
    
    def _on_download_selected(self):
        """Download/copy selected file"""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a file to download.")
            return
        
        file_path = current_item.data(Qt.UserRole)
        
        # Ask where to save
        default_filename = os.path.basename(file_path)
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            default_filename,
            "All Files (*.*)"
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy2(file_path, save_path)
                self.log_success(f"Downloaded: {os.path.basename(save_path)}")
                QMessageBox.information(self, "Success", f"File saved to:\n{save_path}")
            except Exception as e:
                self.log_error(f"Download failed: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

