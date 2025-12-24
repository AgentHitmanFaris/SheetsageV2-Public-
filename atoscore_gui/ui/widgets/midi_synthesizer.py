"""
MIDI Synthesizer Module
Wraps FluidSynth for real-time MIDI playback
"""

import os
import sys
import time
import threading

class MidiSynthesizer:
    def __init__(self, soundfont_path=None):
        self.fs = None
        self.driver = None
        self.sf_id = -1
        self.is_ready = False
        
        # Try to find soundfont if not provided
        if not soundfont_path:
            soundfont_path = self._find_soundfont()
            
        self.soundfont_path = soundfont_path
        self._initialize()
        
    def _find_soundfont(self):
        """Locate default TimGM6mb.sf2 from pretty_midi"""
        possible_paths = [
            # Relative to current script
            os.path.join(os.path.dirname(__file__), '..', '..', 'SheetSage_Core', 'python_embeded', 'Lib', 'site-packages', 'pretty_midi', 'TimGM6mb.sf2'),
            # Standard install
            os.path.join(sys.prefix, 'Lib', 'site-packages', 'pretty_midi', 'TimGM6mb.sf2'),
            # Local fallback
            'TimGM6mb.sf2'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        return None

    def _initialize(self):
        """Initialize FluidSynth"""
        try:
            import fluidsynth
            
            self.fs = fluidsynth.Synth()
            
            # Configure to rely on programmatic events, not hardware MIDI
            # This setting prevents it from eagerly grabbing MIDI ports
            # self.fs.setting('midi.active', 0) # Some versions support this
            
            # Attempt drivers
            # 'wasapi' is often better on modern Windows 10/11
            # 'dsound' is older
            drivers = ['wasapi', 'dsound', 'portaudio', 'winmm']
            started = False
            
            for driver in drivers:
                try:
                    print(f"MidiSynthesizer: Attempting driver '{driver}'...")
                    # We intentionally leave midi_driver unspecified or try to disable it if possible
                    # but pyfluidsynth's start() is rigorous. 
                    # If it fails, we catch it.
                    self.fs.start(driver=driver)
                    started = True
                    print(f"MidiSynthesizer: Started successfully with '{driver}'")
                    break
                except Exception as e:
                    print(f"MidiSynthesizer: Driver '{driver}' failed: {e}")
            
            if not started:
                print("MidiSynthesizer: Failed to start any audio driver")
                self.fs = None
                return

            if self.soundfont_path and os.path.exists(self.soundfont_path):
                self.sf_id = self.fs.sfload(self.soundfont_path)
                self.fs.program_select(0, self.sf_id, 0, 0)
                self.is_ready = True
                print(f"MidiSynthesizer initialized with {self.soundfont_path}")
            else:
                print("MidiSynthesizer: SoundFont not found")
                
        except ImportError:
            print("MidiSynthesizer: fluidsynth not installed")
        except Exception as e:
            print(f"MidiSynthesizer init error: {e}")

    def note_on(self, channel, pitch, velocity):
        """Play a note"""
        if self.is_ready and self.fs:
            self.fs.noteon(channel, pitch, velocity)

    def note_off(self, channel, pitch):
        """Stop a note"""
        if self.is_ready and self.fs:
            self.fs.noteoff(channel, pitch)

    def all_notes_off(self):
        """Stop all notes"""
        if self.is_ready and self.fs:
            # CC 123 is All Notes Off
            for chan in range(16):
                self.fs.cc(chan, 123, 0)

    def set_instrument(self, channel, bank, preset):
        """Change instrument"""
        if self.is_ready and self.fs:
            self.fs.program_select(channel, self.sf_id, bank, preset)

    def close(self):
        """Cleanup"""
        if self.fs:
            self.fs.delete()
            self.fs = None
