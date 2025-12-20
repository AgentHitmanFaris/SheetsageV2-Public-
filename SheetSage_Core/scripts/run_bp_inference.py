
import argparse
import sys
import os
import logging
import json

# Force UTF-8 for stdout/stderr to prevent charmap errors on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# Set up environment BEFORE imports
# Point to local cache directory
local_cache = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".sheetsage"))
os.environ["SHEETSAGE_CACHE_DIR"] = local_cache
os.environ["BASIC_PITCH_USE_ONNX"] = "1" 
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Allow TensorFlow/ONNX to see the GPU
# os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  <-- REMOVED to enable GPU


# Patch os.add_dll_directory to prevent fluidsynth error on Windows
# Some library versions try to add C:\tools\fluidsynth\bin which might not exist
if os.name == 'nt':
    original_add_dll_directory = os.add_dll_directory
    def patched_add_dll_directory(path):
        if not os.path.exists(path):
            return None # Suppress error
        return original_add_dll_directory(path)
    os.add_dll_directory = patched_add_dll_directory

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging to output to stdout in a format we can parse or just read
logging.basicConfig(level=logging.INFO, format='%(message)s')

from sheetsage.basic_pitch_transcription import transcribe_basic_pitch

def main():
    parser = argparse.ArgumentParser(description='Run Basic Pitch Transcription')
    parser.add_argument('--audio_path', required=True)
    parser.add_argument('--output_midi_path', required=True)
    parser.add_argument('--segment_start_hint', type=float, default=None)
    parser.add_argument('--segment_end_hint', type=float, default=None)
    parser.add_argument('--measures_per_chunk', type=int, default=8)
    parser.add_argument('--beats_per_measure_hint', type=int, default=None) # Corrected name
    parser.add_argument('--beats_per_minute_hint', type=int, default=None)
    parser.add_argument('--onset_threshold', type=float, default=0.5)
    parser.add_argument('--frame_threshold', type=float, default=0.3)
    parser.add_argument('--min_note_length', type=int, default=58)
    parser.add_argument('--skip_pdf', action='store_true', help='Skip PDF generation')
    
    args = parser.parse_args()

    print(f"STATUS: Starting Inference Process for {os.path.basename(args.audio_path)}")

    def callback(msg):
        # Print with special prefix for Gradio to catch
        print(f"STATUS: {msg}")
        sys.stdout.flush()

    try:
        results = transcribe_basic_pitch(
            audio_path=args.audio_path,
            output_midi_path=args.output_midi_path,
            segment_start_hint=args.segment_start_hint,
            segment_end_hint=args.segment_end_hint,
            measures_per_chunk=args.measures_per_chunk,
            beats_per_measure=args.beats_per_measure_hint,
            beats_per_minute_hint=args.beats_per_minute_hint,
            onset_threshold=args.onset_threshold,
            frame_threshold=args.frame_threshold,
            min_note_length=args.min_note_length,
            skip_pdf_generation=args.skip_pdf,
            status_callback=callback
        )
        # Print results as JSON on the last line
        print("JSON_RESULT:" + json.dumps(results))
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
