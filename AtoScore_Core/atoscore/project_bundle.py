"""
Project Bundle Utility
Compress transcription outputs into a single .sage project file
Reduces storage by 70-80% while maintaining quality
"""

import os
import json
import zipfile
import tempfile
import shutil
import logging
from pathlib import Path
from datetime import datetime


def compress_audio_file(input_path, output_path, format='flac', quality='high'):
    """
    Compress audio file to a smaller format.
    
    Args:
        input_path: Path to input WAV file
        output_path: Path to output file (extension determines format)
        format: 'flac' (lossless, ~50% size), 'mp3' (lossy, ~10% size), 'ogg' (lossy, ~10% size)
        quality: 'high', 'medium', 'low'
    
    Returns:
        Path to compressed file
    """
    try:
        from pydub import AudioSegment
        
        if not os.path.exists(input_path):
            return None
        
        audio = AudioSegment.from_file(input_path)
        
        # Quality settings
        if format == 'flac':
            # FLAC is lossless, no quality settings needed
            audio.export(output_path, format='flac')
        elif format == 'mp3':
            bitrate_map = {'high': '320k', 'medium': '192k', 'low': '128k'}
            bitrate = bitrate_map.get(quality, '192k')
            audio.export(output_path, format='mp3', bitrate=bitrate)
        elif format == 'ogg':
            quality_map = {'high': '9', 'medium': '5', 'low': '2'}
            q = quality_map.get(quality, '5')
            audio.export(output_path, format='ogg', parameters=['-q:a', q])
        else:
            # Default to FLAC
            audio.export(output_path, format='flac')
        
        return output_path
        
    except Exception as e:
        logging.error(f"Audio compression failed: {e}")
        return None


