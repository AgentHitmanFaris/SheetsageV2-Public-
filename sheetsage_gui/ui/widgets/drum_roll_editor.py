"""
Drum Roll Editor Widget
EZdrummer-style drum editor with lane-based layout and distinct visual style
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QImage, QPolygonF, QCursor, QUndoStack, QUndoCommand
import numpy as np

# ===== Undo Commands (Duplicated from PianoRoll for independence) =====

class AddNoteCommand(QUndoCommand):
    def __init__(self, canvas, note_data, description="Add Note"):
        super().__init__(description)
        self.canvas = canvas
        self.note_data = note_data.copy()
    
    def redo(self):
        self.canvas.notes.append(self.note_data.copy())
        self.canvas.update()
    
    def undo(self):
        for i, n in enumerate(self.canvas.notes):
            if (n['pitch'] == self.note_data['pitch'] and 
                abs(n['start'] - self.note_data['start']) < 0.01):
                self.canvas.notes.pop(i)
                break
        self.canvas.update()

class DeleteNoteCommand(QUndoCommand):
    def __init__(self, canvas, note_data, index, description="Delete Note"):
        super().__init__(description)
        self.canvas = canvas
        self.note_data = note_data.copy()
        self.index = index
    
    def redo(self):
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


class DrumRollEditor(QWidget):
    """Drum editor with lane view"""
    
    note_added = Signal(int, float, float)
    note_removed = Signal(int, float)
    note_removed = Signal(int, float)
    note_modified = Signal(int, float, float, float)
    midi_saved = Signal(str)
    note_preview = Signal(int) # pitch
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notes = []
        self.audio_duration = 10.0
        
        # Undo/Redo
        self.undo_stack = QUndoStack(self)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Drums")
        save_btn.clicked.connect(self.save_midi)
        toolbar.addWidget(save_btn)
        
        undo_btn = QPushButton("↶ Undo")
        undo_btn.clicked.connect(self.undo_stack.undo)
        undo_btn.setEnabled(False)
        toolbar.addWidget(undo_btn)
        self.undo_stack.canUndoChanged.connect(undo_btn.setEnabled)
        
        redo_btn = QPushButton("↷ Redo")
        redo_btn.clicked.connect(self.undo_stack.redo)
        redo_btn.setEnabled(False)
        toolbar.addWidget(redo_btn)
        self.undo_stack.canRedoChanged.connect(redo_btn.setEnabled)
        
        toolbar.addWidget(QLabel(" | "))
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_notes)
        toolbar.addWidget(clear_btn)
        
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        
        info = QLabel("Use 💎 lanes to edit drums")
        info.setStyleSheet("color: #7c3aed; font-weight: bold;")
        toolbar.addWidget(info)
        
        layout.addLayout(toolbar)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.canvas = DrumRollCanvas(self)
        self.canvas.undo_stack = self.undo_stack
        self.canvas.note_added.connect(self.note_added)
        self.canvas.note_removed.connect(self.note_removed)
        self.canvas.note_added.connect(self.note_added)
        self.canvas.note_removed.connect(self.note_removed)
        self.canvas.note_modified.connect(self.note_modified)
        self.canvas.note_preview.connect(self.note_preview)
        
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll)
        
        # Initial sizing
        self.canvas.update_size(self.audio_duration)

    def load_midi(self, midi_path):
        import pretty_midi
        self.current_midi_path = midi_path
        try:
            midi_data = pretty_midi.PrettyMIDI(midi_path)
            self.notes.clear()
            for instrument in midi_data.instruments:
                if instrument.is_drum or True: # Omnizart Drums might not flag correctly, so load all
                     for note in instrument.notes:
                        self.notes.append({
                            'pitch': note.pitch,
                            'start': note.start,
                            'duration': note.end - note.start
                        })
            
            if self.notes:
                max_end = max(n['start'] + n['duration'] for n in self.notes)
                self.audio_duration = max(10.0, max_end * 1.2)
                
                # DEBUG: Print loaded pitches
                pitches = sorted(list(set(n['pitch'] for n in self.notes)))
                print(f"DEBUG: Loaded drum notes with pitches: {pitches}")
                
            self.canvas.set_notes(self.notes)
            self.canvas.update_size(self.audio_duration)
            
        except Exception as e:
            print(f"Error loading MIDI: {e}")

    def save_midi(self, filepath=None):
        if not self.notes: return
        try:
            import pretty_midi
            from PySide6.QtWidgets import QFileDialog
            
            if not filepath:
                default_path = self.current_midi_path.replace('.mid', '_drums_edited.mid') if getattr(self, 'current_midi_path', None) else 'drums.mid'
                filepath, _ = QFileDialog.getSaveFileName(self, "Save Drums", default_path, "MIDI (*.mid)")
            
            if not filepath: return
            
            midi = pretty_midi.PrettyMIDI()
            inst = pretty_midi.Instrument(program=0, is_drum=True)
            for n in self.notes:
                note = pretty_midi.Note(
                    velocity=100, pitch=n['pitch'], start=n['start'], end=n['start'] + max(0.1, n['duration'])
                )
                inst.notes.append(note)
            midi.instruments.append(inst)
            midi.write(filepath)
            self.midi_saved.emit(filepath)
            
        except Exception as e:
            print(f"Error saving MIDI: {e}")

    def clear_notes(self):
        self.notes.clear()
        self.canvas.set_notes([])
    
    def zoom_in(self):
        self.canvas.pixels_per_second = min(500, self.canvas.pixels_per_second * 1.5)
        self.canvas.update_size(self.audio_duration)

    def zoom_out(self):
        self.canvas.pixels_per_second = max(20, self.canvas.pixels_per_second / 1.5)
        self.canvas.update_size(self.audio_duration)
        
    def set_playback_position(self, time):
        self.canvas.set_playback_pos(time)


class DrumRollCanvas(QWidget):
    
    note_added = Signal(int, float, float)
    note_removed = Signal(int, float)
    note_added = Signal(int, float, float)
    note_removed = Signal(int, float)
    note_modified = Signal(int, float, float, float)
    note_preview = Signal(int)
    
    DRUM_MAP = [
        {'name': 'Crash 1', 'pitch': 49},
        {'name': 'Ride 1', 'pitch': 51},
        {'name': 'Open Hi-Hat', 'pitch': 46},
        {'name': 'Closed Hi-Hat', 'pitch': 42},
        {'name': 'High Tom', 'pitch': 50},
        {'name': 'Mid Tom', 'pitch': 47},
        {'name': 'Snare', 'pitch': 38},
        {'name': 'Floor Tom', 'pitch': 41},
        {'name': 'Kick', 'pitch': 36},
        # Common Alternatives / GM
        {'name': 'Kick 2', 'pitch': 35},
        {'name': 'Snare 2', 'pitch': 40},
        {'name': 'Pedal Hat', 'pitch': 44},
        {'name': 'Low Tom', 'pitch': 45},
        {'name': 'Ride 2', 'pitch': 59},
        {'name': 'Crash 2', 'pitch': 57},
        # Fallback
        {'name': 'Misc / Unknown', 'pitch': -1}, 
    ] # Ordered top to bottom
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notes = []
        self.duration = 10.0
        
        self.lane_height = 40
        self.label_width = 120
        self.pixels_per_second = 100
        
        self.setMouseTracking(True)
        self.setMinimumSize(800, len(self.DRUM_MAP) * self.lane_height)
        
        self.hover_note_idx = None
        self.selected_note_idx = None
        self.dragging = False
        self.drag_start = None
        
    def set_notes(self, notes):
        self.notes = notes.copy()
        self.update()
        
    def update_size(self, duration):
        self.duration = duration
        width = self.label_width + int(duration * self.pixels_per_second)
        height = len(self.DRUM_MAP) * self.lane_height
        self.setMinimumSize(width, height)
        self.update()
        
    def set_playback_pos(self, time):
        self.playback_time = time
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background
        painter.fillRect(0, 0, width, height, QColor(30,30,30))
        
        # Draw Lanes
        for i, drum in enumerate(self.DRUM_MAP):
            y = i * self.lane_height
            # Alternating colors
            if i % 2 == 0:
                painter.fillRect(self.label_width, y, width - self.label_width, self.lane_height, QColor(40,40,40))
            else:
                painter.fillRect(self.label_width, y, width - self.label_width, self.lane_height, QColor(35,35,35))
                
            # Lane Label
            painter.setPen(QPen(QColor(60,60,60)))
            painter.drawLine(0, y + self.lane_height, width, y + self.lane_height)
            
            # Label Text
            painter.fillRect(0, y, self.label_width, self.lane_height, QColor(50,50,50))
            painter.setPen(QColor(200,200,200))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(QRect(10, y, self.label_width-10, self.lane_height), Qt.AlignVCenter | Qt.AlignLeft, drum['name'])
            
        # Draw Grid (Time)
        painter.setPen(QPen(QColor(60,60,60), 1))
        for t in range(int(self.duration) + 1):
            x = self.label_width + int(t * self.pixels_per_second)
            if t % 4 == 0:
                painter.setPen(QPen(QColor(100,100,100), 2))
            else:
                painter.setPen(QPen(QColor(60,60,60), 1))
            painter.drawLine(x, 0, x, height)
            
        # Draw Diamond Notes
        for idx, note in enumerate(self.notes):
            # Find which lane this note belongs to
            lane_idx = -1
            for i, drum in enumerate(self.DRUM_MAP):
                if drum['pitch'] == note['pitch']:
                    lane_idx = i
                    break
            
            # Fallback to "Misc" lane if not found
            if lane_idx == -1:
                lane_idx = len(self.DRUM_MAP) - 1 # Last lane is Misc
                
            x = self.label_width + int(note['start'] * self.pixels_per_second)
            y = lane_idx * self.lane_height + (self.lane_height // 2)
            
            size = 14
            color = QColor(255, 165, 0) # Orange for selected
            if idx != self.selected_note_idx:
                color = QColor(0, 200, 255) # Cyan for normal
                if self.DRUM_MAP[lane_idx]['pitch'] == -1: # Different color for unmapped notes
                    color = QColor(255, 100, 100) # Reddish for unknown
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # Diamond shape
            diamond = QPolygonF()
            diamond.append(QPointF(x, y - size/2))
            diamond.append(QPointF(x + size/2, y))
            diamond.append(QPointF(x, y + size/2))
            diamond.append(QPointF(x - size/2, y))
            
            painter.drawPolygon(diamond)
            
        # Playback Cursor
        if hasattr(self, 'playback_time'):
            x = self.label_width + int(self.playback_time * self.pixels_per_second)
            painter.setPen(QPen(QColor(255, 50, 50), 2))
            painter.drawLine(x, 0, x, height)
            
        painter.end()

    def mousePressEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        
        if x < self.label_width: return
        
        # Check hitting a note
        hit_idx = self._get_note_at(x, y)
        
        if hit_idx is not None:
            if event.button() == Qt.RightButton:
                # Delete
                note = self.notes[hit_idx]
                if self.undo_stack:
                    self.undo_stack.push(DeleteNoteCommand(self, note, hit_idx))
                else:
                    self.notes.pop(hit_idx)
                self.note_removed.emit(note['pitch'], note['start'])
                self.selected_note_idx = None
            else:
                # Select / Start Drag
                self.selected_note_idx = hit_idx
                self.dragging = True
                self.drag_start = event.pos()
                self.drag_original_note = self.notes[hit_idx].copy()
                self.note_preview.emit(self.notes[hit_idx]['pitch'])
        
        elif event.button() == Qt.LeftButton:
            # Create Note
            # Determine lane
            lane_idx = y // self.lane_height
            if 0 <= lane_idx < len(self.DRUM_MAP):
                pitch = self.DRUM_MAP[lane_idx]['pitch']
                time = (x - self.label_width) / self.pixels_per_second
                
                new_note = {'pitch': pitch, 'start': time, 'duration': 0.1}
                if self.undo_stack:
                    self.undo_stack.push(AddNoteCommand(self, new_note))
                else:
                    self.notes.append(new_note)
                
                self.notes.append(new_note)
                
                self.note_added.emit(pitch, time, 0.1)
                self.note_preview.emit(pitch)
                self.selected_note_idx = len(self.notes)-1
        
        self.update()

    def mouseMoveEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        
        if self.dragging and self.selected_note_idx is not None:
            delta_x = x - self.drag_start.x()
            delta_y = y - self.drag_start.y()
            
            # Move in time
            time_shift = delta_x / self.pixels_per_second
            new_start = max(0, self.drag_original_note['start'] + time_shift)
            self.notes[self.selected_note_idx]['start'] = new_start
            
            # Move lane (pitch) if vertical drag is significant
            lane_shift = delta_y // self.lane_height
            if lane_shift != 0:
                # Find original lane
                orig_pitch = self.drag_original_note['pitch']
                orig_lane = -1
                for i, d in enumerate(self.DRUM_MAP):
                    if d['pitch'] == orig_pitch:
                        orig_lane = i
                        break
                if orig_lane == -1:
                    orig_lane = len(self.DRUM_MAP) - 1
                
                if orig_lane != -1:
                    new_lane = max(0, min(len(self.DRUM_MAP)-1, orig_lane + lane_shift))
                    self.notes[self.selected_note_idx]['pitch'] = self.DRUM_MAP[new_lane]['pitch']
            
            self.update()
            return

        # Simple hover effect
        hit = self._get_note_at(x, y)
        if hit is not None:
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if self.dragging and self.selected_note_idx is not None:
            # Commit move
            if self.undo_stack:
                 # Check if changed
                 if self.notes[self.selected_note_idx] != self.drag_original_note:
                      # Revert to original temporarily so Undo command sees the change
                      current = self.notes[self.selected_note_idx].copy()
                      self.notes[self.selected_note_idx] = self.drag_original_note
                      self.undo_stack.push(MoveNoteCommand(self, self.selected_note_idx, self.drag_original_note, current))
            pass
        self.dragging = False
        
    def _get_note_at(self, x, y):
        # Hit detection for diamonds
        # Simplified: Check circle radius 10px
        for idx, note in enumerate(self.notes):
             # Find lane
             lane_idx = -1
             for i, d in enumerate(self.DRUM_MAP):
                 if d['pitch'] == note['pitch']:
                     lane_idx = i
                     break
             
             # Fallback
             if lane_idx == -1:
                 lane_idx = len(self.DRUM_MAP) - 1
             
             nx = self.label_width + int(note['start'] * self.pixels_per_second)
             ny = lane_idx * self.lane_height + (self.lane_height // 2)
             
             if (x-nx)**2 + (y-ny)**2 < 100: # 10px radius squared
                 return idx
        return None
