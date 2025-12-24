# High Impact Features - Implementation Plan
**Version 0.5.0 Development Roadmap**

Created: December 23, 2025  
Status: 🚧 In Progress

---

## 🎯 Feature Overview

### 1. **📝 MIDI Editing in Piano Roll** (Priority 1)
**Goal**: Enable direct manipulation of notes in the piano roll viewer

**User Stories:**
- As a user, I want to click and drag notes to change their pitch
- As a user, I want to resize notes to adjust their duration
- As a user, I want to delete notes by right-clicking or pressing Delete
- As a user, I want to add new notes by clicking on empty space
- As a user, I want to save my edited MIDI file

**Technical Implementation:**
- [x] **Phase 1**: Basic note detection (DONE - already in PianoRollCanvas)
- [x] **Phase 2**: Implement note dragging (vertical = pitch, horizontal = time)
- [x] **Phase 3**: Implement note resizing (drag left/right edges)
- [x] **Phase 4**: Implement note deletion (right-click menu + Delete key)
- [x] **Phase 5**: Implement note creation (click empty space)
- [ ] **Phase 6**: Add undo/redo system (QUndoStack) - IN PROGRESS
- [x] **Phase 7**: Implement "Save MIDI" functionality
- [x] **Phase 8**: Add visual feedback (hover states, cursor changes)

**Files to Modify:**
- `widgets/piano_roll_editor.py` - Add editing logic
- `main_window.py` - Add "Save Edited MIDI" menu item
- Create: `utils/midi_editor.py` - MIDI manipulation utilities

**Estimated Time**: 4-6 hours

---

### 2. **⌨️ Keyboard Shortcuts** (Priority 2)
**Goal**: Add power-user keyboard shortcuts for common actions

**Shortcuts to Implement:**

| Action | Shortcut | Category |
|--------|----------|----------|
| Open File | `Ctrl+O` | File |
| Save MIDI | `Ctrl+S` | File |
| Export | `Ctrl+E` | File |
| Quit | `Ctrl+Q` | File |
| Undo | `Ctrl+Z` | Edit |
| Redo | `Ctrl+Y` | Edit |
| Delete Note | `Delete` | Edit |
| Select All | `Ctrl+A` | Edit |
| Play/Pause | `Space` | Playback |
| Stop | `Escape` | Playback |
| Zoom In | `Ctrl++` | View |
| Zoom Out | `Ctrl+-` | View |
| Jump to Start | `Home` | Playback |
| Jump to End | `End` | Playback |
| Toggle Settings | `Ctrl+,` | Tools |

**Technical Implementation:**
- [ ] **Phase 1**: Add QShortcut objects to MainWindow
- [ ] **Phase 2**: Implement keyboard event handlers
- [ ] **Phase 3**: Add shortcuts to menu items (displayed in UI)
- [ ] **Phase 4**: Create keyboard shortcuts help dialog (`F1`)
- [ ] **Phase 5**: Make shortcuts configurable in Settings

**Files to Modify:**
- `main_window.py` - Add shortcuts
- `widgets/settings_dialog.py` - Add shortcuts configuration tab
- Create: `widgets/shortcuts_help_dialog.py` - Display shortcuts

**Estimated Time**: 3-4 hours

---

### 3. **📦 Batch Processing** (Priority 3)
**Goal**: Allow users to queue and process multiple audio files

**User Stories:**
- As a user, I want to add multiple files to a queue
- As a user, I want to see the processing progress for each file
- As a user, I want to apply the same settings to all files
- As a user, I want to remove files from the queue before processing
- As a user, I want to see which files succeeded/failed

**UI Design:**
```
┌─────────────────────────────────────────────┐
│  Batch Transcription Queue                  │
├─────────────────────────────────────────────┤
│  [+ Add Files] [+ Add Folder] [Clear All]   │
├─────────────────────────────────────────────┤
│  📁 song1.mp3          ✓ Complete           │
│  📁 song2.wav          🔄 Processing (45%)   │
│  📁 song3.flac         ⏸️ Pending            │
│  📁 song4.m4a          ❌ Failed             │
├─────────────────────────────────────────────┤
│  Progress: 2/4 files | 1 failed             │
│  [⏸️ Pause] [⏭️ Skip] [🗑️ Cancel]          │
└─────────────────────────────────────────────┘
```

