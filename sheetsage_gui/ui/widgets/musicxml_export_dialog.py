"""
MusicXML Export Dialog
Export MIDI transcriptions to MusicXML format for use in notation software
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QComboBox, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
import os


class MusicXMLExportDialog(QDialog):
    """Dialog for exporting to MusicXML format"""
    
    export_completed = Signal(str)  # Path to exported file
    
    def __init__(self, midi_path=None, notes=None, parent=None):
        super().__init__(parent)
        self.midi_path = midi_path
        self.notes = notes or []
        self.setWindowTitle("🎼 Export to MusicXML")
        self.setMinimumWidth(450)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Export your transcription to MusicXML format for use in:")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
        
        apps_label = QLabel("MuseScore • Finale • Sibelius • Notion • Dorico")
        apps_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(apps_label)
        
        # === METADATA SECTION ===
        metadata_group = QGroupBox("Score Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter score title...")
        if self.midi_path:
            # Use filename as default title
            basename = os.path.splitext(os.path.basename(self.midi_path))[0]
            self.title_edit.setText(basename.replace('_', ' ').title())
        metadata_layout.addRow("Title:", self.title_edit)
        
        self.composer_edit = QLineEdit()
        self.composer_edit.setPlaceholderText("Enter composer/artist name...")
        metadata_layout.addRow("Composer:", self.composer_edit)
        
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(20, 300)
        self.tempo_spin.setValue(120)
        self.tempo_spin.setSuffix(" BPM")
        metadata_layout.addRow("Tempo:", self.tempo_spin)
        
        layout.addWidget(metadata_group)
        
        # === OPTIONS SECTION ===
        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout(options_group)
        
        self.key_combo = QComboBox()
        self.key_combo.addItems([
            "C Major / A Minor",
            "G Major / E Minor",
            "D Major / B Minor",
            "A Major / F# Minor",
            "E Major / C# Minor",
            "F Major / D Minor",
            "Bb Major / G Minor",
            "Eb Major / C Minor",
        ])
        options_layout.addRow("Key Signature:", self.key_combo)
        
        self.time_sig_combo = QComboBox()
        self.time_sig_combo.addItems(["4/4", "3/4", "2/4", "6/8", "2/2"])
        options_layout.addRow("Time Signature:", self.time_sig_combo)
        
        self.quantize_check = QCheckBox("Quantize notes to grid")
        self.quantize_check.setChecked(True)
        options_layout.addRow("", self.quantize_check)
        
        self.include_lyrics_check = QCheckBox("Include lyric placeholders")
        options_layout.addRow("", self.include_lyrics_check)
        
        layout.addWidget(options_group)
        
        # === OUTPUT SECTION ===
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout(output_group)
        
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output location...")
        if self.midi_path:
            default_output = os.path.splitext(self.midi_path)[0] + ".musicxml"
            self.output_edit.setText(default_output)
        output_layout.addWidget(self.output_edit, 1)
        
        browse_btn = QPushButton("📁 Browse...")
        browse_btn.clicked.connect(self._on_browse)
        output_layout.addWidget(browse_btn)
        
        layout.addWidget(output_group)
        
        # === ACTION BUTTONS ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        export_btn = QPushButton("🎼 Export MusicXML")
        export_btn.setProperty("class", "primary")
        export_btn.setMinimumHeight(40)
        export_btn.setMinimumWidth(150)
        export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_browse(self):
        """Browse for output file location"""
        default_name = "transcription.musicxml"
        if self.midi_path:
            default_name = os.path.splitext(os.path.basename(self.midi_path))[0] + ".musicxml"
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save MusicXML File",
            default_name,
            "MusicXML Files (*.musicxml *.xml);;All Files (*.*)"
        )
        
        if path:
            self.output_edit.setText(path)
    
    def _on_export(self):
        """Execute the export"""
        output_path = self.output_edit.text().strip()
        
        if not output_path:
            QMessageBox.warning(self, "No Output Path", "Please select an output location.")
            return
        
        # Ensure extension
        if not output_path.endswith(('.musicxml', '.xml')):
            output_path += '.musicxml'
        
        try:
            # Get metadata
            title = self.title_edit.text().strip() or "Untitled"
            composer = self.composer_edit.text().strip() or "Unknown"
            tempo = self.tempo_spin.value()
            time_sig = self.time_sig_combo.currentText()
            key_sig = self.key_combo.currentText().split('/')[0].strip()
            quantize = self.quantize_check.isChecked()
            
            # Convert
            if self.midi_path and os.path.exists(self.midi_path):
                result = convert_midi_to_musicxml(
                    self.midi_path, 
                    output_path,
                    title=title,
                    composer=composer,
                    tempo=tempo,
                    time_signature=time_sig,
                    key=key_sig,
                    quantize=quantize
                )
            elif self.notes:
                result = convert_notes_to_musicxml(
                    self.notes,
                    output_path,
                    title=title,
                    composer=composer,
                    tempo=tempo,
                    time_signature=time_sig,
                    key=key_sig,
                    quantize=quantize
                )
            else:
                QMessageBox.warning(self, "No Data", "No MIDI file or notes to export.")
                return
            
            self.export_completed.emit(output_path)
            QMessageBox.information(
                self, 
                "Export Complete", 
                f"✅ MusicXML exported successfully!\n\n{output_path}"
            )
            self.accept()
            
        except ImportError:
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "music21 library is required for MusicXML export.\n\n"
                "Install it with:\n"
                "pip install music21"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Error: {str(e)}")


def convert_midi_to_musicxml(midi_path, output_path, **metadata):
    """
    Convert MIDI file to MusicXML format.
    
    Args:
        midi_path: Path to input MIDI file
        output_path: Path to output MusicXML file
        **metadata: title, composer, tempo, time_signature, key, quantize
    
    Returns:
        Path to output file
    """
    try:
        from music21 import converter, metadata as m21meta, tempo, meter, key as m21key
    except ImportError:
        # Fallback to pretty_midi + manual XML generation
        return _convert_midi_fallback(midi_path, output_path, **metadata)
    
    # Parse MIDI with music21
    score = converter.parse(midi_path)
    
    # Set metadata
    if not score.metadata:
        score.metadata = m21meta.Metadata()
    
    score.metadata.title = metadata.get('title', 'Untitled')
    score.metadata.composer = metadata.get('composer', 'Unknown')
    
    # Set tempo if specified
    if metadata.get('tempo'):
        # Remove existing tempo marks and add new one
        for el in score.flat.getElementsByClass(tempo.MetronomeMark):
            el.activeSite.remove(el)
        mm = tempo.MetronomeMark(number=metadata['tempo'])
        score.flat.getElementsByClass('Measure')[0].insert(0, mm) if score.flat.getElementsByClass('Measure') else None
    
    # Quantize if requested
    if metadata.get('quantize', True):
        score = score.quantize()
    
    # Write MusicXML
    score.write('musicxml', output_path)
    
    return output_path


def convert_notes_to_musicxml(notes, output_path, **metadata):
    """
    Convert note list to MusicXML format.
    
    Args:
        notes: List of {'pitch': int, 'start': float, 'duration': float}
        output_path: Path to output MusicXML file
        **metadata: title, composer, tempo, time_signature, key, quantize
    
    Returns:
        Path to output file
    """
    try:
        from music21 import stream, note as m21note, metadata as m21meta, tempo, meter
    except ImportError:
        # Fallback to manual XML generation
        return _convert_notes_fallback(notes, output_path, **metadata)
    
    # Create score
    score = stream.Score()
    
    # Set metadata
    score.metadata = m21meta.Metadata()
    score.metadata.title = metadata.get('title', 'Untitled')
    score.metadata.composer = metadata.get('composer', 'Unknown')
    
    # Create part
    part = stream.Part()
    
    # Add tempo
    if metadata.get('tempo'):
        mm = tempo.MetronomeMark(number=metadata['tempo'])
        part.insert(0, mm)
    
    # Add time signature
    time_sig = metadata.get('time_signature', '4/4')
    ts = meter.TimeSignature(time_sig)
    part.insert(0, ts)
    
    # Add notes sorted by start time
    sorted_notes = sorted(notes, key=lambda n: n['start'])
    
    for note_data in sorted_notes:
        midi_pitch = note_data['pitch']
        start_time = note_data['start']
        duration = note_data['duration']
        
        # Create note
        n = m21note.Note()
        n.pitch.midi = midi_pitch
        n.duration.quarterLength = duration  # Approximate - will be quantized
        n.offset = start_time
        
        part.append(n)
    
    score.append(part)
    
    # Quantize if requested
    if metadata.get('quantize', True):
        score = score.quantize()
    
    # Make measures
    score = score.makeMeasures()
    
    # Write MusicXML
    score.write('musicxml', output_path)
    
    return output_path


def _convert_midi_fallback(midi_path, output_path, **metadata):
    """Fallback conversion using pretty_midi when music21 is not available"""
    import pretty_midi
    
    pm = pretty_midi.PrettyMIDI(midi_path)
    
    # Extract notes
    notes = []
    for instrument in pm.instruments:
        for note in instrument.notes:
            notes.append({
                'pitch': note.pitch,
                'start': note.start,
                'duration': note.end - note.start
            })
    
    return _convert_notes_fallback(notes, output_path, **metadata)


def _convert_notes_fallback(notes, output_path, **metadata):
    """Generate basic MusicXML manually when music21 is not available"""
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    
    title = metadata.get('title', 'Untitled')
    composer = metadata.get('composer', 'Unknown')
    tempo = metadata.get('tempo', 120)
    time_sig = metadata.get('time_signature', '4/4')
    
    # Parse time signature
    beats, beat_type = time_sig.split('/')
    
    # Create MusicXML structure
    root = ET.Element('score-partwise', version='3.1')
    
    # Work info
    work = ET.SubElement(root, 'work')
    work_title = ET.SubElement(work, 'work-title')
    work_title.text = title
    
    # Identification
    identification = ET.SubElement(root, 'identification')
    creator = ET.SubElement(identification, 'creator', type='composer')
    creator.text = composer
    
    # Part list
    part_list = ET.SubElement(root, 'part-list')
    score_part = ET.SubElement(part_list, 'score-part', id='P1')
    part_name = ET.SubElement(score_part, 'part-name')
    part_name.text = 'Piano'
    
    # Part with measures
    part = ET.SubElement(root, 'part', id='P1')
    
    # Sort notes by start time
    sorted_notes = sorted(notes, key=lambda n: n['start'])
    
    # Calculate measures
    beat_duration = 60.0 / tempo  # seconds per beat
    measure_duration = int(beats) * beat_duration
    
    current_measure = 1
    measure = None
    last_measure_start = 0
    
    for note_data in sorted_notes:
        note_measure = int(note_data['start'] / measure_duration) + 1
        
        # Create new measure if needed
        if note_measure != current_measure or measure is None:
            measure = ET.SubElement(part, 'measure', number=str(note_measure))
            
            # Add attributes to first measure
            if note_measure == 1:
                attributes = ET.SubElement(measure, 'attributes')
                divisions = ET.SubElement(attributes, 'divisions')
                divisions.text = '1'  # Quarter note = 1 division
                
                time = ET.SubElement(attributes, 'time')
                beats_el = ET.SubElement(time, 'beats')
                beats_el.text = beats
                beat_type_el = ET.SubElement(time, 'beat-type')
                beat_type_el.text = beat_type
                
                # Add tempo
                direction = ET.SubElement(measure, 'direction', placement='above')
                direction_type = ET.SubElement(direction, 'direction-type')
                metronome = ET.SubElement(direction_type, 'metronome')
                beat_unit = ET.SubElement(metronome, 'beat-unit')
                beat_unit.text = 'quarter'
                per_minute = ET.SubElement(metronome, 'per-minute')
                per_minute.text = str(tempo)
            
            current_measure = note_measure
            last_measure_start = (note_measure - 1) * measure_duration
        
        # Add note
        note_el = ET.SubElement(measure, 'note')
        
        # Pitch
        pitch = ET.SubElement(note_el, 'pitch')
        step, octave, alter = midi_to_pitch_parts(note_data['pitch'])
        step_el = ET.SubElement(pitch, 'step')
        step_el.text = step
        if alter != 0:
            alter_el = ET.SubElement(pitch, 'alter')
            alter_el.text = str(alter)
        octave_el = ET.SubElement(pitch, 'octave')
        octave_el.text = str(octave)
        
        # Duration (in divisions - simplified to quarter beats)
        duration_el = ET.SubElement(note_el, 'duration')
        duration_el.text = str(max(1, int(note_data['duration'] / beat_duration)))
        
        # Type
        type_el = ET.SubElement(note_el, 'type')
        type_el.text = duration_to_type(note_data['duration'], beat_duration)
    
    # Write to file
    xml_str = ET.tostring(root, encoding='unicode')
    parsed = minidom.parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent='  ')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n')
        # Remove first line (duplicate xml declaration)
        lines = pretty_xml.split('\n')[1:]
        f.write('\n'.join(lines))
    
    return output_path


def midi_to_pitch_parts(midi_pitch):
    """Convert MIDI pitch to step, octave, alter"""
    note_names = ['C', 'C', 'D', 'D', 'E', 'F', 'F', 'G', 'G', 'A', 'A', 'B']
    alter_values = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]
    
    note_index = midi_pitch % 12
    octave = (midi_pitch // 12) - 1
    
    return note_names[note_index], octave, alter_values[note_index]


def duration_to_type(duration_seconds, beat_duration):
    """Convert duration in seconds to MusicXML note type"""
    quarters = duration_seconds / beat_duration
    
    if quarters >= 4:
        return 'whole'
    elif quarters >= 2:
        return 'half'
    elif quarters >= 1:
        return 'quarter'
    elif quarters >= 0.5:
        return 'eighth'
    elif quarters >= 0.25:
        return '16th'
    else:
        return '32nd'
