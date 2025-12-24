"""
History Browser Dialog
Browse and reload previous transcription projects
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QGroupBox, QTextEdit, QSplitter, QWidget,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import os
from datetime import datetime


class HistoryBrowser(QDialog):
    """Dialog for browsing transcription history"""
    
    project_selected = Signal(dict)  # Emit project data when loaded
    
    def __init__(self, output_dir, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.projects = []
        
        self.setWindowTitle("Transcription History")
        self.setMinimumSize(900, 600)
        
        self._setup_ui()
        self._load_projects()
    
    def _setup_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Project list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("📜 Previous Transcriptions")
        list_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        left_layout.addWidget(list_label)
        
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        left_layout.addWidget(self.project_list)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_projects)
        left_layout.addWidget(refresh_btn)
        
        splitter.addWidget(left_widget)
        
        # Right: Project details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        details_label = QLabel("📊 Project Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        right_layout.addWidget(details_label)
        
        # Project info
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        
        right_layout.addWidget(info_group)
        
        # Files list
        files_group = QGroupBox("Output Files")
        files_layout = QVBoxLayout(files_group)
        
        self.files_list = QListWidget()
        files_layout.addWidget(self.files_list)
        
        right_layout.addWidget(files_group)
        
        # Load button
        load_btn = QPushButton("📂 Load This Project")
        load_btn.clicked.connect(self._on_load_project)
        load_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        right_layout.addWidget(load_btn)
        
        splitter.addWidget(right_widget)
        
        # Set splitter sizes
        splitter.setSizes([300, 600])
        
        layout.addWidget(splitter)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "secondary")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
    
    def _load_projects(self):
        """Scan output directory for projects"""
        self.projects.clear()
        self.project_list.clear()
        
        if not os.path.exists(self.output_dir):
            self.info_text.setText("Output directory does not exist.")
            return
        
        # Scan for project directories
        for item in os.listdir(self.output_dir):
            project_path = os.path.join(self.output_dir, item)
            
            if not os.path.isdir(project_path):
                continue
            
            # Check if it looks like a project (has MIDI or PDF)
            files = os.listdir(project_path)
            has_output = any(f.endswith(('.midi', '.mid', '.pdf')) for f in files)
            
            if not has_output:
                continue
            
            # Get timestamp from directory name or creation time
            try:
                # Try to parse timestamp from folder name (format: mode_filename_YYYYMMDD_HHMMSS)
                parts = item.split('_')
                if len(parts) >= 3:
                    timestamp_str = '_'.join(parts[-2:])
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                else:
                    # Fall back to directory creation time
                    timestamp = datetime.fromtimestamp(os.path.getctime(project_path))
            except:
                timestamp = datetime.fromtimestamp(os.path.getctime(project_path))
            
            # Determine mode from folder name
            mode = "Unknown"
            if item.startswith("leadsheet_"):
                mode = "Lead Sheet"
            elif item.startswith("piano_"):
                mode = "Piano"
            elif item.startswith("basicpitch_"):
                mode = "Basic Pitch"
            elif item.startswith("drums_"):
                mode = "Drums"
            elif item.startswith("lunaverus_"):
                mode = "SheetSage V3"
            
            project = {
                'path': project_path,
                'name': item,
                'mode': mode,
                'timestamp': timestamp,
                'files': files
            }
            
            self.projects.append(project)
        
        # Sort by timestamp (newest first)
        self.projects.sort(key=lambda p: p['timestamp'], reverse=True)
        
        # Add to list
        for project in self.projects:
            timestamp_str = project['timestamp'].strftime("%Y-%m-%d %H:%M")
            list_item = QListWidgetItem(f"[{timestamp_str}] {project['mode']} - {project['name']}")
            list_item.setData(Qt.UserRole, project)
            self.project_list.addItem(list_item)
        
        if not self.projects:
            self.info_text.setText("No previous transcriptions found.")
    
    def _on_project_selected(self, current, previous):
        """Handle project selection"""
        if not current:
            return
        
        project = current.data(Qt.UserRole)
        
        # Display info
        info_html = f"""
        <b>Mode:</b> {project['mode']}<br>
        <b>Date:</b> {project['timestamp'].strftime("%Y-%m-%d %H:%M:%S")}<br>
        <b>Folder:</b> {project['name']}<br>
        <b>Path:</b> {project['path']}
        """
        self.info_text.setHtml(info_html)
        
        # Display files
        self.files_list.clear()
        for filename in sorted(project['files']):
            file_path = os.path.join(project['path'], filename)
            file_size = os.path.getsize(file_path)
            size_str = self._format_size(file_size)
            
            ext = os.path.splitext(filename)[1].lower()
            icon_map = {
                '.midi': '🎹', '.mid': '🎹',
                '.pdf': '📄',
                '.wav': '🔊', '.mp3': '🔊',
                '.ly': '📝'
            }
            icon = icon_map.get(ext, '📄')
            
            item = QListWidgetItem(f"{icon} {filename} ({size_str})")
            item.setData(Qt.UserRole, file_path)
            self.files_list.addItem(item)
    
    def _on_load_project(self):
        """Load selected project"""
        current = self.project_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a project to load.")
            return
        
        project = current.data(Qt.UserRole)
        project_path = project['path']
        
        # Find files
        midi_path = None
        pdf_path = None
        synth_path = None
        mixed_path = None
        original_path = None
        vocals_path = None
        
        for filename in os.listdir(project_path):
            file_path = os.path.join(project_path, filename)
            
            if filename.endswith(('.midi', '.mid')) and not midi_path:
                midi_path = file_path
            elif filename.endswith('.pdf') and not pdf_path:
                pdf_path = file_path
            elif 'synth' in filename.lower() and filename.endswith('.wav'):
                synth_path = file_path
            elif 'mixed' in filename.lower() and filename.endswith('.wav'):
                mixed_path = file_path
            elif 'original' in filename.lower() and filename.endswith('.wav'):
                original_path = file_path
            elif 'vocals' in filename.lower() and filename.endswith('.wav'):
                vocals_path = file_path
        
        project_data = {
            'mode': project['mode'],
            'midi_path': midi_path,
            'pdf_path': pdf_path,
            'synth_path': synth_path,
            'mixed_path': mixed_path,
            'original_path': original_path,
            'vocals_path': vocals_path,
            'output_dir': project_path
        }
        
        self.project_selected.emit(project_data)
        self.accept()
    
    def _format_size(self, size_bytes):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
