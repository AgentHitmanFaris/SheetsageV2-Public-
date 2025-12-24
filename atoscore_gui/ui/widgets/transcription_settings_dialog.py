"""
Transcription Settings Dialog
Popup dialog for configuring transcription settings after file selection
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
import os


class TranscriptionSettingsDialog(QDialog):
    """Dialog for transcription settings after file selection"""
    
    transcription_confirmed = Signal(dict)  # Emits config when OK is clicked
    
    def __init__(self, audio_file_path, parent=None):
        super().__init__(parent)
        self.audio_file_path = audio_file_path
        self.setWindowTitle("Transcribe Audio File")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # File info
        file_info = QGroupBox("📁 Audio File")
        file_info_layout = QVBoxLayout(file_info)
        
        filename = os.path.basename(self.audio_file_path)
        file_label = QLabel(f"✓ {filename}")
        file_label.setStyleSheet("color: #2196f3; font-weight: bold; padding: 8px;")
        file_label.setWordWrap(True)
        file_info_layout.addWidget(file_label)
        
        layout.addWidget(file_info)
        
        # Transcription mode
        mode_group = QGroupBox("🎵 Transcription Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Basic Pitch (Standalone - No Harmony)",
            "Lead Sheet (Standard)",
            "Piano (Polyphonic)",
            "Drums (Omnizart)",
            "atoscore V3 (Lunaverus)"
        ])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        
        # Mode description
        self.mode_desc = QLabel("Melody + Chords + Key + Tempo")
        self.mode_desc.setWordWrap(True)
        self.mode_desc.setStyleSheet("color: #999; font-size: 9pt; font-style: italic; padding: 4px;")
        mode_layout.addWidget(self.mode_desc)
        
        layout.addWidget(mode_group)
        
        # Processing options
        options_group = QGroupBox("⚙️ Processing Options")
        options_layout = QVBoxLayout(options_group)
        
        self.separate_vocals_check = QCheckBox("Separate Vocals (Demucs)")
        self.separate_vocals_check.setChecked(False)
        self.separate_vocals_check.setToolTip("Use AI to separate vocals from instrumentals before transcription")
        options_layout.addWidget(self.separate_vocals_check)
        
        self.generate_pdf_check = QCheckBox("Generate Sheet Music PDF")
        self.generate_pdf_check.setChecked(True)
        self.generate_pdf_check.setToolTip("Generate printable PDF sheet music using LilyPond")
        options_layout.addWidget(self.generate_pdf_check)
        
        layout.addWidget(options_group)
        
        # Time options (section of song)
        time_group = QGroupBox("⏱️ Time Range")
        time_group.setCheckable(True)
        time_group.setChecked(False)
        time_layout = QVBoxLayout(time_group)
        
        # Full song / Section radio
        full_song_label = QLabel("○ Full song")
        full_song_label.setStyleSheet("color: #ccc;")
        time_layout.addWidget(full_song_label)
        
        section_label = QLabel("○ Section of song")
        section_label.setStyleSheet("color: #ccc;")
        time_layout.addWidget(section_label)
        
        # Start/End time
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("From:"))
        self.start_time_spin = QDoubleSpinBox()
        self.start_time_spin.setRange(0, 36000)
        self.start_time_spin.setValue(0)
        self.start_time_spin.setSuffix(" s")
        time_row.addWidget(self.start_time_spin)
        
        time_row.addWidget(QLabel("To:"))
        self.end_time_spin = QDoubleSpinBox()
        self.end_time_spin.setRange(0, 36000)
        self.end_time_spin.setValue(0)
        self.end_time_spin.setSuffix(" s")
        time_row.addWidget(self.end_time_spin)
        
        time_layout.addLayout(time_row)
        
        layout.addWidget(time_group)
        
        # Display settings (visual only)
        display_group = QGroupBox("🎨 Display Settings (visual only)")
        display_layout = QVBoxLayout(display_group)
        
        self.find_notes_check = QCheckBox("Find notes")
        self.find_notes_check.setChecked(True)
        display_layout.addWidget(self.find_notes_check)
        
        self.spectrogram_only_check = QCheckBox("Spectrogram only")
        self.spectrogram_only_check.setChecked(False)
        display_layout.addWidget(self.spectrogram_only_check)
        
        # Resolution settings
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Frequency Resolution:"))
        self.freq_res_spin = QSpinBox()
        self.freq_res_spin.setRange(1, 16)
        self.freq_res_spin.setValue(4)
        self.freq_res_spin.setSuffix(" bands/note")
        res_layout.addWidget(self.freq_res_spin)
        display_layout.addLayout(res_layout)
        
        time_step_layout = QHBoxLayout()
        time_step_layout.addWidget(QLabel("Time Step:"))
        self.time_step_spin = QSpinBox()
        self.time_step_spin.setRange(1, 100)
        self.time_step_spin.setValue(10)
        self.time_step_spin.setSuffix(" ms")
        time_step_layout.addWidget(self.time_step_spin)
        display_layout.addLayout(time_step_layout)
        
        layout.addWidget(display_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_ok_clicked)
        button_box.rejected.connect(self.reject)
        
        # Style OK button
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText("✓ Start Transcription")
        ok_button.setProperty("class", "primary")
        ok_button.setMinimumHeight(40)
        
        layout.addWidget(button_box)
    
    def _on_mode_changed(self, mode_text):
        """Handle mode selection change"""
        descriptions = {
            "Basic Pitch (Standalone - No Harmony)": "Pure Basic Pitch MIDI (No beat/chord analysis)",
            "Lead Sheet (Standard)": "Melody + Chords + Key + Tempo",
            "Piano (Polyphonic)": "Polyphonic piano transcription",
            "Drums (Omnizart)": "Drum kit transcription",
            "atoscore V3 (Lunaverus)": "CNN trained on MAESTRO"
        }
        self.mode_desc.setText(descriptions.get(mode_text, ""))
    
    def _on_ok_clicked(self):
        """Handle OK button - gather config and emit signal"""
        config = {
            'audio_file': self.audio_file_path,
            'mode': self.mode_combo.currentText(),
            'separate_vocals': self.separate_vocals_check.isChecked(),
            'generate_pdf': self.generate_pdf_check.isChecked(),
            'start_time': self.start_time_spin.value() if self.start_time_spin.value() > 0 else None,
            'end_time': self.end_time_spin.value() if self.end_time_spin.value() > 0 else None,
        }
        
        self.transcription_confirmed.emit(config)
        self.accept()

