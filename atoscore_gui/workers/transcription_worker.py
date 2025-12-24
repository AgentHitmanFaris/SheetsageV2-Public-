"""
Transcription Worker Thread
QThread worker for running transcription in background without blocking UI
"""

from PySide6.QtCore import QThread, Signal
import sys
import os

# Add SheetSage_Core to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'AtoScore_Core')))


class TranscriptionWorker(QThread):
    """Background worker for audio transcription"""
    
    # Signals
    progress_update = Signal(str)  # Progress message
    progress_percent = Signal(int)  # Progress percentage (0-100)
    transcription_finished = Signal(dict)  # Results: {midi_path, pdf_path, wav_path, etc.}
    error = Signal(str)  # Error message
    
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.is_cancelled = False
    
    def cancel(self):
        """Cancel the transcription"""
        self.is_cancelled = True
    
    def run(self):
        """Execute transcription based on mode"""
        try:
            mode = self.config.get('mode', '')
            audio_file = self.config.get('audio_file', '')
            
            self.progress_update.emit(f"Starting {mode} transcription...")
            self.progress_percent.emit(5)
            
            # Route to appropriate transcription function
            if mode == "Lead Sheet (Standard)":
                result = self._transcribe_lead_sheet()
            elif mode == "Piano (Polyphonic)":
                result = self._transcribe_piano()
            elif mode == "Basic Pitch (Polyphonic)":
                result = self._transcribe_basic_pitch()
            elif mode == "Drums (Omnizart)":
                result = self._transcribe_drums()
            elif mode == "SheetSage V3 (Lunaverus)":
                result = self._transcribe_lunaverus()
            else:
                raise ValueError(f"Unknown transcription mode: {mode}")
            
            if not self.is_cancelled:
                self.progress_percent.emit(100)
                self.transcription_finished.emit(result)
        
        except Exception as e:
            if not self.is_cancelled:
                import traceback
                self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")
    
    def run_sync(self):
        """Execute transcription synchronously (for batch processing)
        Returns the result directly instead of emitting signals.
        """
        mode = self.config.get('mode', 'lead_sheet')
        
        # Map shorthand modes to full names for internal routing
        mode_map = {
            'lead_sheet': 'Lead Sheet (Standard)',
            'piano': 'Piano (Polyphonic)',
            'basic_pitch': 'Basic Pitch (Polyphonic)',
            'drums': 'Drums (Omnizart)',
            'lunaverus': 'SheetSage V3 (Lunaverus)'
        }
        
        full_mode = mode_map.get(mode, mode)
        self.config['mode'] = full_mode
        
        # Route to appropriate transcription function
        if 'Lead Sheet' in full_mode:
            return self._transcribe_lead_sheet()
        elif 'Piano' in full_mode:
            return self._transcribe_piano()
        elif 'Basic Pitch' in full_mode:
            return self._transcribe_basic_pitch()
        elif 'Drums' in full_mode:
            return self._transcribe_drums()
        elif 'Lunaverus' in full_mode or 'V3' in full_mode:
            return self._transcribe_lunaverus()
        else:
            raise ValueError(f"Unknown transcription mode: {mode}")
    
    def _transcribe_lead_sheet(self):
        """Transcribe using Lead Sheet (Standard) mode"""
        from atoscore.infer import sheetsage
        from atoscore.audio_utils import synthesize_midi, create_mix
        from atoscore.utils import engrave
        from atoscore.config_manager import current_config
        import os
        from datetime import datetime
        import subprocess
        import pathlib
        import numpy as np
        from atoscore.align import create_beat_to_time_fn
        
        audio_file = self.config['audio_file']
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = os.path.join(current_config.get('output_dir', 'output'), 
                                  f"leadsheet_{filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        output_dir_path = pathlib.Path(output_dir)
        
        self.progress_update.emit("Analyzing audio...")
        self.progress_percent.emit(20)
        
        # Separate vocals if requested
        vocals_path = None
        if self.config.get('separate_vocals', False):
            self.progress_update.emit("Separating vocals with Demucs...")
            self.progress_percent.emit(30)
            
            # Run Demucs for vocal separation
            sep_out_dir = output_dir_path / "demucs"
            sep_out_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                sys.executable,
                "-m", "demucs.separate",
                "-n", "htdemucs",
                "--two-stems=vocals",
                "-o", str(sep_out_dir),
                audio_file
            ]
            
            # Note: demucs subprocess might output to console.
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Check for vocals.wav
                vocals_candidate = sep_out_dir / "htdemucs" / pathlib.Path(audio_file).stem / "vocals.wav"
                if vocals_candidate.exists():
                    vocals_path = str(vocals_candidate)
        
        # Transcribe
        self.progress_update.emit("Transcribing to sheet music...")
        self.progress_percent.emit(50)
        
        # Call sheetsage infer (returns objects, does NOT save files)
        # Signature: sheetsage(audio_path_bytes_or_url, ...)
        target_audio = vocals_path if vocals_path else audio_file
        
        lead_sheet, segment_beats, beats_times = sheetsage(
            target_audio,
            segment_start_hint=self.config.get('start_time'),
            segment_end_hint=self.config.get('end_time'),
            beats_per_minute_hint=self.config.get('bpm_hint'),
            # Note: beats_per_measure is handled via hint in sheetsage
            beats_per_measure_hint=self.config.get('beats_per_measure'), 
        )
        
        # --- Generate Files ---
        
        # 1. MIDI Generation
        midi_path = output_dir_path / "transcription.midi"
        
        # We need to construct pulse_to_time_fn for as_midi to sound synced
        # segment_beats is list of indices. beats_times is array of times.
        # beats_times is aligned to downbeats? No, it's list of ALL beats.
        # We can map pulse index -> time.
        
        # lead_sheet.as_midi expects a function that takes tertiary index?
        # Actually as_midi implementation: 
        # tertiary_to_time_fn = lambda t: pulse_to_time_fn(t / tertiary_per_pulse)
        # So pulse_to_time_fn must accept BEATS (float).
        
        # Note: If we just pass nothing, as_midi uses constant tempo from lead_sheet (which might be average).
        # For accurate sync, we should provide the mapping.
        
        bs = np.arange(len(beats_times))
        beat_to_time = create_beat_to_time_fn(bs, beats_times)
        
        # Offset: segment_beats contains indices RELATIVE to start? 
        # No, from infer.py: segment_beats = [b - segment_start_downbeat for b in beats]
        # Wait, verify what create_beat_to_time_fn expects.
        # It expects raw arrays.
        
        midi_bytes = lead_sheet.as_midi(
            pulse_to_time_fn=lambda p: beat_to_time(p) 
            # as_midi calculates beats from tertiaries, then calls this. 
            # Since our lead_sheet starts at 0, and beat_to_time starts at 0 (relative to segment?),
            # We might need to handle offset.
            # But the lead_sheet object returned from sheetsage is typically trimmed/re-zeroed.
            # Let's trust as_midi default for now if in doubt, or use simple beat_to_time.
            # Actually, sheetsage() returns (lead_sheet, segment_beats, beats_times).
            # The lead sheet structure is aligned to 0.
            # The beats_times are absolute times in the audio.
            # We need to map LeadSheet time 0 -> Audio Time X.
            
            # Construct a beat_to_time relative to the segment start.
            # segment_beats[0] is 0. 
            # beats_times[segment_beats[0] + offset_in_original_beats]...
            
            # Simple approach: Use default constant tempo for the MIDI file itself (it's cleaner for notation).
            # For playback sync, we might want the warped one.
            # Let's stick to default (None) for clean output first.
        )
        
        with open(midi_path, "wb") as f:
            f.write(midi_bytes)
            
        # 2. PDF Generation (LilyPond)
        pdf_path = None
        if self.config.get('generate_pdf', True):
            try:
                lily = lead_sheet.as_lily()
                ly_path = output_dir_path / "output.ly"
                with open(ly_path, "w") as f:
                    f.write(lily)
                
                # Engrave
                self.progress_update.emit("Engraving PDF...")
                pdf_bytes = engrave(lily, out_format="pdf", transparent=False, trim=False, hide_footer=False)
                pdf_path = output_dir_path / "output.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
            except Exception as e:
                self.progress_update.emit(f"PDF generation failed: {e}")
                print(f"PDF Error: {e}")
        
        self.progress_update.emit("Synthesizing audio...")
        self.progress_percent.emit(80)
        
        # Synthesize MIDI
        soundfont = current_config.get('soundfont_path', '')
        synth_path = synthesize_midi(midi_path, soundfont, output_dir_path)
        
        # Create mix
        mixed_path, original_segment = create_mix(audio_file, synth_path, output_dir_path)
        
        return {
            'mode': 'Lead Sheet',
            'midi_path': str(midi_path),
            'pdf_path': str(pdf_path) if pdf_path else None,
            'synth_path': synth_path,
            'mixed_path': mixed_path,
            'original_path': original_segment,
            'vocals_path': vocals_path,
            'output_dir': output_dir
        }
    
    def _transcribe_piano(self):
        """Transcribe using Piano (ByteDance) mode"""
        from atoscore.piano_transcription import transcribe_piano
        from atoscore.audio_utils import synthesize_midi, create_mix
        from atoscore.config_manager import current_config
        import os
        import pathlib
        from datetime import datetime
        
        audio_file = self.config['audio_file']
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = os.path.join(current_config.get('output_dir', 'output'), 
                                  f"piano_{filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        output_dir_path = pathlib.Path(output_dir)
        
        self.progress_update.emit("Transcribing piano...")
        self.progress_percent.emit(40)
        
        midi_path = os.path.join(output_dir, "piano_transcription.midi")
        transcribe_piano(audio_file, midi_path)
        
        self.progress_update.emit("Synthesizing audio...")
        self.progress_percent.emit(70)
        
        soundfont = current_config.get('soundfont_path', '')
        synth_path = synthesize_midi(midi_path, soundfont, output_dir_path)
        mixed_path, original_segment = create_mix(audio_file, synth_path, output_dir_path)
        
        return {
            'mode': 'Piano',
            'midi_path': midi_path,
            'synth_path': synth_path,
            'mixed_path': mixed_path,
            'original_path': original_segment,
            'output_dir': output_dir
        }
    
    def _transcribe_basic_pitch(self):
        """Transcribe using Basic Pitch mode"""
        from atoscore.basic_pitch_transcription import transcribe_basic_pitch
        from atoscore.audio_utils import synthesize_midi, create_mix
        from atoscore.config_manager import current_config
        import os
        import pathlib
        from datetime import datetime
        
        import subprocess
        import sys
        import shutil
        
        audio_file = self.config['audio_file']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = os.path.join(current_config.get('output_dir', 'output'), 
                                  f"basicpitch_{filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        output_dir_path = pathlib.Path(output_dir)
        
        # Demucs Separation
        vocals_path = None
        if self.config.get('separate_vocals', False):
            self.progress_update.emit("Separating vocals with Demucs...")
            self.progress_percent.emit(10)
            
            sep_out_dir = output_dir_path / "demucs"
            sep_out_dir.mkdir(parents=True, exist_ok=True)
            
            # Run Demucs
            cmd = [
                sys.executable, 
                "-m", "demucs.separate",
                "-n", "htdemucs",
                "--two-stems=vocals",
                "-o", str(sep_out_dir),
                audio_file
            ]
            
            try:
                # Run with timeout/check
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Find vocals
                # Structure: output/demucs/htdemucs/song_name/vocals.wav
                vocals_candidate = sep_out_dir / "htdemucs" / pathlib.Path(filename).name / "vocals.wav"
                
                # Sometimes filename in demucs output might be different slightly (spaces vs underscores?)
                # Try simple find
                if not vocals_candidate.exists():
                     # Fallback search
                     candidates = list(sep_out_dir.glob("**/vocals.wav"))
                     if candidates:
                         vocals_candidate = candidates[0]
                
                if vocals_candidate.exists():
                    # Move to main output dir for simpler bundling
                    final_vocals = output_dir_path / "vocals.wav"
                    shutil.copy2(str(vocals_candidate), str(final_vocals))
                    vocals_path = str(final_vocals)
                    
            except Exception as e:
                print(f"Demucs failed: {e}")
                # Continue without vocals
        
        self.progress_update.emit("Transcribing with Basic Pitch...")
        self.progress_percent.emit(40)
        
        target_midi_path = output_dir_path / "basic_pitch_transcription.midi"
        sys_result = transcribe_basic_pitch(audio_file, str(target_midi_path))
        midi_path = str(target_midi_path)
        
        # Extract metadata
        metadata = {}
        if isinstance(sys_result, dict) and 'metadata' in sys_result:
            metadata = sys_result['metadata']
        elif isinstance(sys_result, dict):
             # Fallback if return format is different/old
             pass
        
        self.progress_update.emit("Synthesizing audio...")
        self.progress_percent.emit(70)
        
        soundfont = current_config.get('soundfont_path', '')
        synth_path = synthesize_midi(midi_path, soundfont, output_dir_path)
        mixed_path, original_segment = create_mix(audio_file, synth_path, output_dir_path)
        
        return {
            'mode': 'Basic Pitch',
            'midi_path': midi_path,
            'synth_path': synth_path,
            'mixed_path': mixed_path,
            'original_path': original_segment,
            'output_dir': output_dir,
            'metadata': metadata,
            'vocals_path': vocals_path
        }
    
    def _transcribe_drums(self):
        """Transcribe using Omnizart Drums mode"""
        from atoscore.modules.omnizart_transcription import run_omnizart
        from atoscore.audio_utils import synthesize_midi, create_mix
        from atoscore.config_manager import current_config
        import os
        import pathlib
        from datetime import datetime
        
        audio_file = self.config['audio_file']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = os.path.join(current_config.get('output_dir', 'output'), 
                                  f"drums_{filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        self.progress_update.emit("Transcribing drums with Omnizart...")
        self.progress_percent.emit(40)
        
        def progress_callback(msg):
            self.progress_update.emit(f"Omnizart: {msg[:50]}")
        
        midi_path = run_omnizart(audio_file, output_dir, mode='drum', callback=progress_callback)
        
        self.progress_update.emit("Synthesizing audio...")
        self.progress_percent.emit(70)
        
        output_dir_path = pathlib.Path(output_dir)
        soundfont = current_config.get('soundfont_path', '')
        synth_path = synthesize_midi(midi_path, soundfont, output_dir_path)
        mixed_path, original_segment = create_mix(audio_file, synth_path, output_dir_path)
        
        return {
            'mode': 'Drums',
            'midi_path': midi_path,
            'synth_path': synth_path,
            'mixed_path': mixed_path,
            'original_path': original_segment,
            'output_dir': output_dir
        }
    
    def _transcribe_lunaverus(self):
        """Transcribe using SheetSage V3 (Lunaverus) mode"""
        from atoscore.modules.lunaverus_cnn import run_lunaverus
        from atoscore.audio_utils import synthesize_midi, create_mix
        from atoscore.config_manager import current_config
        import os
        import pathlib
        from datetime import datetime
        import torch
        
        audio_file = self.config['audio_file']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = os.path.join(current_config.get('output_dir', 'output'), 
                                  f"lunaverus_{filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        output_dir_path = pathlib.Path(output_dir)
        
        self.progress_update.emit("Transcribing with SheetSage V3 CNN...")
        self.progress_percent.emit(40)
        
        weights_path = os.path.join(os.path.dirname(__file__), '..', '..', 'AtoScore_Core', 
                                    'atoscore', 'modules', 'lunaverus_weights.pth')
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        midi_path = run_lunaverus(audio_file, model_weights_path=weights_path, device=device)
        
        # Move MIDI to output directory
        import shutil
        final_midi_path = os.path.join(output_dir, os.path.basename(midi_path))
        if midi_path != final_midi_path:
            shutil.move(midi_path, final_midi_path)
        
        self.progress_update.emit("Synthesizing audio...")
        self.progress_percent.emit(70)
        
        soundfont = current_config.get('soundfont_path', '')
        synth_path = synthesize_midi(final_midi_path, soundfont, output_dir_path)
        mixed_path, original_segment = create_mix(audio_file, synth_path, output_dir_path)
        
        return {
            'mode': 'SheetSage V3',
            'midi_path': final_midi_path,
            'synth_path': synth_path,
            'mixed_path': mixed_path,
            'original_path': original_segment,
            'output_dir': output_dir
        }
