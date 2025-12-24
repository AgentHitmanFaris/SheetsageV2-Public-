"""
Piano Roll Editor Widget
FL Studio-style piano roll with spectrogram background and manual note editing
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QImage, QPalette, QCursor, QUndoStack, QUndoCommand
import numpy as np
import os


# ===== Undo Commands for Piano Roll Editing =====

class AddNoteCommand(QUndoCommand):
    """Command to add a note (undoable)"""
    def __init__(self, canvas, note_data, description="Add Note"):
        super().__init__(description)
        self.canvas = canvas
        self.note_data = note_data.copy()
    
    def redo(self):
        self.canvas.notes.append(self.note_data.copy())
        self.canvas.update()
    
    def undo(self):
        # Find and remove the note
        for i, n in enumerate(self.canvas.notes):
            if (n['pitch'] == self.note_data['pitch'] and 
                abs(n['start'] - self.note_data['start']) < 0.01):
                self.canvas.notes.pop(i)
                break
        self.canvas.update()


class DeleteNoteCommand(QUndoCommand):
    """Command to delete a note (undoable)"""
    def __init__(self, canvas, note_data, index, description="Delete Note"):
        super().__init__(description)
        self.canvas = canvas
        self.note_data = note_data.copy()
        self.index = index
    
    def redo(self):
        # Find and remove the note
        for i, n in enumerate(self.canvas.notes):
            if (n['pitch'] == self.note_data['pitch'] and 
                abs(n['start'] - self.note_data['start']) < 0.01):
                self.canvas.notes.pop(i)
                break
        self.canvas.update()
    
    def undo(self):
        self.canvas.notes.insert(self.index, self.note_data.copy())
        self.canvas.update()


class MoveNoteCommand(QUndoCommand):
    """Command to move/resize a note (undoable)"""
    def __init__(self, canvas, index, old_data, new_data, description="Move Note"):
        super().__init__(description)
        self.canvas = canvas
        self.index = index
        self.old_data = old_data.copy()
        self.new_data = new_data.copy()
    
    def redo(self):
        if self.index < len(self.canvas.notes):
            self.canvas.notes[self.index] = self.new_data.copy()
            self.canvas.update()
    
    def undo(self):
        if self.index < len(self.canvas.notes):
            self.canvas.notes[self.index] = self.old_data.copy()
            self.canvas.update()


class PianoRollEditor(QWidget):
    """Piano roll editor with spectrogram background"""
    
    note_added = Signal(int, float, float)  # pitch, start_time, duration
    note_removed = Signal(int, float)  # pitch, start_time
    note_modified = Signal(int, float, float, float)  # pitch, old_start, new_start, new_duration
    midi_saved = Signal(str)  # path where MIDI was saved
    note_preview = Signal(int) # pitch
    
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
        self.current_midi_path = None  # Store loaded MIDI path for saving
        
        # Undo/Redo system
        self.undo_stack = QUndoStack(self)
        
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
        
        # Save button
        save_btn = QPushButton("💾 Save MIDI")
        save_btn.clicked.connect(self.save_midi)
        save_btn.setToolTip("Save edited MIDI (Ctrl+S)")
        toolbar.addWidget(save_btn)
        
        # Undo button
        undo_btn = QPushButton("↶ Undo")
        undo_btn.clicked.connect(self.undo_stack.undo)
        undo_btn.setToolTip("Undo last action (Ctrl+Z)")
        undo_btn.setEnabled(False)
        toolbar.addWidget(undo_btn)
        self.undo_stack.canUndoChanged.connect(undo_btn.setEnabled)
        
        # Redo button
        redo_btn = QPushButton("↷ Redo")
        redo_btn.clicked.connect(self.undo_stack.redo)
        redo_btn.setToolTip("Redo last action (Ctrl+Y)")
        redo_btn.setEnabled(False)
        toolbar.addWidget(redo_btn)
        self.undo_stack.canRedoChanged.connect(redo_btn.setEnabled)
        
        toolbar.addWidget(QLabel("  |  "))  # Separator
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self.clear_notes)
        toolbar.addWidget(clear_btn)
        
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        
        self.info_label = QLabel("Left-click: Add/Select | Drag: Move | Edges: Resize | Right-click: Delete | Ctrl+Z/Y: Undo/Redo")
        self.info_label.setStyleSheet("color: #999; font-size: 9pt;")
        toolbar.addWidget(self.info_label)
        
        layout.addLayout(toolbar)
        
        # Scroll area for piano roll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.canvas = PianoRollCanvas(self)
        self.canvas.undo_stack = self.undo_stack  # Share undo stack
        self.canvas.note_added.connect(self.note_added)
        self.canvas.note_removed.connect(self.note_removed)
        self.canvas.note_removed.connect(self.note_removed)
        self.canvas.note_modified.connect(self.note_modified)
        self.canvas.note_preview.connect(self.note_preview)
        
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll)
        
        self.canvas.update_size(self.audio_duration, self.min_pitch, self.max_pitch)
    
    def load_midi(self, midi_path: str):
        """Load MIDI file and display notes"""
        try:
            import pretty_midi
            self.current_midi_path = midi_path  # Store for saving
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
    
    def save_midi(self, filepath=None):
        """Save edited MIDI to file. If filepath is None, prompt user."""
        if not self.notes:
            print("No notes to save")
            return
        
        try:
            import pretty_midi
            from PySide6.QtWidgets import QFileDialog
            
            if filepath:
                save_path = filepath
            else:
                # Determine save path
                if self.current_midi_path:
                    # Save to same path or prompt for new name
                    default_path = self.current_midi_path.replace('.mid', '_edited.mid')
                else:
                    default_path = 'output.mid'
                
                save_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save MIDI File",
                    default_path,
                    "MIDI Files (*.mid *.midi)"
                )
            
            if not save_path:
                return  # User cancelled
            
            # Create MIDI file
            midi = pretty_midi.PrettyMIDI()
            instrument = pretty_midi.Instrument(program=0)  # Acoustic Grand Piano
            
            # Add notes
            for note_data in self.notes:
                note = pretty_midi.Note(
                    velocity=100,
                    pitch=note_data['pitch'],
                    start=note_data['start'],
                    end=note_data['start'] + note_data['duration']
                )
                instrument.notes.append(note)
            
            midi.instruments.append(instrument)
            midi.write(save_path)
            
            self.current_midi_path = save_path
            self.midi_saved.emit(save_path)
            print(f"MIDI saved to: {save_path}")
            
        except Exception as e:
            print(f"Error saving MIDI: {e}")
    
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
    
    def wheelEvent(self, event):
        """Handle mouse wheel - Ctrl+Scroll for zoom"""
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+Scroll = Zoom
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            # Normal scroll - pass to scroll area
            super().wheelEvent(event)


class PianoRollCanvas(QWidget):
    """Custom widget for piano roll drawing and interaction"""
    
    note_added = Signal(int, float, float)
    note_removed = Signal(int, float)
    note_modified = Signal(int, float, float, float)
    note_preview = Signal(int)
    
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
        
        # Editing state
        self.selected_note_idx = None
        self.dragging = False
        self.drag_start = None
        self.drag_note_start = None
        self.drag_note_pitch = None  # For vertical dragging
        
        # Resizing state
        self.resizing = False
        self.resize_edge = None  # 'left' or 'right'
        self.resize_original_duration = None
        self.resize_original_start = None
        
        # Interaction modes
        self.hover_note_idx = None
        self.hover_edge = None  # Which edge we're hovering over
        
        # Undo stack (will be set by parent)
        self.undo_stack = None
        
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
        """Handle mouse press - add, select, or resize note"""
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            
            # First check if clicking on a resize edge
            edge_info = self._get_note_edge_at_position(x, y)
            if edge_info is not None:
                idx, edge = edge_info
                self.selected_note_idx = idx
                self.resizing = True
                self.resize_edge = edge
                self.drag_start = event.pos()
                self.resize_original_duration = self.notes[idx]['duration']
                self.resize_original_start = self.notes[idx]['start']
                # Save original state for undo
                self.resize_original_note = self.notes[idx].copy()
                self.setCursor(QCursor(Qt.SizeHorCursor))
                return
            
            # Check if clicking on existing note (not edge)
            clicked_note = self._get_note_at_position(x, y)
            
            if clicked_note is not None:
                self.selected_note_idx = clicked_note
                self.dragging = True
                self.drag_start = event.pos()
                self.drag_note_start = self.notes[clicked_note]['start']
                self.drag_note_pitch = self.notes[clicked_note]['pitch']
                # Save original state for undo
                self.drag_original_note = self.notes[clicked_note].copy()
                self.update()
                self.note_preview.emit(self.notes[clicked_note]['pitch'])
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
                    # Use undo command for add
                    if hasattr(self, 'undo_stack') and self.undo_stack:
                        cmd = AddNoteCommand(self, new_note)
                        self.undo_stack.push(cmd)
                    else:
                        self.notes.append(new_note)
                    self.selected_note_idx = len(self.notes) - 1
                    self.note_added.emit(pitch, start_time, 0.5)
                    self.note_preview.emit(pitch)
                    self.update()
        
        elif event.button() == Qt.RightButton:
            # Delete note
            clicked_note = self._get_note_at_position(event.pos().x(), event.pos().y())
            if clicked_note is not None:
                note = self.notes[clicked_note]
                # Use undo command for delete
                if hasattr(self, 'undo_stack') and self.undo_stack:
                    cmd = DeleteNoteCommand(self, note, clicked_note)
                    self.undo_stack.push(cmd)
                else:
                    self.notes.pop(clicked_note)
                self.selected_note_idx = None
                self.note_removed.emit(note['pitch'], note['start'])
                self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - drag note, resize, or update cursor"""
        x = event.pos().x()
        y = event.pos().y()
        
        # Handle resizing
        if self.resizing and self.selected_note_idx is not None:
            note = self.notes[self.selected_note_idx]
            delta_x = x - self.drag_start.x()
            delta_time = delta_x / self.pixels_per_second
            
            if self.resize_edge == 'right':
                # Resize from right edge (change duration)
                new_duration = max(0.1, self.resize_original_duration + delta_time)
                note['duration'] = new_duration
            elif self.resize_edge == 'left':
                # Resize from left edge (change start and duration)
                new_start = max(0, self.resize_original_start + delta_time)
                duration_change = new_start - self.resize_original_start
                new_duration = max(0.1, self.resize_original_duration - duration_change)
                note['start'] = new_start
                note['duration'] = new_duration
            
            self.update()
            return
        
        # Handle dragging (both horizontal and vertical)
        if self.dragging and self.selected_note_idx is not None:
            delta_x = x - self.drag_start.x()
            delta_y = y - self.drag_start.y()
            
            # Calculate new time (horizontal)
            delta_time = delta_x / self.pixels_per_second
            new_start = max(0, self.drag_note_start + delta_time)
            
            # Calculate new pitch (vertical)
            delta_rows = -delta_y // self.key_height  # Negative because y increases downward
            new_pitch = self.drag_note_pitch + delta_rows
            new_pitch = max(self.min_pitch, min(self.max_pitch, new_pitch))
            
            # Update note
            self.notes[self.selected_note_idx]['start'] = new_start
            self.notes[self.selected_note_idx]['pitch'] = new_pitch
            
            self.update()
            return
        
        # Update cursor based on hover
        edge_info = self._get_note_edge_at_position(x, y)
        if edge_info is not None:
            self.setCursor(QCursor(Qt.SizeHorCursor))
            self.hover_note_idx = edge_info[0]
            self.hover_edge = edge_info[1]
        else:
            note_idx = self._get_note_at_position(x, y)
            if note_idx is not None:
                self.setCursor(QCursor(Qt.SizeAllCursor))
                self.hover_note_idx = note_idx
                self.hover_edge = None
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
                self.hover_note_idx = None
                self.hover_edge = None
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if (self.dragging or self.resizing) and self.selected_note_idx is not None:
            note = self.notes[self.selected_note_idx]
            
            if self.dragging:
                # Push undo command for move
                if hasattr(self, 'undo_stack') and self.undo_stack and hasattr(self, 'drag_original_note'):
                    old_data = self.drag_original_note
                    new_data = note.copy()
                    # Only push command if note actually changed
                    if old_data != new_data:
                        # Restore original and let command handle the change
                        self.notes[self.selected_note_idx] = old_data.copy()
                        cmd = MoveNoteCommand(self, self.selected_note_idx, old_data, new_data, "Move Note")
                        self.undo_stack.push(cmd)
                
                self.note_modified.emit(
                    note['pitch'], 
                    self.drag_note_start,
                    note['start'], 
                    note['duration']
                )
            elif self.resizing:
                # Push undo command for resize
                if hasattr(self, 'undo_stack') and self.undo_stack and hasattr(self, 'resize_original_note'):
                    old_data = self.resize_original_note
                    new_data = note.copy()
                    # Only push command if note actually changed
                    if old_data != new_data:
                        # Restore original and let command handle the change
                        self.notes[self.selected_note_idx] = old_data.copy()
                        cmd = MoveNoteCommand(self, self.selected_note_idx, old_data, new_data, "Resize Note")
                        self.undo_stack.push(cmd)
                
                self.note_modified.emit(
                    note['pitch'],
                    self.resize_original_start,
                    note['start'],
                    note['duration']
                )
        
        self.dragging = False
        self.resizing = False
        self.drag_start = None
        self.resize_edge = None
        self.drag_original_note = None
        self.resize_original_note = None
        self.setCursor(QCursor(Qt.ArrowCursor))
    
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
    
    def _get_note_edge_at_position(self, x, y):
        """Check if position is near a note edge for resizing"""
        edge_threshold = 8  # pixels
        
        for idx, note in enumerate(self.notes):
            pitch = note['pitch']
            start = note['start']
            duration = note['duration']
            
            note_x = self.key_width + int(start * self.pixels_per_second)
            note_y = (self.max_pitch - pitch) * self.key_height
            note_w = max(int(duration * self.pixels_per_second), 5)
            note_h = self.key_height
            
            # Check if y is within note
            if not (note_y <= y <= note_y + note_h):
                continue
            
            # Check for left edge
            if abs(x - note_x) < edge_threshold:
                return (idx, 'left')
            
            # Check for right edge
            if abs(x - (note_x + note_w)) < edge_threshold:
                return (idx, 'right')
        
        return None
