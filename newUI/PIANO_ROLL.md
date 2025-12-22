# 🎹 Piano Roll Editor - FL Studio Style

## ✅ NEW FEATURE: Interactive Piano Roll Editor

I've completely replaced the simple matplotlib graph with a **professional FL Studio-style piano roll editor**!

### Features:

#### 1. **Piano Keys Display (Left Side)**
- White and black piano keys rendered accurately
- Note names displayed (C1, C2, C3, etc.)
- Proper key coloring (white keys = light, black keys = dark)
- MIDI pitch range: A0 (21) to C8 (108)

#### 2. **Grid System**
- Time grid (vertical lines every second)
- Pitch grid (horizontal lines per semitone)
- Emphasized grid lines every 4 seconds
- Dark background (#1e1e1e) matching DAW aesthetic

#### 3. **Spectrogram Background** (Optional)
- When audio file is provided, displays spectrogram
- Blue-to-purple gradient visualization
- Helps visualize frequency content behind notes
- Uses librosa for mel spectrogram computation

#### 4. **Interactive Note Editing**
- **Click to Add**: Click on empty space to add new note (0.5s default duration)
- **Drag to Move**: Click and drag notes horizontally to change timing
- **Right-Click to Delete**: Remove unwanted notes
- **Visual Feedback**: Selected notes highlighted in brighter purple
- **Real-time Updates**: All changes logged to console

#### 5. **Zoom Controls**
- Zoom In button (🔍+)
- Zoom Out button (🔍-)
- Dynamic canvas resizing
- Horizontal and vertical scrollbars

#### 6. **Note Visualization**
- Purple rectangles (#7c3aed) for notes
- Semi-transparent (80%) for better visibility
- Minimum width of 5 pixels for very short notes
- Selected notes use brighter color (#9333ea)

### Technical Details:

**Custom Qt Widget**: Built entirely with PySide6's QPainter
- No matplotlib dependency for piano roll
- Hardware-accelerated rendering
- Smooth mouse interaction
- Efficient painting algorithms

**Dual View Mode**:
1. **MIDI Only**: Shows notes on dark grid
2. **MIDI + Spectrogram**: Shows notes overlaid on audio spectrogram

**Signal Emissions**:
- `note_added(pitch, start_time, duration)` - When user adds note
- `note_removed(pitch, start_time)` - When user deletes note
- `note_modified(pitch, old_start, new_start, duration)` - When user moves note

### Usage:

```python
# Load MIDI file
piano_roll.load_midi("path/to/file.mid")

# Load both MIDI and audio (for spectrogram)
piano_roll.load_midi("path/to/file.mid")
piano_roll.load_spectrogram("path/to/audio.wav")

# Connect to note editing signals
piano_roll.note_added.connect(on_note_added)
piano_roll.note_removed.connect(on_note_removed)
piano_roll.note_modified.connect(on_note_modified)
```

### What It Looks Like:

```
┌─────────┬────────────────────────────────────────────┐
│  C8     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  ■■     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  □□     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  ■■     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  □□     │░░░░░░░░░█████░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  ■■     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  C7     │░░░░░░░░░░░░░░░░░░░░█████░░░░░░░░░░░░░░░░░│
│  ■■     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  □□     │░░░░░░░░░░░░░░░█████░░░░░░░░░░░░░░░░░░░░░░│
│  ...    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  C1     │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
└─────────┴────────────────────────────────────────────┘
  Piano      Time →
  Keys     (░ = spectrogram, █ = notes)
```

### Controls:

- **Left Click**: Add note or select existing note
- **Right Click**: Delete note
- **Drag**: Move note horizontally (change timing)
- **Toolbar**:
  - 🗑️ Clear All Notes
  - 🔍 Zoom In
  - 🔍 Zoom Out

### Future Enhancements (Optional):

- [ ] Note resizing (drag right edge to change duration)
- [ ] Velocity editing (note brightness)
- [ ] Multi-select (Ctrl+Click)
- [ ] Copy/Paste notes
- [ ] Snap to grid option
- [ ] Export edited MIDI

---

**The piano roll is now fully functional and ready for professional music editing!** 🎵
