"""
Audio Mixer Panel Widget
Right sidebar for audio playback with volume controls
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import os


class AudioMixerPanel(QWidget):
    """Right panel for audio playback and mixing"""
    
    # Signals
    playback_started = Signal()
    playback_stopped = Signal()
    playback_position_changed = Signal(int) # Current position in ms
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._players = {} # {name: {'player': QMediaPlayer, 'output': QAudioOutput}}
        self._master_track = None # The track driving the progress bar
        self._audio_tracks = {}  # {track_name: file_path}
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("🎵 Audio Mixer")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #7c3aed;")
        layout.addWidget(title)
        
        # === TRACK VOLUME CONTROLS ===
        
        # Original Track
        self.original_group = self._create_track_control("Original", "🎧")
        layout.addWidget(self.original_group)
        
        # Synthesized Track
        self.synth_group = self._create_track_control("Synthesized", "🎹")
        layout.addWidget(self.synth_group)
        
        # Vocals Track
        self.vocals_group = self._create_track_control("Vocals", "🎤")
        layout.addWidget(self.vocals_group)
        
        layout.addSpacing(10)
        
        # === MASTER PLAYBACK CONTROLS ===
        master_group = QGroupBox("Master Controls")
        master_layout = QVBoxLayout(master_group)
        
        # Play/Pause/Stop buttons
        button_row = QHBoxLayout()
        
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.setEnabled(False)
        button_row.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.clicked.connect(self._on_pause)
        self.pause_btn.setEnabled(False)
        button_row.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        button_row.addWidget(self.stop_btn)
        
        master_layout.addLayout(button_row)
        
        # Seek bar
        seek_layout = QHBoxLayout()
        seek_layout.addWidget(QLabel("Seek:"))
        
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderMoved.connect(self._on_seek)
        self.seek_slider.setEnabled(False)
        seek_layout.addWidget(self.seek_slider)
        
        master_layout.addLayout(seek_layout)
        
        # Time display
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #7c3aed; font-weight: bold; font-size: 11pt;")
        master_layout.addWidget(self.time_label)
        
        layout.addWidget(master_group)
        
        # === INFO DISPLAY ===
        layout.addStretch()
        
        self.info_label = QLabel("No audio loaded\nTranscribe to enable playback")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #999; font-size: 9pt; padding: 10px;")
        layout.addWidget(self.info_label)
    
    def _create_track_control(self, name: str, icon: str):
        """Create a track volume control group"""
        group = QGroupBox(f"{icon} {name}")
        layout = QVBoxLayout(group)
        
        # Volume slider
        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Volume:"))
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(70) # Default volume
        slider.setTickInterval(10)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.valueChanged.connect(lambda v: self._on_volume_changed(name, v))
        slider_row.addWidget(slider)
        
        volume_label = QLabel("70%")
        volume_label.setMinimumWidth(40)
        volume_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_row.addWidget(volume_label)
        
        layout.addLayout(slider_row)
        
        # Mute button
        mute_btn = QPushButton("🔇 Mute")
        mute_btn.setCheckable(True)
        mute_btn.setProperty("class", "secondary")
        mute_btn.toggled.connect(lambda checked: self._on_mute_toggled(name, checked, mute_btn))
        layout.addWidget(mute_btn)
        
        # Store references to UI elements dynamically
        setattr(self, f"{name.lower()}_group", group)
        setattr(self, f"{name.lower()}_slider", slider)
        setattr(self, f"{name.lower()}_volume_label", volume_label)
        setattr(self, f"{name.lower()}_mute_btn", mute_btn)
        
        group.setEnabled(False)  # Disabled until audio is loaded
        return group
    
    def load_audio_tracks(self, tracks: dict):
        """
        Load audio tracks for playback with independent players
        tracks: dict of {track_name: file_path}
        """
        self.clear_audio()
        self._audio_tracks = tracks
        
        # Choose master track (longest or Original/Synthesized preference)
        if "Original" in tracks:
            self._master_track = "Original"
        elif "Synthesized" in tracks:
            self._master_track = "Synthesized"
        elif "Vocals" in tracks:
            self._master_track = "Vocals"
        else:
            self._master_track = None
            return

        for name, path in tracks.items():
            if not os.path.exists(path):
                continue
                
            player = QMediaPlayer()
            audio_output = QAudioOutput()
            player.setAudioOutput(audio_output)
            player.setSource(QUrl.fromLocalFile(path))
            
            # Set initial volume
            initial_vol = 70
            if name == "Original": initial_vol = 70
            elif name == "Synthesized": initial_vol = 100
            elif name == "Vocals": initial_vol = 70
            
            # Specific UI defaults update
            slider = getattr(self, f"{name.lower()}_slider", None)
            if slider:
                slider.setValue(initial_vol)
            
            audio_output.setVolume(initial_vol / 100.0)
            
            self._players[name] = {'player': player, 'output': audio_output}
            
            # Enable UI
            group = getattr(self, f"{name.lower()}_group", None)
            if group: group.setEnabled(True)
            
            # Connect master track events
            if name == self._master_track:
                player.positionChanged.connect(self._on_position_changed)
                player.durationChanged.connect(self._on_duration_changed)
                player.playbackStateChanged.connect(self._on_playback_state_changed)
        
        if self._players:
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.seek_slider.setEnabled(True)
            
            track_names = ", ".join(self._players.keys())
            self.info_label.setText(f"Loaded tracks:\n{track_names}")
    
    def clear_audio(self):
        """Clear all players"""
        for data in self._players.values():
            data['player'].stop()
            data['player'].setSource(QUrl())
        self._players.clear()
        
        # Disable all controls
        self.original_group.setEnabled(False)
        self.synth_group.setEnabled(False)
        self.vocals_group.setEnabled(False)
        
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.seek_slider.setEnabled(False)
        
        self.time_label.setText("00:00 / 00:00")
        self.info_label.setText("No audio loaded\nTranscribe to enable playback")
    
    def _on_volume_changed(self, track_name: str, value: int):
        """Handle volume slider change for a specific track"""
        volume_label = getattr(self, f"{track_name.lower()}_volume_label", None)
        if volume_label:
            volume_label.setText(f"{value}%")
        
        if track_name in self._players:
            self._players[track_name]['output'].setVolume(value / 100.0)
    
    def _on_mute_toggled(self, track_name: str, checked: bool, button: QPushButton):
        """Handle mute button toggle"""
        if checked:
            button.setText("🔊 Unmute")
            if track_name in self._players:
                self._players[track_name]['output'].setMuted(True)
        else:
            button.setText("🔇 Mute")
            if track_name in self._players:
                self._players[track_name]['output'].setMuted(False)
    
    def _on_play(self):
        """Play all tracks simultaneously"""
        for data in self._players.values():
            data['player'].play()
        self.playback_started.emit()
    
    def _on_pause(self):
        """Pause all tracks simultaneously"""
        for data in self._players.values():
            data['player'].pause()
    
    def _on_stop(self):
        """Stop all tracks simultaneously"""
        for data in self._players.values():
            data['player'].stop()
        self.seek_slider.setValue(0)
        self.playback_stopped.emit()
    
    def _on_seek(self, position: int):
        """Seek all tracks simultaneously"""
        if not self._master_track or self._master_track not in self._players:
            return
            
        master_player = self._players[self._master_track]['player']
        duration = master_player.duration()
        
        if duration > 0:
            actual_position = int((position / 1000.0) * duration)
            for data in self._players.values():
                data['player'].setPosition(actual_position)
    
    def _on_position_changed(self, position: int):
        """Update UI based on master track position"""
        if not self._master_track or self._master_track not in self._players:
            return
            
        master_player = self._players[self._master_track]['player']
        duration = master_player.duration()
        
        if duration > 0:
            slider_position = int((position / duration) * 1000)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(slider_position)
            self.seek_slider.blockSignals(False)
        
        self._update_time_display(position, duration)
    
    def _on_duration_changed(self, duration: int):
        """Update UI when master duration changes"""
        position = 0
        if self._master_track and self._master_track in self._players:
            position = self._players[self._master_track]['player'].position()
        self._update_time_display(position, duration)
    
    def _update_time_display(self, position: int, duration: int):
        """Update the time display label"""
        # Emit signal for other widgets (e.g. piano roll)
        self.playback_position_changed.emit(position)
        
        def format_time(ms: int) -> str:
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        
        current = format_time(position)
        total = format_time(duration) if duration > 0 else "00:00"
        self.time_label.setText(f"{current} / {total}")
    
    def _on_playback_state_changed(self, state):
        """Update play button text based on master state"""
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸️ Pause")
        else:
            self.play_btn.setText("▶️ Play")
