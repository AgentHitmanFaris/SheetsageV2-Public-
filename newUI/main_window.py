"""
Main Window for SheetSage Native UI
Implements the primary application window with menu bar, toolbar, and three-panel layout
"""

import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QSplitter,
    QMessageBox, QLabel
)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtCore import Qt, QSize


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sheet Sage V3 - Music Transcription Suite")
        self.setMinimumSize(1400, 800)
        
        # Transcription state
        self.current_worker = None
        self.current_config = None
        
        # Initialize UI components
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
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
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut(QKeySequence.HelpContents)
        docs_action.setStatusTip("View user documentation")
        docs_action.triggered.connect(self._on_docs)
        help_menu.addAction(docs_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About Sheet Sage", self)
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
        
        # === Left Sidebar ===
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(1)
        
        # File Input Section
        from widgets.file_input_panel import FileInputPanel
        self.file_input_panel = FileInputPanel()
        self.file_input_panel.file_selected.connect(self._on_file_selected)
        self.file_input_panel.transcribe_requested.connect(self._on_transcribe_requested)
        # Add margins for Sidebar look
        self.file_input_panel.setContentsMargins(4, 4, 4, 4)
        sidebar_layout.addWidget(self.file_input_panel)
        
        # Audio Mixer Section
        from widgets.audio_mixer_panel import AudioMixerPanel
        self.audio_mixer = AudioMixerPanel()
        self.audio_mixer.playback_started.connect(self._on_playback_started)
        self.audio_mixer.playback_stopped.connect(self._on_playback_stopped)
        self.audio_mixer.playback_position_changed.connect(self._on_playback_position_changed)
        self.audio_mixer.setContentsMargins(4, 4, 4, 4)
        sidebar_layout.addWidget(self.audio_mixer)
        
        # Add sidebar to splitter
        sidebar_widget.setMinimumWidth(380)
        sidebar_widget.setMaximumWidth(480)
        splitter.addWidget(sidebar_widget)
        
        # === Center Panel (TranscriptionView) ===
        from widgets.transcription_view import TranscriptionView
        self.transcription_view = TranscriptionView()
        self.transcription_view.file_download_requested.connect(self._on_file_download)
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
    
    # Action handlers (placeholders)
    def _on_file_selected(self, file_path):
        """Handle file selection from input panel"""
        self.statusbar.showMessage(f"File selected: {os.path.basename(file_path)}", 5000)
    
    def _on_transcribe_requested(self, config):
        """Handle transcription request"""
        mode = config.get('mode', 'Unknown')
        filename = os.path.basename(config.get('audio_file', ''))
        
        # Store config
        self.current_config = config
        
        # Update UI
        self.statusbar.showMessage(f"Starting {mode} transcription for {filename}...", 0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Log to transcription view
        self.transcription_view.log_progress(f"Starting {mode} transcription...")
        self.transcription_view.log_info(f"File: {filename}")
        self.transcription_view.log_info(f"Separate Vocals: {config.get('separate_vocals', False)}")
        self.transcription_view.log_info(f"Generate PDF: {config.get('generate_pdf', False)}")
        
        # Clear previous results
        self.transcription_view.clear_output_files()
        self.audio_mixer.clear_audio()
        
        # Create and start worker
        from workers.transcription_worker import TranscriptionWorker
        self.current_worker = TranscriptionWorker(config)
        self.current_worker.progress_update.connect(self._on_transcription_progress)
        self.current_worker.progress_percent.connect(self._on_transcription_percent)
        self.current_worker.finished.connect(self._on_transcription_finished)
        self.current_worker.error.connect(self._on_transcription_error)
        self.current_worker.start()
        
        # Connect cancel button
        self.file_input_panel.cancel_btn.clicked.connect(self._on_cancel_transcription)
    
    def _on_transcription_progress(self, message):
        """Handle progress message from worker"""
        self.transcription_view.log_progress(message)
        self.statusbar.showMessage(message, 0)
    
    def _on_transcription_percent(self, percent):
        """Handle progress percentage from worker"""
        self.progress_bar.setValue(percent)
    
    def _on_transcription_finished(self, result):
        """Handle transcription completion"""
        # Reset UI
        self.progress_bar.setVisible(False)
        self.current_worker = None
        
        mode = result.get('mode', 'Unknown')
        self.transcription_view.log_success(f"{mode} transcription completed!")
        self.statusbar.showMessage("Transcription completed successfully!", 5000)
        
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
        if result.get('midi_path'):
            audio_path = result.get('original_path') or self.current_config.get('audio_file')
            self.transcription_view.set_piano_roll_data(result['midi_path'], audio_path)
        
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
    
    def _on_transcription_error(self, error_message):
        """Handle transcription error"""
        self.progress_bar.setVisible(False)
        self.file_input_panel.transcribe_btn.setEnabled(True)
        self.file_input_panel.cancel_btn.setEnabled(False)
        self.current_worker = None
        
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
            self.current_worker = None
            
            self.transcription_view.log_warning("Transcription cancelled by user")
            self.statusbar.showMessage("Transcription cancelled", 3000)
    
    def _on_file_download(self, file_path):
        """Handle file download request"""
        self.statusbar.showMessage(f"Downloaded: {os.path.basename(file_path)}", 3000)
    
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
            self.file_input_panel._on_browse_clicked()
    
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
            self.transcription_view.set_piano_roll_data(project_data['midi_path'], audio_path)
        
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
