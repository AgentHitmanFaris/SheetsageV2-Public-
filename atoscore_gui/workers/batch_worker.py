"""
Batch Worker
Worker thread for sequential batch transcription
"""

from PySide6.QtCore import QThread, Signal
import os
import time


class BatchWorker(QThread):
    """Worker thread for batch transcription"""
    
    # Signals
    file_started = Signal(str, int, int)  # file_path, index, total
    file_progress = Signal(str, int)  # file_path, percent
    file_completed = Signal(str, dict)  # file_path, result
    file_error = Signal(str, str)  # file_path, error message
    batch_completed = Signal(list)  # list of results
    
    def __init__(self, files, settings):
        super().__init__()
        self.files = files
        self.settings = settings
        self.results = []
        self._cancelled = False
        self._paused = False
    
    def run(self):
        """Process all files sequentially"""
        total = len(self.files)
        
        for index, file_path in enumerate(self.files):
            if self._cancelled:
                break
            
            # Wait while paused
            while self._paused and not self._cancelled:
                time.sleep(0.1)
            
            if self._cancelled:
                break
            
            # Emit started signal
            self.file_started.emit(file_path, index, total)
            
            try:
                result = self._process_file(file_path, index, total)
                self.results.append({'file': file_path, 'success': True, 'result': result})
                self.file_completed.emit(file_path, result)
            except Exception as e:
                error_msg = str(e)
                self.results.append({'file': file_path, 'success': False, 'error': error_msg})
                self.file_error.emit(file_path, error_msg)
        
        self.batch_completed.emit(self.results)
    
    def _process_file(self, file_path, index, total):
        """Process a single file"""
        from workers.transcription_worker import TranscriptionWorker
        
        # Build config for this file
        config = {
            'audio_file': file_path,
            'mode': self.settings.get('mode', 'lead_sheet'),
            'separate_vocals': self.settings.get('separate_vocals', False),
            'generate_pdf': self.settings.get('generate_pdf', False),
            'synthesize': self.settings.get('synthesize', True),
        }
        
        # Create a worker for this file
        worker = TranscriptionWorker(config)
        
        # Track progress
        def on_progress(msg):
            pass  # Could log if needed
        
        def on_percent(pct):
            self.file_progress.emit(file_path, pct)
        
        worker.progress_update.connect(on_progress)
        worker.progress_percent.connect(on_percent)
        
        # Run synchronously (we're already in a thread)
        result = worker.run_sync()
        
        return result
    
    def pause(self):
        """Pause processing"""
        self._paused = True
    
    def resume(self):
        """Resume processing"""
        self._paused = False
    
    def cancel(self):
        """Cancel processing"""
        self._cancelled = True
        self._paused = False  # Unpause to allow thread to exit
