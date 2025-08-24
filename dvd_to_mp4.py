#!/usr/bin/env python3
"""
DVD to MP4 Converter
Automatically detects inserted DVDs and converts them to MP4 format.
"""

import os
import sys
import subprocess
import platform
import time
from pathlib import Path

class DVDConverter:
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.getcwd()
        self.system = platform.system()
        
    def find_dvd_drive(self):
        """Find the DVD drive path based on the operating system."""
        if self.system == "Darwin":  # macOS
            # Check common mount points
            volumes = Path("/Volumes")
            if volumes.exists():
                for volume in volumes.iterdir():
                    if volume.is_dir() and self.is_dvd_volume(volume):
                        return str(volume)
            
            # Also check /dev/disk* for raw DVD access
            try:
                result = subprocess.run(['diskutil', 'list'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'DVD' in line or 'CD' in line:
                        # Extract disk identifier
                        parts = line.split()
                        if parts and parts[0].startswith('/dev/'):
                            return parts[0]
            except:
                pass
                
        elif self.system == "Linux":
            # Common DVD device paths on Linux
            dvd_paths = ["/dev/dvd", "/dev/sr0", "/dev/cdrom"]
            for path in dvd_paths:
                if os.path.exists(path):
                    return path
                    
        elif self.system == "Windows":
            # Windows drive letters
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        # Check if it's a DVD
                        if self.is_dvd_volume(drive):
                            return drive
                    except:
                        continue
        
        return None
    
    def is_dvd_volume(self, path):
        """Check if the given path contains DVD structure."""
        dvd_indicators = ["VIDEO_TS", "AUDIO_TS", "video_ts", "audio_ts"]
        path_obj = Path(path)
        
        for indicator in dvd_indicators:
            if (path_obj / indicator).exists():
                return True
        return False
    
    def get_dvd_info(self, dvd_path):
        """Get DVD information including title and available streams using ffprobe."""
        # Determine the best input source for analysis
        analysis_input = dvd_path
        
        if self.is_dvd_volume(dvd_path):
            # For DVD volumes, analyze the largest VOB file to get stream info
            video_ts_path = os.path.join(dvd_path, "VIDEO_TS")
            if os.path.exists(video_ts_path):
                vob_files = []
                for file in sorted(os.listdir(video_ts_path)):
                    if file.startswith("VTS_01_") and file.endswith(".VOB") and not file.endswith("_0.VOB"):
                        vob_files.append(os.path.join(video_ts_path, file))
                
                if vob_files:
                    # Use the first (usually largest) VOB file for analysis
                    analysis_input = vob_files[0]
                    print(f"Analyzing DVD using: {os.path.basename(analysis_input)}")
        
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                analysis_input
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Get title
                title = data.get('format', {}).get('tags', {}).get('title', 'Unknown_DVD')
                if not title or title == 'Unknown_DVD':
                    # Try to get title from directory name
                    if self.is_dvd_volume(dvd_path):
                        title = os.path.basename(dvd_path)
                
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                title = title.replace(' ', '_') if title else "DVD_Conversion"
                
                # Get audio streams
                audio_streams = []
                video_streams = []
                subtitle_streams = []
                
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        language = stream.get('tags', {}).get('language', 'unknown')
                        codec = stream.get('codec_name', 'unknown')
                        channels = stream.get('channels', 0)
                        audio_streams.append({
                            'index': stream.get('index'),
                            'language': language,
                            'codec': codec,
                            'channels': channels,
                            'title': stream.get('tags', {}).get('title', f'Audio {len(audio_streams) + 1}')
                        })
                    elif stream.get('codec_type') == 'video':
                        video_streams.append({
                            'index': stream.get('index'),
                            'codec': stream.get('codec_name'),
                            'width': stream.get('width'),
                            'height': stream.get('height')
                        })
                    elif stream.get('codec_type') == 'subtitle':
                        language = stream.get('tags', {}).get('language', 'unknown')
                        subtitle_streams.append({
                            'index': stream.get('index'),
                            'language': language,
                            'codec': stream.get('codec_name'),
                            'title': stream.get('tags', {}).get('title', f'Subtitle {len(subtitle_streams) + 1}')
                        })
                
                return {
                    'title': title,
                    'audio_streams': audio_streams,
                    'video_streams': video_streams,
                    'subtitle_streams': subtitle_streams,
                    'vob_files_count': len(vob_files) if 'vob_files' in locals() else 1
                }
        except Exception as e:
            print(f"Error getting DVD info: {e}")
            pass
        
        return {
            'title': "DVD_Conversion",
            'audio_streams': [],
            'video_streams': [],
            'subtitle_streams': [],
            'vob_files_count': 0
        }
    
    def get_dvd_title(self, dvd_path):
        """Get the DVD title (backward compatibility)."""
        return self.get_dvd_info(dvd_path)['title']
    
    def convert_dvd_to_video(self, dvd_path, output_filename=None, output_format='mp4', audio_tracks='all', include_subtitles=True):
        """Convert DVD to MP4 using ffmpeg with multiple audio track support."""
        if not output_filename:
            title = self.get_dvd_title(dvd_path)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f"{title}_{timestamp}.{output_format}"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        print(f"Converting DVD from: {dvd_path}")
        print(f"Output file: {output_path}")
        
        # Get DVD information
        dvd_info = self.get_dvd_info(dvd_path)
        
        # Display VOB files information
        if dvd_info.get('vob_files_count', 0) > 1:
            print(f"\n📀 Found {dvd_info['vob_files_count']} VOB files to combine into single MP4")
        
        # Display available streams
        if dvd_info['audio_streams']:
            print(f"\n🔊 Found {len(dvd_info['audio_streams'])} audio track(s):")
            for i, stream in enumerate(dvd_info['audio_streams']):
                lang = stream['language']
                title = stream.get('title', f"Track {i+1}")
                channels = stream.get('channels', 'unknown')
                codec = stream.get('codec', 'unknown')
                print(f"  {i+1}. {title} ({lang}) - {codec}, {channels} channels")
        
        if dvd_info['subtitle_streams']:
            print(f"\n📝 Found {len(dvd_info['subtitle_streams'])} subtitle track(s):")
            for i, stream in enumerate(dvd_info['subtitle_streams']):
                lang = stream['language']
                title = stream.get('title', f"Subtitle {i+1}")
                codec = stream.get('codec', 'unknown')
                print(f"  {i+1}. {title} ({lang}) - {codec}")
        
        if dvd_info['video_streams']:
            print(f"\n🎥 Found {len(dvd_info['video_streams'])} video stream(s):")
            for i, stream in enumerate(dvd_info['video_streams']):
                codec = stream.get('codec', 'unknown')
                width = stream.get('width', 'unknown')
                height = stream.get('height', 'unknown')
                print(f"  {i+1}. {codec} - {width}x{height}")
        
        # Format-specific compression info
        format_info = {
            'mp4': "🗜️  HIGH COMPRESSION MP4: Targeting file size <200MB",
            '3gp': "📱 3GP FORMAT: Mobile-optimized, very small file size",
            'mkv': "🎬 MKV FORMAT: High quality with good compression",
            'webm': "🌐 WebM FORMAT: Web-optimized, excellent compression"
        }
        
        print(f"\n{format_info.get(output_format, '🔄 Converting to ' + output_format.upper())}")
        print("⚠️  This will take longer due to high compression settings")
        print("🔄 This may take a while depending on the DVD length...")
        
        # Determine the proper input format for DVD
        dvd_input = dvd_path
        concat_file = None
        
        if self.is_dvd_volume(dvd_path):
            # If it's a DVD volume, use the VIDEO_TS folder or concat protocol
            video_ts_path = os.path.join(dvd_path, "VIDEO_TS")
            if os.path.exists(video_ts_path):
                # Use concat protocol to combine all VOB files
                vob_files = []
                for file in sorted(os.listdir(video_ts_path)):
                    if file.startswith("VTS_01_") and file.endswith(".VOB") and not file.endswith("_0.VOB"):
                        vob_files.append(os.path.join(video_ts_path, file))
                
                if vob_files:
                    # Create a temporary concat file list
                    concat_file = os.path.join(self.output_dir, "temp_concat.txt")
                    with open(concat_file, 'w') as f:
                        for vob_file in vob_files:
                            f.write(f"file '{vob_file}'\n")
                    dvd_input = concat_file
                else:
                    # Fallback to direct VIDEO_TS path
                    dvd_input = video_ts_path
        
        # Build FFmpeg command with format-specific settings
        cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', dvd_input]
        
        # Format-specific video encoding settings
        if output_format == 'mp4':
            # MP4: Ultra high compression for <200MB
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'veryslow',
                '-crf', '30',              # Even higher compression for <200MB
                '-maxrate', '300k',        # Lower bitrate for <200MB target
                '-bufsize', '600k',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-movflags', '+faststart',
                '-vf', 'scale=640:480'     # Reduce resolution for smaller file
            ])
        elif output_format == '3gp':
            # 3GP: Mobile format, very small file size
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'veryslow',
                '-crf', '32',              # Very high compression
                '-maxrate', '200k',        # Very low bitrate
                '-bufsize', '400k',
                '-profile:v', 'baseline',
                '-level', '1.3',           # Lower level for mobile
                '-vf', 'scale=320:240'     # Small resolution for mobile
            ])
        elif output_format == 'mkv':
            # MKV: Good quality with efficient compression
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '26',              # Good quality/size balance
                '-maxrate', '500k',
                '-bufsize', '1000k',
                '-vf', 'scale=720:576'     # Keep original DVD resolution
            ])
        elif output_format == 'webm':
            # WebM: Web-optimized with VP9 codec
            cmd.extend([
                '-c:v', 'libvpx-vp9',
                '-crf', '32',              # High compression
                '-b:v', '300k',            # Target bitrate
                '-vf', 'scale=640:480'     # Web-friendly resolution
            ])
        else:
            # Default fallback to MP4 settings
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23'
            ])
        
        # Handle audio tracks
        if audio_tracks == 'all' and dvd_info['audio_streams']:
            # Include all audio tracks
            cmd.extend(['-map', '0:v:0'])  # Map first video stream
            for i, audio_stream in enumerate(dvd_info['audio_streams']):
                cmd.extend(['-map', f"0:a:{i}"])  # Map each audio stream
                cmd.extend([f'-c:a:{i}', 'aac'])   # Set codec for each audio stream
                # Format-specific audio bitrate
                audio_bitrate = {'mp4': '48k', '3gp': '32k', 'mkv': '128k', 'webm': '64k'}.get(output_format, '64k')
                cmd.extend([f'-b:a:{i}', audio_bitrate])
                # Add metadata for language
                if audio_stream['language'] != 'unknown':
                    cmd.extend([f'-metadata:s:a:{i}', f"language={audio_stream['language']}"])
                    cmd.extend([f'-metadata:s:a:{i}', f"title={audio_stream.get('title', f'Audio {i+1}')}"])
        else:
            # Default: just first audio track
            cmd.extend([
                '-c:a', 'aac',               # AAC audio codec
                '-b:a', {'mp4': '48k', '3gp': '32k', 'mkv': '128k', 'webm': '64k'}.get(output_format, '64k'),
            ])
        
        # Handle subtitles
        if include_subtitles and dvd_info['subtitle_streams']:
            for i, sub_stream in enumerate(dvd_info['subtitle_streams']):
                cmd.extend(['-map', f"0:s:{i}"])  # Map subtitle stream
                cmd.extend([f'-c:s:{i}', 'mov_text'])  # Use mov_text for MP4 compatibility
                if sub_stream['language'] != 'unknown':
                    cmd.extend([f'-metadata:s:s:{i}', f"language={sub_stream['language']}"])
                    cmd.extend([f'-metadata:s:s:{i}', f"title={sub_stream.get('title', f'Subtitle {i+1}')}"])
        
        cmd.extend([
            '-movflags', '+faststart',    # Optimize for streaming
            '-y',                        # Overwrite output file if exists
            output_path
        ])
        
        print(f"\nFFmpeg command: {' '.join(cmd[:10])}... (truncated)")
        if audio_tracks == 'all':
            print(f"Including all {len(dvd_info['audio_streams'])} audio tracks")
        if include_subtitles and dvd_info['subtitle_streams']:
            print(f"Including {len(dvd_info['subtitle_streams'])} subtitle tracks")
        
        try:
            # Run conversion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Show progress with better parsing
            duration = None
            for line in process.stdout:
                line = line.strip()
                
                # Extract duration from the first Duration line
                if 'Duration:' in line and duration is None:
                    try:
                        duration_str = line.split('Duration: ')[1].split(',')[0]
                        h, m, s = duration_str.split(':')
                        duration = int(h) * 3600 + int(m) * 60 + float(s)
                        print(f"Total duration: {duration_str}")
                    except:
                        pass
                
                # Show progress with percentage if we have duration
                if 'time=' in line:
                    try:
                        # Extract current time
                        time_part = line.split('time=')[1].split()[0]
                        h, m, s = time_part.split(':')
                        current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        
                        if duration and duration > 0:
                            percentage = (current_time / duration) * 100
                            print(f"\rProgress: {percentage:.1f}% - {line}", end='', flush=True)
                        else:
                            print(f"\rProgress: {line}", end='', flush=True)
                    except:
                        print(f"\rProgress: {line}", end='', flush=True)
            
            process.wait()
            
            if process.returncode == 0:
                print(f"\n✅ Conversion completed successfully!")
                print(f"Output file: {output_path}")
                # Clean up temporary concat file
                if 'concat_file' in locals() and os.path.exists(concat_file):
                    os.remove(concat_file)
                return output_path
            else:
                print(f"\n❌ Conversion failed with return code: {process.returncode}")
                # Clean up temporary concat file on failure too
                if 'concat_file' in locals() and os.path.exists(concat_file):
                    os.remove(concat_file)
                return None
                
        except FileNotFoundError:
            print("❌ Error: ffmpeg not found. Please install ffmpeg first.")
            print("Install instructions:")
            if self.system == "Darwin":
                print("  brew install ffmpeg")
            elif self.system == "Linux":
                print("  sudo apt-get install ffmpeg  # Ubuntu/Debian")
                print("  sudo yum install ffmpeg      # CentOS/RHEL")
            elif self.system == "Windows":
                print("  Download from: https://ffmpeg.org/download.html")
            return None
        except Exception as e:
            print(f"❌ Error during conversion: {e}")
            return None
    
    def wait_for_dvd(self):
        """Wait for a DVD to be inserted and return its path."""
        print("Waiting for DVD to be inserted...")
        print("Press Ctrl+C to cancel")
        
        try:
            while True:
                dvd_path = self.find_dvd_drive()
                if dvd_path:
                    print(f"📀 DVD detected at: {dvd_path}")
                    return dvd_path
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n🛑 Cancelled by user")
            return None
    
    def run(self, dvd_path=None):
        """Main conversion process."""
        print("🎬 DVD to MP4 Converter")
        print("=" * 30)
        
        if not dvd_path:
            dvd_path = self.wait_for_dvd()
            if not dvd_path:
                return
        
        # Convert the DVD
        output_file = self.convert_dvd_to_mp4(dvd_path)
        
        if output_file:
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"📁 File size: {file_size:.1f} MB")
            print(f"📍 Location: {output_file}")