**Technical Implementation:**
- [ ] **Phase 1**: Create BatchProcessingDialog widget
- [ ] **Phase 2**: Implement file queue management (add, remove, reorder)
- [ ] **Phase 3**: Create BatchWorker (processes files sequentially)
- [ ] **Phase 4**: Add progress tracking per file
- [ ] **Phase 5**: Implement pause/resume/skip functionality
- [ ] **Phase 6**: Add batch results summary
- [ ] **Phase 7**: Auto-save results to organized folders

**Files to Create:**
- `widgets/batch_processing_dialog.py` - Main batch UI
- `workers/batch_worker.py` - Batch transcription worker

**Files to Modify:**
- `main_window.py` - Add "Batch Transcribe" menu item

**Estimated Time**: 6-8 hours

---

### 4. **💾 Export Options - MusicXML** (Priority 4)
**Goal**: Export transcriptions in MusicXML format for notation software

**Supported Export Formats:**
- [x] MIDI (already supported)
- [x] PDF (already supported)
- [ ] **MusicXML** - For MuseScore, Finale, Sibelius
- [ ] **JSON** - For programmatic access
- [ ] **LilyPond** - For advanced engraving (future)

**Technical Implementation:**
- [ ] **Phase 1**: Install/integrate `music21` library
- [ ] **Phase 2**: Create MusicXML converter (MIDI → MusicXML)
- [ ] **Phase 3**: Add metadata support (title, composer, key, time signature)
- [ ] **Phase 4**: Implement intelligent voice separation for polyphonic music
- [ ] **Phase 5**: Add export options dialog
- [ ] **Phase 6**: Create JSON export for API/scripting use

**Files to Create:**
- `utils/export_formats.py` - Export utilities
- `widgets/export_dialog.py` - Export configuration UI

**Files to Modify:**
- `main_window.py` - Add "Export As..." menu
- `requirements.txt` - Add `music21`

**Estimated Time**: 4-5 hours

---

## 📅 Implementation Schedule

### Week 1: Core Editing (Features 1 & 2)
- **Day 1-2**: MIDI Editing - Dragging & Resizing
- **Day 3**: MIDI Editing - Creation & Deletion + Undo/Redo
- **Day 4**: Keyboard Shortcuts Implementation
- **Day 5**: Testing & Bug Fixes

### Week 2: Batch & Export (Features 3 & 4)
- **Day 1-2**: Batch Processing UI & Worker
- **Day 3**: Batch Testing & Polish
- **Day 4**: MusicXML Export Implementation
- **Day 5**: Final Testing & Documentation

---

## ✅ Success Criteria

### MIDI Editing
- [ ] Users can drag notes vertically (pitch change)
- [ ] Users can drag notes horizontally (time shift)
- [ ] Users can resize notes (duration change)
- [ ] Users can delete notes (Delete key + right-click)
- [ ] Users can add notes (click + drag)
- [ ] Undo/Redo works correctly
- [ ] Edited MIDI can be saved

### Keyboard Shortcuts
- [ ] All shortcuts work as expected
- [ ] Shortcuts are displayed in menus
- [ ] F1 shows shortcuts help
- [ ] No conflicts with OS shortcuts

### Batch Processing
- [ ] Can add 10+ files to queue
- [ ] Progress updates correctly per file
- [ ] Can pause, resume, skip files
- [ ] Error handling doesn't crash batch
- [ ] Results organized in folders

### Export Options
- [ ] MusicXML export opens in MuseScore
- [ ] JSON export is valid and complete
- [ ] Export dialog shows all options
- [ ] Export preserves note data accurately

---

## 🚀 Next Steps

**Immediate Action**: Start with Feature 1 (MIDI Editing)

**Order of Implementation:**
1. 📝 MIDI Editing (Most requested, builds on existing piano roll)
2. ⌨️ Keyboard Shortcuts (Quick win, improves UX)
3. 💾 Export Options (Requires MIDI editing to be complete)
4. 📦 Batch Processing (Independent, can be done in parallel)

---

## 📊 Progress Tracking

| Feature | Status | Progress | Est. Completion |
|---------|--------|----------|-----------------|
| MIDI Editing | 🚧 Starting | 0% | Dec 24 |
| Keyboard Shortcuts | ⏸️ Pending | 0% | Dec 25 |
| Batch Processing | ⏸️ Pending | 0% | Dec 27 |
| Export Options | ⏸️ Pending | 0% | Dec 28 |

**Overall Progress: 0/4 features complete**

---

*This plan will be updated as implementation progresses*
