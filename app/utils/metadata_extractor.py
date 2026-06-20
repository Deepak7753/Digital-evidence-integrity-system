import os
import re
import struct
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

def extract_image_metadata(file_path: str) -> dict:
    metadata = {}
    try:
        with Image.open(file_path) as img:
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['format'] = img.format
            
            exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    # Convert bytes to string or readable format
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except Exception:
                            value = str(value)
                    
                    if tag_name in ['Make', 'Model', 'DateTime', 'DateTimeOriginal', 'GPSInfo']:
                        if tag_name == 'GPSInfo':
                            # Simplify GPS info display
                            metadata['gps_raw'] = str(value)
                        else:
                            metadata[tag_name.lower()] = str(value)
    except Exception as e:
        metadata['error'] = f"Failed to extract image EXIF: {str(e)}"
    return metadata

def extract_pdf_metadata(file_path: str) -> dict:
    metadata = {}
    try:
        # Simple PDF Info Dictionary scraper for basic author/date extraction
        with open(file_path, 'rb') as f:
            content = f.read(100 * 1024)  # Read first 100KB for info dict
            
        # Look for typical pdf patterns e.g., /Author (name) or /CreationDate (D:2026...)
        patterns = {
            'author': rb'\/Author\s*\(([^\)]+)\)',
            'creator': rb'\/Creator\s*\(([^\)]+)\)',
            'creation_date': rb'\/CreationDate\s*\(([^\)]+)\)',
            'mod_date': rb'\/ModDate\s*\(([^\)]+)\)',
            'title': rb'\/Title\s*\(([^\)]+)\)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                try:
                    metadata[key] = match.group(1).decode('utf-8', errors='ignore')
                except Exception:
                    metadata[key] = str(match.group(1))
                    
        # Check basic file attributes
        metadata['pages_estimate'] = content.count(b'/Page\r') + content.count(b'/Page\n') + content.count(b'/Page ')
    except Exception as e:
        metadata['error'] = f"Failed to parse document: {str(e)}"
    return metadata

def extract_wav_metadata(file_path: str) -> dict:
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            riff = f.read(12)
            if riff[:4] == b'RIFF' and riff[8:12] == b'WAVE':
                # Parse WAV chunks
                fmt_chunk = f.read(8)
                if fmt_chunk[:4] == b'fmt ':
                    fmt_size = struct.unpack('<I', fmt_chunk[4:8])[0]
                    fmt_data = f.read(fmt_size)
                    audio_format, channels, sample_rate, byte_rate, block_align, bits_per_sample = struct.unpack('<HHIIHH', fmt_data[:16])
                    
                    metadata['channels'] = channels
                    metadata['sample_rate'] = sample_rate
                    metadata['bits_per_sample'] = bits_per_sample
                    metadata['codec'] = 'PCM' if audio_format == 1 else f'Format-{audio_format}'
                    
                    # Find data chunk to calculate duration
                    while True:
                        chunk_header = f.read(8)
                        if not chunk_header or len(chunk_header) < 8:
                            break
                        chunk_name = chunk_header[:4]
                        chunk_size = struct.unpack('<I', chunk_header[4:8])[0]
                        if chunk_name == b'data':
                            duration = chunk_size / byte_rate
                            metadata['duration_seconds'] = round(duration, 2)
                            break
                        else:
                            f.seek(chunk_size, os.SEEK_CUR)  # skip chunk
    except Exception as e:
        metadata['error'] = f"Failed to extract WAV metadata: {str(e)}"
    return metadata

def extract_mp4_metadata(file_path: str) -> dict:
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            # Look for mvhd (Movie Header) atom in the MP4 file
            file_size = os.path.getsize(file_path)
            content = f.read(min(file_size, 500 * 1024))  # Read first 500KB
            
            mvhd_idx = content.find(b'mvhd')
            if mvhd_idx != -1:
                # mvhd structure: 4 bytes size, 4 bytes type, 1 byte version, 3 bytes flags,
                # then based on version:
                # version 0: 4B creation, 4B modification, 4B timescale, 4B duration
                # version 1: 8B creation, 8B modification, 4B timescale, 8B duration
                version = content[mvhd_idx + 4]
                if version == 0:
                    timescale = struct.unpack('>I', content[mvhd_idx + 16:mvhd_idx + 20])[0]
                    duration = struct.unpack('>I', content[mvhd_idx + 20:mvhd_idx + 24])[0]
                elif version == 1:
                    timescale = struct.unpack('>I', content[mvhd_idx + 24:mvhd_idx + 28])[0]
                    duration = struct.unpack('>Q', content[mvhd_idx + 28:mvhd_idx + 36])[0]
                else:
                    timescale = 0
                    duration = 0
                
                if timescale > 0:
                    metadata['duration_seconds'] = round(duration / timescale, 2)
                
            # Scan for resolution or codec markers if any
            if b'avc1' in content:
                metadata['codec'] = 'H.264 / AVC'
            elif b'hev1' in content or b'hvc1' in content:
                metadata['codec'] = 'H.265 / HEVC'
            elif b'mp4a' in content:
                metadata['codec'] = 'AAC / MP4 Audio'
    except Exception as e:
        metadata['error'] = f"Failed to extract MP4 metadata: {str(e)}"
    return metadata

def extract_metadata(file_path: str, category: str) -> dict:
    """
    Main metadata extraction dispatch method.
    """
    category = category.lower()
    if category == 'image':
        return extract_image_metadata(file_path)
    elif category == 'document' and file_path.lower().endswith('.pdf'):
        return extract_pdf_metadata(file_path)
    elif category == 'audio' and file_path.lower().endswith('.wav'):
        return extract_wav_metadata(file_path)
    elif category in ('video', 'movie') and file_path.lower().endswith('.mp4'):
        return extract_mp4_metadata(file_path)
    
    # Return generic info for others
    try:
        return {
            'file_size_bytes': os.path.getsize(file_path),
            'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception:
        return {}