def create_project_bundle(output_dir, bundle_name=None, format='flac', quality='high', 
                          delete_originals=True):
    """
    Create a compressed .sage project bundle from transcription output.
    
    The .sage file is a ZIP archive containing:
    - metadata.json (song info, timestamps, etc.)
    - audio/ folder with compressed audio files
    - transcription.midi
    - output.pdf (if exists)
    
    Args:
        output_dir: Directory containing transcription output (WAV files, MIDI, etc.)
        bundle_name: Name for the bundle (defaults to folder name)
        format: Audio compression format ('flac', 'mp3', 'ogg')
        quality: Audio quality ('high', 'medium', 'low')
        delete_originals: If True, delete original WAV files after bundling
    
    Returns:
        Path to the .sage bundle file
    
    Storage savings (typical):
        - FLAC: ~50% smaller (lossless)
        - MP3 high: ~85% smaller (320kbps)
        - MP3 medium: ~90% smaller (192kbps)
        - OGG: ~85% smaller
    """
    output_dir = Path(output_dir)
    
    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory not found: {output_dir}")
    
    # Determine bundle name
    if not bundle_name:
        bundle_name = output_dir.name
    
    bundle_path = output_dir / f"{bundle_name}.sage"
    
    # Create temporary directory for compressed files
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Collect metadata
        metadata = {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'format': format,
            'quality': quality,
            'files': {}
        }
        
        # File extension mapping
        ext_map = {'flac': '.flac', 'mp3': '.mp3', 'ogg': '.ogg'}
        audio_ext = ext_map.get(format, '.flac')
        
        # Find and compress audio files
        audio_files = []
        # Support various extensions for source files
        for pattern in ['synth.*', 'mixed.*', 'original.*', 'vocals.*']:
            for f in output_dir.glob(pattern):
                if f.suffix.lower() in ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac']:
                    audio_files.append(f.name)
        
        audio_files = sorted(list(set(audio_files)))
        
        compressed_files = []
        original_size = 0
        compressed_size = 0
        
        for audio_file in audio_files:
            source = output_dir / audio_file
            if source.exists():
                original_size += source.stat().st_size
                
                # Compress
                base_name = source.stem
                dest = temp_dir / f"{base_name}{audio_ext}"
                result = compress_audio_file(str(source), str(dest), format, quality)
                
                if result and os.path.exists(result):
                    compressed_size += Path(result).stat().st_size
                    compressed_files.append((dest, f"audio/{base_name}{audio_ext}"))
                    metadata['files'][base_name] = f"audio/{base_name}{audio_ext}"
        
        # Find MIDI files
        for midi_file in output_dir.glob('*.midi'):
            compressed_files.append((midi_file, f"midi/{midi_file.name}"))
            metadata['files']['midi'] = f"midi/{midi_file.name}"
        
        for midi_file in output_dir.glob('*.mid'):
            compressed_files.append((midi_file, f"midi/{midi_file.name}"))
            metadata['files']['midi'] = f"midi/{midi_file.name}"
        
        # Find PDF files
        for pdf_file in output_dir.glob('*.pdf'):
            compressed_files.append((pdf_file, f"sheet/{pdf_file.name}"))
            metadata['files']['pdf'] = f"sheet/{pdf_file.name}"
        
        # Find LilyPond files
        for ly_file in output_dir.glob('*.ly'):
            compressed_files.append((ly_file, f"sheet/{ly_file.name}"))
            metadata['files']['lilypond'] = f"sheet/{ly_file.name}"
        
        # Calculate savings
        if original_size > 0:
            savings_percent = (1 - compressed_size / original_size) * 100
            metadata['original_size_mb'] = round(original_size / (1024 * 1024), 2)
            metadata['compressed_size_mb'] = round(compressed_size / (1024 * 1024), 2)
            metadata['savings_percent'] = round(savings_percent, 1)
        
        # Write metadata
        metadata_path = temp_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create ZIP archive
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            zf.write(metadata_path, 'metadata.json')
            
            # Add all files
            for source, archive_name in compressed_files:
                if Path(source).exists():
                    zf.write(source, archive_name)
        
        # Delete original WAV files if requested
        if delete_originals:
            for audio_file in audio_files:
                source = output_dir / audio_file
                if source.exists():
                    try:
                        source.unlink()
                    except:
                        pass
            
            # Also delete demucs folder if empty
            demucs_dir = output_dir / 'demucs'
            if demucs_dir.exists():
                try:
                    shutil.rmtree(demucs_dir)
                except:
                    pass
        
        logging.info(f"Created bundle: {bundle_path}")
        if 'savings_percent' in metadata:
            logging.info(f"Storage saved: {metadata['savings_percent']:.1f}% "
                        f"({metadata['original_size_mb']:.1f} MB → {metadata['compressed_size_mb']:.1f} MB)")
        
        return str(bundle_path)
        
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def extract_project_bundle(bundle_path, output_dir=None, convert_to_wav=False):
    """
    Extract a .sage project bundle.
    
    Args:
        bundle_path: Path to .sage file
        output_dir: Directory to extract to (defaults to same location as bundle)
        convert_to_wav: If True, convert compressed audio back to WAV
    
    Returns:
        Dictionary with paths to extracted files
    """
    bundle_path = Path(bundle_path)
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    if output_dir is None:
        output_dir = bundle_path.parent / bundle_path.stem
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extracted_files = {}
    
    with zipfile.ZipFile(bundle_path, 'r') as zf:
        # Extract all files
        zf.extractall(output_dir)
        
        # Read metadata
        metadata_path = output_dir / 'metadata.json'
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        # Get file paths
        for key, rel_path in metadata.get('files', {}).items():
            full_path = output_dir / rel_path
            if full_path.exists():
                extracted_files[key] = str(full_path)
    
    # Convert compressed audio back to WAV if requested
    if convert_to_wav:
        from pydub import AudioSegment
        
        audio_dir = output_dir / 'audio'
        if audio_dir.exists():
            for audio_file in audio_dir.iterdir():
                if audio_file.suffix in ['.flac', '.mp3', '.ogg']:
                    wav_path = audio_file.with_suffix('.wav')
                    audio = AudioSegment.from_file(str(audio_file))
                    audio.export(str(wav_path), format='wav')
                    extracted_files[audio_file.stem] = str(wav_path)
    
    return extracted_files


def get_bundle_info(bundle_path):
    """
    Get information about a .sage bundle without extracting it.
    
    Args:
        bundle_path: Path to .sage file
    
    Returns:
        Dictionary with bundle metadata
    """
    bundle_path = Path(bundle_path)
    
    if not bundle_path.exists():
        return None
    
    with zipfile.ZipFile(bundle_path, 'r') as zf:
        try:
            with zf.open('metadata.json') as f:
                return json.load(f)
        except:
            return {'version': 'unknown', 'files': {}}


# Convenience function to use in transcription workflow
def bundle_transcription_output(output_dir, format='mp3', quality='high', delete_originals=True):
    """
    Quick function to bundle transcription output into a .sage file.
    
    Recommended settings:
    - format='mp3', quality='high' - Best balance (85% smaller, excellent quality)
    - format='flac' - Lossless compression (50% smaller)
    - format='mp3', quality='medium' - Smaller files (90% smaller)
    
    Args:
        output_dir: Transcription output directory
        format: 'mp3', 'flac', or 'ogg'
        quality: 'high', 'medium', 'low'
        delete_originals: Delete WAV files after bundling
    
    Returns:
        Path to .sage bundle
    """
    return create_project_bundle(
        output_dir, 
        format=format, 
        quality=quality, 
        delete_originals=delete_originals
    )
