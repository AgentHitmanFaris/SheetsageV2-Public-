"""
Batch Processing Dialog
Queue multiple audio files for transcription
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QGroupBox, QComboBox, QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor, QBrush
import os


class BatchProcessingDialog(QDialog):
    """Dialog for batch transcription of multiple files"""
    
    batch_started = Signal(list, dict)  # files, settings
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📁 Batch Transcription")
        self.setMinimumSize(600, 500)
        self.files = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # === FILE LIST SECTION ===
        files_group = QGroupBox("Audio Files")
        files_layout = QVBoxLayout(files_group)
        
        # Buttons row
        btn_row = QHBoxLayout()
        
        add_files_btn = QPushButton("📄 Add Files...")
        add_files_btn.clicked.connect(self._on_add_files)
        btn_row.addWidget(add_files_btn)
        
        add_folder_btn = QPushButton("📁 Add Folder...")
        add_folder_btn.clicked.connect(self._on_add_folder)
        btn_row.addWidget(add_folder_btn)
        
        remove_btn = QPushButton("🗑️ Remove Selected")
        remove_btn.clicked.connect(self._on_remove_selected)
        btn_row.addWidget(remove_btn)
        
        clear_btn = QPushButton("❌ Clear All")
        clear_btn.clicked.connect(self._on_clear_all)
        btn_row.addWidget(clear_btn)
        
        files_layout.addLayout(btn_row)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.setMinimumHeight(150)
        files_layout.addWidget(self.file_list)
        
        # File count label
        self.count_label = QLabel("0 files in queue")
        self.count_label.setStyleSheet("color: #666; font-size: 9pt;")
        files_layout.addWidget(self.count_label)
        
        layout.addWidget(files_group)
        
        # === SETTINGS SECTION ===
        settings_group = QGroupBox("Transcription Settings (Applied to All Files)")
        settings_layout = QVBoxLayout(settings_group)
        
        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Lead Sheet (Standard)",
            "Piano (ByteDance)",
            "Basic Pitch (Spotify)",
            "Drums (Omnizart)",
            "SheetSage V3 (Lunaverus)"
        ])
        mode_row.addWidget(self.mode_combo, 1)
        settings_layout.addLayout(mode_row)
        
        # Options row
        options_row = QHBoxLayout()
        self.vocals_checkbox = QCheckBox("Separate Vocals (Demucs)")
        options_row.addWidget(self.vocals_checkbox)
        
        self.pdf_checkbox = QCheckBox("Generate PDF")
        options_row.addWidget(self.pdf_checkbox)
        
        self.synth_checkbox = QCheckBox("Synthesize Audio")
        self.synth_checkbox.setChecked(True)
        options_row.addWidget(self.synth_checkbox)
        
        options_row.addStretch()
        settings_layout.addLayout(options_row)
        
        layout.addWidget(settings_group)
        
        # === PROGRESS SECTION ===
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Current file label
        self.current_file_label = QLabel("Ready to start")
        self.current_file_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(self.current_file_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt;")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # === ACTION BUTTONS ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QPushButton("▶️ Start Batch")
        self.start_btn.setProperty("class", "primary")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setMinimumWidth(120)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause)
        btn_layout.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # Worker reference
        self.worker = None
        self.is_paused = False
    
    def _on_add_files(self):
        """Add audio files to queue"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg);;All Files (*.*)"
        )
        
        for file_path in files:
            if file_path not in self.files:
                self.files.append(file_path)
                item = QListWidgetItem(f"⏸️ {os.path.basename(file_path)}")
                item.setData(Qt.UserRole, file_path)
                self.file_list.addItem(item)
        
        self._update_count()
    
    def _on_add_folder(self):
        """Add all audio files from a folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder"
        )
        
        if folder:
            audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}
            for filename in os.listdir(folder):
                ext = os.path.splitext(filename)[1].lower()
                if ext in audio_extensions:
                    file_path = os.path.join(folder, filename)
                    if file_path not in self.files:
                        self.files.append(file_path)
                        item = QListWidgetItem(f"⏸️ {filename}")
                        item.setData(Qt.UserRole, file_path)
                        self.file_list.addItem(item)
            
            self._update_count()
    
    def _on_remove_selected(self):
        """Remove selected files from queue"""
        for item in self.file_list.selectedItems():
            file_path = item.data(Qt.UserRole)
            if file_path in self.files:
                self.files.remove(file_path)
            self.file_list.takeItem(self.file_list.row(item))
        
        self._update_count()
    
    def _on_clear_all(self):
        """Clear all files from queue"""
        self.files.clear()
        self.file_list.clear()
        self._update_count()
    
    def _update_count(self):
        """Update file count label"""
        count = len(self.files)
        self.count_label.setText(f"{count} file{'s' if count != 1 else ''} in queue")
        self.start_btn.setEnabled(count > 0)
    
    def _get_mode_string(self):
        """Get mode string from combo selection"""
        text = self.mode_combo.currentText()
        if "Lead Sheet" in text:
            return "lead_sheet"
        elif "Piano" in text:
            return "piano"
        elif "Basic Pitch" in text:
            return "basic_pitch"    
        elif "Drums" in text:
            return "drums"
        elif "Lunaverus" in text:
            return "lunaverus"
        return "lead_sheet"
    
    def _on_start(self):
        """Start batch processing"""
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please add files to the queue first.")
            return
        
        # Get settings
        settings = {
            'mode': self._get_mode_string(),
            'separate_vocals': self.vocals_checkbox.isChecked(),
            'generate_pdf': self.pdf_checkbox.isChecked(),
            'synthesize': self.synth_checkbox.isChecked()
        }
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        self.current_file_label.setText("Starting batch processing...")
        self.progress_bar.setValue(0)
        
        # Create and start worker
        from workers.batch_worker import BatchWorker
        self.worker = BatchWorker(self.files.copy(), settings)
        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_progress.connect(self._on_file_progress)
        self.worker.file_completed.connect(self._on_file_completed)
        self.worker.file_error.connect(self._on_file_error)
        self.worker.batch_completed.connect(self._on_batch_completed)
        self.worker.start()
    
    def _on_pause(self):
        """Pause/resume batch processing"""
        if self.worker:
            if self.is_paused:
                self.worker.resume()
                self.pause_btn.setText("⏸️ Pause")
                self.is_paused = False
            else:
                self.worker.pause()
                self.pause_btn.setText("▶️ Resume")
                self.is_paused = True
    
    def _on_cancel(self):
        """Cancel batch processing"""
        if self.worker:
            self.worker.cancel()
            self.worker.wait()
            self.worker = None
        
        self._reset_ui()
        self.current_file_label.setText("Batch cancelled")
    
    def _on_file_started(self, file_path, index, total):
        """Handle file started signal"""
        filename = os.path.basename(file_path)
        self.current_file_label.setText(f"Processing: {filename}")
        self.status_label.setText(f"File {index + 1} of {total}")
        
        # Update list item
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == file_path:
                item.setText(f"🔄 {filename}")
                item.setBackground(QBrush(QColor(50, 100, 150, 50)))
                break
    
    def _on_file_progress(self, file_path, percent):
        """Handle file progress signal"""
        self.progress_bar.setValue(percent)
    
    def _on_file_completed(self, file_path, result):
        """Handle file completed signal"""
        filename = os.path.basename(file_path)
        
        # Update list item
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == file_path:
                item.setText(f"✅ {filename}")
                item.setBackground(QBrush(QColor(50, 150, 50, 50)))
                break
    
    def _on_file_error(self, file_path, error):
        """Handle file error signal"""
        filename = os.path.basename(file_path)
        
        # Update list item
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == file_path:
                item.setText(f"❌ {filename} - {error}")
                item.setBackground(QBrush(QColor(150, 50, 50, 50)))
                break
    
    def _on_batch_completed(self, results):
        """Handle batch completed signal"""
        completed = sum(1 for r in results if r.get('success', False))
        failed = len(results) - completed
        
        self.current_file_label.setText("Batch complete!")
        self.status_label.setText(f"✅ {completed} succeeded, ❌ {failed} failed")
        self.progress_bar.setValue(100)
        
        self._reset_ui()
        
        QMessageBox.information(
            self,
            "Batch Complete",
            f"Batch transcription finished!\n\n"
            f"✅ Completed: {completed}\n"
            f"❌ Failed: {failed}"
        )
    
    def _reset_ui(self):
        """Reset UI to initial state"""
        self.start_btn.setEnabled(len(self.files) > 0)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        self.is_paused = False
        self.worker = None
