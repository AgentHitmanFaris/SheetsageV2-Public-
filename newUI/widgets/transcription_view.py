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
        
        # Piano roll visualization
        from widgets.piano_roll_editor import PianoRollEditor
        self.piano_roll = PianoRollEditor()
        self.piano_roll.note_added.connect(self._on_note_added)
        self.piano_roll.note_removed.connect(self._on_note_removed)
        self.piano_roll.note_modified.connect(self._on_note_modified)
        results_layout.addWidget(self.piano_roll)
        
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
    
    def set_piano_roll_data(self, midi_path: str, audio_path: str = None):
        """Load and display MIDI file in piano roll"""
        try:
            self.piano_roll.load_midi(midi_path)
            if audio_path and os.path.exists(audio_path):
                self.piano_roll.load_spectrogram(audio_path)
            self.results_info.hide()
            self.log_success(f"Piano roll visualization updated")
        except Exception as e:
            self.log_error(f"Failed to visualize MIDI: {e}")
            self.results_info.setText(f"Failed to load MIDI visualization: {e}")
            self.results_info.setText(f"Failed to load MIDI visualization: {e}")
            self.results_info.show()
    
    def set_playback_time(self, seconds: float):
        """Update piano roll playback position"""
        if hasattr(self, 'piano_roll'):
            self.piano_roll.set_playback_position(seconds)
    
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