def main():
    """Command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert DVD to MP4 with multiple audio track support")
    parser.add_argument("--dvd-path", help="Path to DVD (if not auto-detecting)")
    parser.add_argument("--output-dir", help="Output directory (default: current directory)")
    parser.add_argument("--filename", help="Output filename (default: auto-generated)")
    parser.add_argument("--format", choices=['mp4', '3gp', 'mkv', 'webm'], default='mp4',
                        help="Output format: mp4 (<200MB), 3gp (mobile), mkv (quality), webm (web) (default: mp4)")
    parser.add_argument("--audio-tracks", choices=['all', 'first'], default='all', 
                        help="Audio tracks to include: 'all' for all tracks, 'first' for first track only (default: all)")
    parser.add_argument("--no-subtitles", action='store_true', 
                        help="Exclude subtitle tracks from conversion")
    parser.add_argument("--analyze-only", action='store_true',
                        help="Only analyze DVD streams without converting")
    
    args = parser.parse_args()
    
    converter = DVDConverter(output_dir=args.output_dir)
    
    if args.dvd_path:
        if args.analyze_only:
            # Just analyze and display DVD information
            dvd_info = converter.get_dvd_info(args.dvd_path)
            print(f"\n📀 DVD Analysis: {dvd_info['title']}")
            print("=" * 50)
            
            # Show VOB file information
            if dvd_info.get('vob_files_count', 0) > 1:
                print(f"\n📀 VOB Files: {dvd_info['vob_files_count']} files will be combined into single {args.format.upper()}")
            elif dvd_info.get('vob_files_count', 0) == 1:
                print(f"\n📀 VOB Files: 1 file detected")
            else:
                print(f"\n📀 Source: Direct file input")
            
            if dvd_info['audio_streams']:
                print(f"\n🔊 Audio Tracks ({len(dvd_info['audio_streams'])}):")
                for i, stream in enumerate(dvd_info['audio_streams']):
                    lang = stream['language']
                    title = stream.get('title', f"Track {i+1}")
                    channels = stream.get('channels', 'unknown')
                    codec = stream.get('codec', 'unknown')
                    print(f"  {i+1}. {title} ({lang}) - {codec}, {channels} channels")
            
            if dvd_info['subtitle_streams']:
                print(f"\n📝 Subtitle Tracks ({len(dvd_info['subtitle_streams'])}):")
                for i, stream in enumerate(dvd_info['subtitle_streams']):
                    lang = stream['language']
                    title = stream.get('title', f"Subtitle {i+1}")
                    codec = stream.get('codec', 'unknown')
                    print(f"  {i+1}. {title} ({lang}) - {codec}")
            
            if dvd_info['video_streams']:
                print(f"\n🎥 Video Streams ({len(dvd_info['video_streams'])}):")
                for i, stream in enumerate(dvd_info['video_streams']):
                    codec = stream.get('codec', 'unknown')
                    width = stream.get('width', 'unknown')
                    height = stream.get('height', 'unknown')
                    print(f"  {i+1}. {codec} - {width}x{height}")
        else:
            # Convert with specified options
            converter.convert_dvd_to_video(
                args.dvd_path, 
                args.filename, 
                args.format,
                args.audio_tracks,
                not args.no_subtitles
            )
    else:
        converter.run()

if __name__ == "__main__":
    main()
