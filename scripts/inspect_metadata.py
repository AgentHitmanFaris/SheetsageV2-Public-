
import os
import sys

try:
    import mutagen
    from mutagen.id3 import ID3
    print("Mutagen is installed. Inspecting ID3 tags...")
except ImportError:
    print("Mutagen is not installed. Trying to use standard libraries or ffmpeg if available.")
    mutagen = None

audio_path = r"D:\Download\Music\BABYMONSTER - PSYCHO MV.mp3"

if not os.path.exists(audio_path):
    print(f"File not found: {audio_path}")
    sys.exit(1)

if mutagen:
    try:
        audio = ID3(audio_path)
        print("\n--- ID3 Tags ---")
        for key, value in audio.items():
            print(f"{key}: {value}")
            # The error mentions 'process_comment', so let's look closely at COMM frames
            if key.startswith("COMM"):
                print(f"  -> Description: '{value.desc}'")
                print(f"  -> Text: '{value.text}'")
                print(f"  -> Lang: '{value.lang}'")
    except Exception as e:
        print(f"Error reading ID3 tags with mutagen: {e}")

# Check file header
try:
    with open(audio_path, "rb") as f:
        header = f.read(16)
        print("\n--- File Header ---")
        print(f"Hex: {header.hex()}")
        print(f"ASCII: {header}")
        
    if header.startswith(b'ID3'):
        print("-> Looks like valid ID3v2 container.")
    elif header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3') or header.startswith(b'\xff\xf2'):
        print("-> Looks like valid MPEG-1 Layer 3 (MP3) frame.")
    elif header[4:8] == b'ftyp':
        print("-> WARNING: This is an MP4/M4A file (ISO Base Media file), NOT an MP3!")
        print("   The file extension .mp3 is incorrect.")
except Exception as e:
    print(f"Error reading file header: {e}")
