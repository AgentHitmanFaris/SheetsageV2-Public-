"""
Piano Roll Editor Widget
FL Studio-style piano roll with spectrogram background and manual note editing
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QImage, QPalette
import numpy as np
import os


class PianoRollEditor(QWidget):
    """Piano roll editor with spectrogram background"""
    
    note_added = Signal(int, float, float)  # pitch, start_time, duration
    note_removed = Signal(int, float)  # pitch, start_time
    note_modified = Signal(int, float, float, float)  # pitch, old_start, new_start, new_duration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notes = []  # List of {pitch, start, duration}
        self.spectrogram_data = None
        self.audio_duration = 10.0  # seconds
        self.min_pitch = 21  # A0
        self.max_pitch = 108  # C8
        
        # Visual settings
        self.key_width = 60
        self.key_height = 12
        self.pixels_per_second = 100
        self.grid_color = QColor(60, 60, 60)
        self.note_color = QColor(124, 58, 237)  # Purple
        self.note_selected_color = QColor(147, 51, 234)
        
        # Interaction state
        self.selected_note = None
        self.dragging_note = None
        self.drag_start_pos = None
        self.resizing_note = None
        
        self.current_playback_time = 0.0
        
        self._setup_ui()
    
    def set_playback_position(self, time_in_seconds: float):
        """Set current playback position indicator"""
        self.current_playback_time = time_in_seconds
        self.canvas.set_playback_pos(time_in_seconds)
        
        # Auto-scroll if playing
        # Calculate x position
        x = self.canvas.key_width + int(time_in_seconds * self.canvas.pixels_per_second)
        
        # Get visible region
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            viewport_width = scroll_area.viewport().width()
            horizontal_scroll = scroll_area.horizontalScrollBar()
            current_scroll = horizontal_scroll.value()
            
            # If cursor moves near the right edge, scroll
            if x > current_scroll + viewport_width * 0.8:
                 horizontal_scroll.setValue(x - viewport_width * 0.2)
            # If cursor is behind (e.g. seek), scroll back
            elif x < current_scroll:
                 horizontal_scroll.setValue(max(0, x - viewport_width * 0.2))
    
    def _setup_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Clear All Notes")
        clear_btn.clicked.connect(self.clear_notes)
        toolbar.addWidget(clear_btn)
        
        zoom_in_btn = QPushButton("🔍 Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("🔍 Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        
        self.info_label = QLabel("Click to add notes | Drag to move | Right edge to resize")
        self.info_label.setStyleSheet("color: #999; font-size: 9pt;")
        toolbar.addWidget(self.info_label)
        
        layout.addLayout(toolbar)
        
        # Scroll area for piano roll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.canvas = PianoRollCanvas(self)
        self.canvas.note_added.connect(self.note_added)
        self.canvas.note_removed.connect(self.note_removed)
        self.canvas.note_modified.connect(self.note_modified)
        
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll)
        
        self.canvas.update_size(self.audio_duration, self.min_pitch, self.max_pitch)
    
    def load_midi(self, midi_path: str):
        """Load MIDI file and display notes"""
        try:
            import pretty_midi
            midi_data = pretty_midi.PrettyMIDI(midi_path)
            
            # Extract notes
            self.notes.clear()
            for instrument in midi_data.instruments:
                for note in instrument.notes:
                    self.notes.append({
                        'pitch': note.pitch,
                        'start': note.start,
                        'duration': note.end - note.start
                    })
            
            # Update duration
            if self.notes:
                max_end = max(n['start'] + n['duration'] for n in self.notes)
                self.audio_duration = max(10.0, max_end * 1.2)
            
            # Update canvas
            self.canvas.set_notes(self.notes)
            self.canvas.update_size(self.audio_duration, self.min_pitch, self.max_pitch)
            
        except Exception as e:
            print(f"Error loading MIDI: {e}")
            raise
    
    def load_spectrogram(self, audio_path: str):
        """Load audio and compute spectrogram for background"""
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050)
            self.audio_duration = len(y) / sr
            
            # Compute mel spectrogram
            S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
            S_db = librosa.power_to_db(S, ref=np.max)
            
            # Normalize to 0-255
            S_norm = ((S_db - S_db.min()) / (S_db.max() - S_db.min()) * 255).astype(np.uint8)
            
            self.canvas.set_spectrogram(S_norm, self.audio_duration)
            self.canvas.update_size(self.audio_duration, self.min_pitch, self.max_pitch)
            
        except Exception as e:
            print(f"Error loading spectrogram: {e}")
    
    def clear_notes(self):
        """Clear all notes"""
        self.notes.clear()
        self.canvas.set_notes([])
        self.canvas.update()
    
    def zoom_in(self):
        """Increase zoom level"""
        self.canvas.pixels_per_second = min(self.canvas.pixels_per_second * 1.5, 500)
        self.canvas.update_size(self.audio_duration, self.min_pitch, self.max_pitch)
    
    def zoom_out(self):
        """Decrease zoom level"""
        self.canvas.pixels_per_second = max(self.canvas.pixels_per_second / 1.5, 20)
        self.canvas.update_size(self.audio_duration, self.min_pitch, self.max_pitch)


class PianoRollCanvas(QWidget):
    """Custom widget for piano roll drawing and interaction"""
    
    note_added = Signal(int, float, float)
    note_removed = Signal(int, float)
    note_modified = Signal(int, float, float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notes = []
        self.spectrogram_image = None
        self.duration = 10.0
        self.min_pitch = 21
        self.max_pitch = 108
        
        self.key_width = 60
        self.key_height = 12
        self.pixels_per_second = 100
        
        self.selected_note_idx = None
        self.dragging = False
        self.drag_start = None
        self.drag_note_start = None
        
        self.setMouseTracking(True)
        self.setMinimumSize(800, 600)
    
    def set_notes(self, notes):
        """Set notes to display"""
        self.notes = notes.copy() if notes else []
        self.update()
    
    def set_spectrogram(self, spectrogram_data, duration):
        """Set spectrogram background"""
        # Convert numpy array to QImage
        height, width = spectrogram_data.shape
        
        # Create colored spectrogram (blue to purple gradient)
        colored = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(height):
            for j in range(width):
                val = spectrogram_data[i, j]
                # Blue to purple gradient
                colored[i, j, 0] = int(val * 0.3)  # Low red
                colored[i, j, 1] = int(val * 0.1)  # Very low green
                colored[i, j, 2] = val  # Full blue channel
        
        # Flip vertically
        colored = np.flipud(colored)
        
        # Ensure contiguous memory for QImage
        if not colored.flags['C_CONTIGUOUS']:
            colored = np.ascontiguousarray(colored)
        
        self.spectrogram_image = QImage(colored.data, width, height, 
                                        width * 3, QImage.Format_RGB888)
        self.duration = duration
        self.update()
    
    def update_size(self, duration, min_pitch, max_pitch):
        """Update canvas size based on duration and pitch range"""
        self.duration = duration
        self.min_pitch = min_pitch
        self.max_pitch = max_pitch
        
        width = self.key_width + int(duration * self.pixels_per_second)
        height = (max_pitch - min_pitch + 1) * self.key_height
        
        self.setMinimumSize(width, height)
        self.update()
    
    def paintEvent(self, event):
        """Paint the piano roll"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        canvas_width = int(self.duration * self.pixels_per_second)
        canvas_height = (self.max_pitch - self.min_pitch + 1) * self.key_height
        
        # Draw spectrogram background
        if self.spectrogram_image:
            target_rect = QRect(self.key_width, 0, canvas_width, canvas_height)
            painter.drawImage(target_rect, self.spectrogram_image)
        else:
            # Dark background
            painter.fillRect(self.key_width, 0, canvas_width, canvas_height, QColor(30, 30, 30))
        
        # Draw grid
        self._draw_grid(painter, canvas_width, canvas_height)
        
        # Draw piano keys
        self._draw_piano_keys(painter, canvas_height)
        
        # Draw notes
        self._draw_notes(painter)
        
        # Draw playback indicator
        self._draw_playback_pos(painter, canvas_height)
        
        painter.end()
    
    def set_playback_pos(self, time):
        """Set playback position and update"""
        self.playback_time = time
        self.update()

    def _draw_playback_pos(self, painter, height):
        """Draw vertical line for playback position"""
        if not hasattr(self, 'playback_time') or self.playback_time is None:
            return
            
        x = self.key_width + int(self.playback_time * self.pixels_per_second)
        painter.setPen(QPen(QColor(255, 0, 0), 2)) # Red line
        painter.drawLine(x, 0, x, height)
    
    def _draw_grid(self, painter, width, height):
        """Draw grid lines"""
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        
        # Horizontal lines (pitch)
        for i in range(self.max_pitch - self.min_pitch + 2):
            y = i * self.key_height
            painter.drawLine(self.key_width, y, self.key_width + width, y)
        
        # Vertical lines (time) - every second
        for t in range(int(self.duration) + 1):
            x = self.key_width + int(t * self.pixels_per_second)
            painter.drawLine(x, 0, x, height)
        
        # Emphasize every 4 seconds
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        for t in range(0, int(self.duration) + 1, 4):
            x = self.key_width + int(t * self.pixels_per_second)
            painter.drawLine(x, 0, x, height)
    
    def _draw_piano_keys(self, painter, height):
        """Draw piano keys on the left"""
        white_key_color = QColor(220, 220, 220)
        black_key_color = QColor(40, 40, 40)
        
        # Note names for black keys
        black_keys = {1, 3, 6, 8, 10}  # C#, D#, F#, G#, A#
        
        for pitch in range(self.min_pitch, self.max_pitch + 1):
            y = (self.max_pitch - pitch) * self.key_height
            note_in_octave = pitch % 12
            
            is_black = note_in_octave in black_keys
            
            # Draw key
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(QBrush(black_key_color if is_black else white_key_color))
            painter.drawRect(0, y, self.key_width, self.key_height)
            
            # Draw note name on C notes
            if note_in_octave == 0:  # C note
                octave = (pitch // 12) - 1
                painter.setPen(QColor(0, 0, 0) if not is_black else QColor(200, 200, 200))
                painter.setFont(QFont('Arial', 8))
                painter.drawText(QRect(5, y, self.key_width - 10, self.key_height),
                               Qt.AlignVCenter | Qt.AlignLeft, f"C{octave}")
    
    def _draw_notes(self, painter):
        """Draw MIDI notes"""
        for idx, note in enumerate(self.notes):
            pitch = note['pitch']
            start = note['start']
            duration = note['duration']
            
            if pitch < self.min_pitch or pitch > self.max_pitch:
                continue
            
            x = self.key_width + int(start * self.pixels_per_second)
            y = (self.max_pitch - pitch) * self.key_height
            w = max(int(duration * self.pixels_per_second), 5)
            h = self.key_height - 2
            
            # Color
            color = QColor(147, 51, 234) if idx == self.selected_note_idx else QColor(124, 58, 237)
            
            # Draw note rectangle
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(180, 100, 255), 2 if idx == self.selected_note_idx else 1))
            painter.setOpacity(0.8)
            painter.drawRect(x, y + 1, w, h)
            painter.setOpacity(1.0)
    
    def mousePressEvent(self, event):
        """Handle mouse press - add or select note"""
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            
            # Check if clicking on existing note
            clicked_note = self._get_note_at_position(x, y)
            
            if clicked_note is not None:
                self.selected_note_idx = clicked_note
                self.dragging = True
                self.drag_start = event.pos()
                self.drag_note_start = self.notes[clicked_note]['start']
                self.update()
            elif x > self.key_width:
                # Add new note
                pitch = self._y_to_pitch(y)
                start_time = self._x_to_time(x)
                
                if pitch is not None:
                    new_note = {
                        'pitch': pitch,
                        'start': start_time,
                        'duration': 0.5  # Default duration
                    }
                    self.notes.append(new_note)
                    self.selected_note_idx = len(self.notes) - 1
                    self.note_added.emit(pitch, start_time, 0.5)
                    self.update()
        
        elif event.button() == Qt.RightButton:
            # Delete note
            clicked_note = self._get_note_at_position(event.pos().x(), event.pos().y())
            if clicked_note is not None:
                note = self.notes[clicked_note]
                self.notes.pop(clicked_note)
                self.selected_note_idx = None
                self.note_removed.emit(note['pitch'], note['start'])
                self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - drag note"""
        if self.dragging and self.selected_note_idx is not None:
            delta_x = event.pos().x() - self.drag_start.x()
            delta_time = delta_x / self.pixels_per_second
            
            new_start = max(0, self.drag_note_start + delta_time)
            old_start = self.notes[self.selected_note_idx]['start']
            self.notes[self.selected_note_idx]['start'] = new_start
            
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if self.dragging and self.selected_note_idx is not None:
            note = self.notes[self.selected_note_idx]
            self.note_modified.emit(note['pitch'], self.drag_note_start, 
                                  note['start'], note['duration'])
        
        self.dragging = False
        self.drag_start = None
    
    def _get_note_at_position(self, x, y):
        """Get note index at position"""
        for idx, note in enumerate(self.notes):
            pitch = note['pitch']
            start = note['start']
            duration = note['duration']
            
            note_x = self.key_width + int(start * self.pixels_per_second)
            note_y = (self.max_pitch - pitch) * self.key_height
            note_w = max(int(duration * self.pixels_per_second), 5)
            note_h = self.key_height
            
            if (note_x <= x <= note_x + note_w and
                note_y <= y <= note_y + note_h):
                return idx
        
        return None
    
    def _y_to_pitch(self, y):
        """Convert Y coordinate to MIDI pitch"""
        row = y // self.key_height
        pitch = self.max_pitch - row
        if self.min_pitch <= pitch <= self.max_pitch:
            return pitch
        return None
    
    def _x_to_time(self, x):
        """Convert X coordinate to time"""
        return max(0, (x - self.key_width) / self.pixels_per_second)
