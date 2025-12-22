"""
File Input Panel Widget - Simplified for Dialog-Based Workflow
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QGroupBox, QLabel, QFileDialog
)
from PySide6.QtCore import Qt, Signal
import os


class FileInputPanel(QWidget):
    """Simplified panel with just an Open button"""
    
    # Signals
    file_selected = Signal(str)
    transcribe_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # === OPEN FILE BUTTON ===
        open_file_group = QGroupBox("📁 File")
        open_file_layout = QVBoxLayout(open_file_group)
        
        # Open button
        self.open_btn = QPushButton("📂 Open...")
        self.open_btn.setProperty("class", "primary")
        self.open_btn.setMinimumHeight(50)
        self.open_btn.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.open_btn.clicked.connect(self._on_open_clicked)
        open_file_layout.addWidget(self.open_btn)
        
        layout.addWidget(open_file_group)
        
        # === RECENT FILES ===
        recent_group = QGroupBox("📋 Recent")
        recent_layout = QVBoxLayout(recent_group)
        
        recent_label = QLabel("No recent files")
        recent_label.setStyleSheet("color: #666; font-size: 9pt; padding: 8px;")
        recent_label.setAlignment(Qt.AlignCenter)
        recent_layout.addWidget(recent_label)
        
        layout.addWidget(recent_group)
        
        # Push everything to top
        layout.addStretch()
    
    def _on_open_clicked(self):
        """Handle Open button - show file picker then settings dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg);;All Files (*.*)"
        )
        
        if file_path:
            # Emit file selected
            self.file_selected.emit(file_path)
            
            # Show transcription settings dialog
            from widgets.transcription_settings_dialog import TranscriptionSettingsDialog
            
            dialog = TranscriptionSettingsDialog(file_path, self)
            dialog.transcription_confirmed.connect(self._on_transcription_confirmed)
            dialog.exec()
    
    def _on_transcription_confirmed(self, config):
        """Handle when user confirms transcription settings"""
        self.transcribe_requested.emit(config)
