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
    project_loaded = Signal(str) # New signal for loading projects
    transcribe_requested = Signal(dict)
    save_requested = Signal() # Signal when save button is clicked
    
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
        self.open_btn.setMinimumHeight(45)
        self.open_btn.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.open_btn.clicked.connect(self._on_open_clicked)
        open_file_layout.addWidget(self.open_btn)
        
        # Save button (hidden/disabled initially)
        self.save_btn = QPushButton("💾 Save Project")
        self.save_btn.setProperty("class", "success")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("font-size: 11pt; font-weight: bold;")
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setEnabled(False)
        self.save_btn.setVisible(False) # Hide until needed
        open_file_layout.addWidget(self.save_btn)
        
        layout.addWidget(open_file_group)

    def enable_save_button(self, enabled=True):
        """Enable/Disable and Show/Hide save button"""
        self.save_btn.setEnabled(enabled)
        self.save_btn.setVisible(enabled)
        
    def _on_save_clicked(self):
        """Emit save requested signal"""
        self.save_requested.emit()
        
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
            "Open File",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg);;SheetSage Project (*.sage);;All Files (*.*)"
        )
        
        if file_path:
            # Check for project file
            if file_path.lower().endswith('.sage'):
                self.project_loaded.emit(file_path)
                return
                
            # Emit file selected
            self.file_selected.emit(file_path)
            
            # Show transcription settings dialog
            from ui.widgets.transcription_settings_dialog import TranscriptionSettingsDialog
            
            dialog = TranscriptionSettingsDialog(file_path, self)
            dialog.transcription_confirmed.connect(self._on_transcription_confirmed)
            dialog.exec()
    
    def _on_transcription_confirmed(self, config):
        """Handle when user confirms transcription settings"""
        self.transcribe_requested.emit(config)
