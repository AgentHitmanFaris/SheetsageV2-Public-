"""
Settings Dialog
Configuration dialog for application settings
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QGroupBox, QCheckBox,
    QComboBox, QSpinBox, QTabWidget, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import os
import json


class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    settings_saved = Signal(dict)  # Emits settings dict when saved
    
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Sheet Sage")
        self.setMinimumSize(600, 500)
        self.current_settings = current_settings or self._default_settings()
        self._setup_ui()
        self._load_current_settings()
    
    def _default_settings(self):
        """Get default settings"""
        return {
            'output_dir': os.path.join(os.getcwd(), 'output'),
            'soundfont_path': os.path.join(os.getcwd(), '..', 'atoscore_Core', 'soundfont', 'MS Basic.sf3'),
            'gpu_enabled': True,
            'default_mode': 'Lead Sheet (Standard)',
            'separate_vocals_default': True,
            'generate_pdf_default': True,
            # Compression settings
            'compress_output': True,
            'compression_format': 'mp3',  # 'wav', 'flac', 'mp3', 'ogg'
            'compression_quality': 'high',  # 'high', 'medium', 'low'
            'auto_bundle': True,  # Create .sage bundle automatically
            # Notation software
            'notation_software': '',  # Path to notation software exe
            'notation_name': 'MuseScore'  # Name of the notation software
        }
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # === GENERAL TAB ===
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setSpacing(16)
        
        # Output Directory
        output_group = QGroupBox("Output Directory")
        output_layout = QVBoxLayout(output_group)
        
        output_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        output_row.addWidget(self.output_dir_edit)
        
        browse_output_btn = QPushButton("Browse...")
        browse_output_btn.clicked.connect(self._browse_output_dir)
        output_row.addWidget(browse_output_btn)
        
        output_layout.addLayout(output_row)
        general_layout.addWidget(output_group)
        
        # Default Mode
        mode_group = QGroupBox("Default Transcription Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.default_mode_combo = QComboBox()
        self.default_mode_combo.addItems([
            "Lead Sheet (Standard)",
            "Piano (Polyphonic)",
            "Basic Pitch (Polyphonic)",
            "Drums (Omnizart)",
            "atoscore V3 (Lunaverus)"
        ])
        mode_layout.addWidget(self.default_mode_combo)
        
        general_layout.addWidget(mode_group)
        
        # Default Options
        defaults_group = QGroupBox("Default Options")
        defaults_layout = QVBoxLayout(defaults_group)
        
        self.separate_vocals_check = QCheckBox("Separate Vocals by default")
        defaults_layout.addWidget(self.separate_vocals_check)
        
        self.generate_pdf_check = QCheckBox("Generate PDF by default")
        defaults_layout.addWidget(self.generate_pdf_check)
        
        general_layout.addWidget(defaults_group)
        
        general_layout.addStretch()
        tabs.addTab(general_tab, "General")
        
        # === AUDIO TAB ===
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        audio_layout.setSpacing(16)
        
        # Soundfont Path
        soundfont_group = QGroupBox("Soundfont for MIDI Synthesis")
        soundfont_layout = QVBoxLayout(soundfont_group)
        
        soundfont_row = QHBoxLayout()
        self.soundfont_edit = QLineEdit()
        soundfont_row.addWidget(self.soundfont_edit)
        
        browse_soundfont_btn = QPushButton("Browse...")
        browse_soundfont_btn.clicked.connect(self._browse_soundfont)
        soundfont_row.addWidget(browse_soundfont_btn)
        
        soundfont_layout.addLayout(soundfont_row)
        
        soundfont_info = QLabel("Select a .sf2 or .sf3 SoundFont file for audio synthesis")
        soundfont_info.setStyleSheet("color: #999; font-size: 9pt;")
        soundfont_layout.addWidget(soundfont_info)
        
        audio_layout.addWidget(soundfont_group)
        
        # Output Compression (NEW)
        compression_group = QGroupBox("📦 Output Compression (Save Storage)")
        compression_layout = QVBoxLayout(compression_group)
        
        self.compress_check = QCheckBox("Enable output compression")
        self.compress_check.setToolTip("Compress audio files to save storage (70-85% smaller)")
        compression_layout.addWidget(self.compress_check)
        
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Audio Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "WAV (Uncompressed - 100%)",
            "FLAC (Lossless - 50%)",
            "MP3 (High Quality - 15%)",
            "OGG (High Quality - 15%)"
        ])
        self.format_combo.setCurrentIndex(2)  # Default to MP3
        format_row.addWidget(self.format_combo, 1)
        compression_layout.addLayout(format_row)
        
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["High (320kbps)", "Medium (192kbps)", "Low (128kbps)"])
        quality_row.addWidget(self.quality_combo, 1)
        compression_layout.addLayout(quality_row)
        
        self.auto_bundle_check = QCheckBox("Auto-create .sage project bundle")
        self.auto_bundle_check.setToolTip("Bundle all output files into a single .sage file")
        compression_layout.addWidget(self.auto_bundle_check)
        
        compression_info = QLabel(
            "💡 Compression reduces storage from ~91 MB to ~15 MB per transcription.\n"
            "MP3 is recommended for best space savings with excellent quality."
        )
        compression_info.setStyleSheet("color: #999; font-size: 9pt;")
        compression_info.setWordWrap(True)
        compression_layout.addWidget(compression_info)
        
        audio_layout.addWidget(compression_group)
        
        audio_layout.addStretch()
        tabs.addTab(audio_tab, "Audio")
        
        # === ADVANCED TAB ===
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setSpacing(16)
        
        # GPU Settings
        gpu_group = QGroupBox("Hardware Acceleration")
        gpu_layout = QVBoxLayout(gpu_group)
        
        self.gpu_check = QCheckBox("Enable GPU acceleration (CUDA)")
        self.gpu_check.setToolTip("Use NVIDIA GPU for faster transcription (requires compatible GPU)")
        gpu_layout.addWidget(self.gpu_check)
        
        gpu_info = QLabel("Requires NVIDIA GPU with CUDA support. Restart app after changing.")
        gpu_info.setStyleSheet("color: #999; font-size: 9pt;")
        gpu_info.setWordWrap(True)
        gpu_layout.addWidget(gpu_info)
        
        advanced_layout.addWidget(gpu_group)
        
        # Notation Software Integration
        notation_group = QGroupBox("🎼 Notation Software Integration")
        notation_layout = QVBoxLayout(notation_group)
        
        notation_info = QLabel(
            "Configure your notation software to open transcriptions directly.\n"
            "Supports: MuseScore, Finale, Sibelius, Dorico, Notion"
        )
        notation_info.setStyleSheet("color: #999; font-size: 9pt;")
        notation_info.setWordWrap(True)
        notation_layout.addWidget(notation_info)
        
        software_row = QHBoxLayout()
        software_row.addWidget(QLabel("Software:"))
        self.notation_name_combo = QComboBox()
        self.notation_name_combo.addItems([
            "MuseScore",
            "Finale",
            "Sibelius",
            "Dorico",
            "Notion",
            "Other"
        ])
        software_row.addWidget(self.notation_name_combo, 1)
        notation_layout.addLayout(software_row)
        
        path_row = QHBoxLayout()
        self.notation_path_edit = QLineEdit()
        self.notation_path_edit.setPlaceholderText("Path to notation software executable...")
        path_row.addWidget(self.notation_path_edit, 1)
        
        browse_notation_btn = QPushButton("📂 Browse...")
        browse_notation_btn.clicked.connect(self._browse_notation_software)
        path_row.addWidget(browse_notation_btn)
        
        detect_btn = QPushButton("🔍 Auto-Detect")
        detect_btn.clicked.connect(self._auto_detect_notation)
        path_row.addWidget(detect_btn)
        
        notation_layout.addLayout(path_row)
        
        advanced_layout.addWidget(notation_group)
        
        advanced_layout.addStretch()
        tabs.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(tabs)
        
        # === BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _load_current_settings(self):
        """Load current settings into UI"""
        self.output_dir_edit.setText(self.current_settings.get('output_dir', ''))
        self.soundfont_edit.setText(self.current_settings.get('soundfont_path', ''))
        self.gpu_check.setChecked(self.current_settings.get('gpu_enabled', True))
        
        default_mode = self.current_settings.get('default_mode', 'Lead Sheet (Standard)')
        index = self.default_mode_combo.findText(default_mode)
        if index >= 0:
            self.default_mode_combo.setCurrentIndex(index)
        
        self.separate_vocals_check.setChecked(self.current_settings.get('separate_vocals_default', True))
        self.generate_pdf_check.setChecked(self.current_settings.get('generate_pdf_default', True))
        
        # Compression settings
        self.compress_check.setChecked(self.current_settings.get('compress_output', True))
        self.auto_bundle_check.setChecked(self.current_settings.get('auto_bundle', True))
        
        format_val = self.current_settings.get('compression_format', 'mp3')
        format_index = {'wav': 0, 'flac': 1, 'mp3': 2, 'ogg': 3}.get(format_val, 2)
        self.format_combo.setCurrentIndex(format_index)
        
        quality_val = self.current_settings.get('compression_quality', 'high')
        quality_index = {'high': 0, 'medium': 1, 'low': 2}.get(quality_val, 0)
        self.quality_combo.setCurrentIndex(quality_index)
        
        # Notation software
        self.notation_path_edit.setText(self.current_settings.get('notation_software', ''))
        notation_name = self.current_settings.get('notation_name', 'MuseScore')
        notation_index = self.notation_name_combo.findText(notation_name)
        if notation_index >= 0:
            self.notation_name_combo.setCurrentIndex(notation_index)
    
    def _browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_dir_edit.text() or os.getcwd()
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def _browse_soundfont(self):
        """Browse for soundfont file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SoundFont File",
            self.soundfont_edit.text() or os.getcwd(),
            "SoundFont Files (*.sf2 *.sf3);;All Files (*.*)"
        )
        if file_path:
            self.soundfont_edit.setText(file_path)
    
    def _browse_notation_software(self):
        """Browse for notation software executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Notation Software Executable",
            os.environ.get('ProgramFiles', 'C:\\Program Files'),
            "Executable Files (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.notation_path_edit.setText(file_path)
            # Try to detect which software it is
            basename = os.path.basename(file_path).lower()
            if 'musescore' in basename:
                self.notation_name_combo.setCurrentText('MuseScore')
            elif 'finale' in basename:
                self.notation_name_combo.setCurrentText('Finale')
            elif 'sibelius' in basename:
                self.notation_name_combo.setCurrentText('Sibelius')
            elif 'dorico' in basename:
                self.notation_name_combo.setCurrentText('Dorico')
            elif 'notion' in basename:
                self.notation_name_combo.setCurrentText('Notion')
    
    def _auto_detect_notation(self):
        """Auto-detect installed notation software"""
        # Common installation paths
        search_paths = [
            # MuseScore
            (r'C:\Program Files\MuseScore 4\bin\MuseScore4.exe', 'MuseScore'),
            (r'C:\Program Files\MuseScore 3\bin\MuseScore3.exe', 'MuseScore'),
            (r'C:\Program Files (x86)\MuseScore 3\bin\MuseScore3.exe', 'MuseScore'),
            # Finale
            (r'C:\Program Files\MakeMusic\Finale\Finale.exe', 'Finale'),
            # Sibelius
            (r'C:\Program Files\Avid\Sibelius\Sibelius.exe', 'Sibelius'),
            # Dorico
            (r'C:\Program Files\Steinberg\Dorico5\Dorico5.exe', 'Dorico'),
            (r'C:\Program Files\Steinberg\Dorico4\Dorico4.exe', 'Dorico'),
            # Notion
            (r'C:\Program Files\PreSonus\Notion\Notion.exe', 'Notion'),
        ]
        
        found = []
        for path, name in search_paths:
            if os.path.exists(path):
                found.append((path, name))
        
        if found:
            # Use the first one found
            path, name = found[0]
            self.notation_path_edit.setText(path)
            self.notation_name_combo.setCurrentText(name)
            QMessageBox.information(
                self,
                "Software Detected",
                f"✅ Found: {name}\n\nPath: {path}"
            )
        else:
            QMessageBox.information(
                self,
                "Not Found",
                "Could not auto-detect notation software.\n\n"
                "Please browse to the executable manually."
            )
    
    def _save_settings(self):
        """Save settings and close dialog"""
        # Validate
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Invalid Settings", "Please specify an output directory.")
            return
        
        soundfont_path = self.soundfont_edit.text().strip()
        if soundfont_path and not os.path.exists(soundfont_path):
            reply = QMessageBox.question(
                self,
                "SoundFont Not Found",
                f"The soundfont file does not exist:\n{soundfont_path}\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Collect settings
        settings = {
            'output_dir': output_dir,
            'soundfont_path': soundfont_path,
            'gpu_enabled': self.gpu_check.isChecked(),
            'default_mode': self.default_mode_combo.currentText(),
            'separate_vocals_default': self.separate_vocals_check.isChecked(),
            'generate_pdf_default': self.generate_pdf_check.isChecked(),
            # Compression settings
            'compress_output': self.compress_check.isChecked(),
            'compression_format': ['wav', 'flac', 'mp3', 'ogg'][self.format_combo.currentIndex()],
            'compression_quality': ['high', 'medium', 'low'][self.quality_combo.currentIndex()],
            'auto_bundle': self.auto_bundle_check.isChecked(),
            # Notation software
            'notation_software': self.notation_path_edit.text().strip(),
            'notation_name': self.notation_name_combo.currentText()
        }
        
        # Emit signal
        self.settings_saved.emit(settings)
        
        # Save to file
        self._save_to_file(settings)
        
        QMessageBox.information(self, "Success", "Settings saved successfully!")
        self.accept()
    
    def _save_to_file(self, settings):
        """Save settings to JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Failed to save settings file:\n{e}")
    
    @staticmethod
    def load_settings_from_file():
        """Load settings from JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return SettingsDialog(None)._default_settings()

