#!/usr/bin/env python3
"""
Web-based DVD to MP4 Converter
A Flask web application for converting DVDs to MP4 format with real-time progress tracking.
"""

import os
import sys
import json
import time
import threading
import subprocess
import platform
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from dvd_to_mp4 import DVDConverter

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dvd_converter_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for tracking conversion progress
conversion_status = {
    'active': False,
    'progress': 0,
    'status': 'idle',
    'message': '',
    'output_file': '',
    'error': ''
}

class WebDVDConverter(DVDConverter):
    """Extended DVD converter with web interface support and real-time progress."""
    
    def __init__(self, output_dir=None, socketio_instance=None):
        super().__init__(output_dir)
        self.socketio = socketio_instance
        self.conversion_active = False
    
    def emit_progress(self, data):
        """Emit progress updates via SocketIO."""
        if self.socketio:
            self.socketio.emit('conversion_progress', data)
    
    def find_all_dvd_drives(self):
        """Find all available DVD drives and their paths."""
        dvd_drives = []
        
        if self.system == "Darwin":  # macOS
            # Check /Volumes for mounted DVDs
            volumes = Path("/Volumes")
            if volumes.exists():
                for volume in volumes.iterdir():
                    if volume.is_dir() and self.is_dvd_volume(volume):
                        dvd_drives.append({
                            'path': str(volume),
                            'name': volume.name,
                            'type': 'mounted'
                        })
            
            # Check for unmounted DVD devices
            try:
                result = subprocess.run(['diskutil', 'list'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'DVD' in line or 'CD' in line:
                        parts = line.split()
                        if parts and parts[0].startswith('/dev/'):
                            dvd_drives.append({
                                'path': parts[0],
                                'name': f"DVD Drive ({parts[0]})",
                                'type': 'device'
                            })
            except:
                pass
                
        elif self.system == "Linux":
            # Common DVD device paths on Linux
            dvd_paths = ["/dev/dvd", "/dev/sr0", "/dev/cdrom"]
            for path in dvd_paths:
                if os.path.exists(path):
                    dvd_drives.append({
                        'path': path,
                        'name': f"DVD Drive ({path})",
                        'type': 'device'
                    })
            
            # Check /media and /mnt for mounted DVDs
            for mount_point in ["/media", "/mnt"]:
                if os.path.exists(mount_point):
                    for item in os.listdir(mount_point):
                        full_path = os.path.join(mount_point, item)
                        if os.path.isdir(full_path) and self.is_dvd_volume(full_path):
                            dvd_drives.append({
                                'path': full_path,
                                'name': item,
                                'type': 'mounted'
                            })
                            
        elif self.system == "Windows":
            # Windows drive letters
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        if self.is_dvd_volume(drive):
                            dvd_drives.append({
                                'path': drive,
                                'name': f"DVD Drive ({letter}:)",
                                'type': 'mounted'
                            })
                    except:
                        continue
        
        return dvd_drives
    
    def convert_dvd_to_video_web(self, dvd_path, output_filename, output_dir=None, output_format='mp4', audio_tracks='all', include_subtitles=True):
        """Convert DVD to MP4 with web progress tracking and multiple audio track support."""
        global conversion_status
        
        if not output_dir:
            output_dir = self.output_dir
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Update status
        conversion_status.update({
            'active': True,
            'progress': 0,
            'status': 'starting',
            'message': f'Starting conversion of {dvd_path}',
            'output_file': output_path,
            'error': ''
        })
        self.emit_progress(conversion_status)
        
        # Get DVD information
        dvd_info = self.get_dvd_info(dvd_path)
        
        # Update status with stream information
        audio_count = len(dvd_info['audio_streams'])
        subtitle_count = len(dvd_info['subtitle_streams'])
        conversion_status.update({
            'message': f'Found {audio_count} audio tracks and {subtitle_count} subtitle tracks'
        })
        self.emit_progress(conversion_status)
        
        # Determine the proper input format for DVD
        dvd_input = dvd_path
        concat_file = None
        
        if self.is_dvd_volume(dvd_path):
            video_ts_path = os.path.join(dvd_path, "VIDEO_TS")
            if os.path.exists(video_ts_path):
                # Use concat protocol to combine all VOB files
                vob_files = []
                for file in sorted(os.listdir(video_ts_path)):
                    if file.startswith("VTS_01_") and file.endswith(".VOB") and not file.endswith("_0.VOB"):
                        vob_files.append(os.path.join(video_ts_path, file))
                
                if vob_files:
                    # Create a temporary concat file list
                    concat_file = os.path.join(output_dir, "temp_concat.txt")
                    with open(concat_file, 'w') as f:
                        for vob_file in vob_files:
                            f.write(f"file '{vob_file}'\n")
                    dvd_input = concat_file
        
        # Build FFmpeg command for DVD conversion with multiple audio tracks
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', dvd_input,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
        ]
        
        # Handle audio tracks
        if audio_tracks == 'all' and dvd_info['audio_streams']:
            # Include all audio tracks
            cmd.extend(['-map', '0:v:0'])  # Map first video stream
            for i, audio_stream in enumerate(dvd_info['audio_streams']):
                cmd.extend(['-map', f"0:a:{i}"])  # Map each audio stream
                cmd.extend([f'-c:a:{i}', 'aac'])   # Set codec for each audio stream
                cmd.extend([f'-b:a:{i}', '128k'])  # Set bitrate for each audio stream
                # Add metadata for language
                if audio_stream['language'] != 'unknown':
                    cmd.extend([f'-metadata:s:a:{i}', f"language={audio_stream['language']}"])
                    cmd.extend([f'-metadata:s:a:{i}', f"title={audio_stream.get('title', f'Audio {i+1}')}"])
        else:
            # Default: just first audio track
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '128k',
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
            '-movflags', '+faststart',
            '-y',
            output_path
        ])
        
        try:
            # Run conversion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Track progress
            duration = None
            for line in process.stdout:
                line = line.strip()
                
                # Extract duration
                if 'Duration:' in line and duration is None:
                    try:
                        duration_str = line.split('Duration: ')[1].split(',')[0]
                        h, m, s = duration_str.split(':')
                        duration = int(h) * 3600 + int(m) * 60 + float(s)
                        
                        conversion_status.update({
                            'status': 'converting',
                            'message': f'Converting... Duration: {duration_str}'
                        })
                        self.emit_progress(conversion_status)
                    except:
                        pass
                
                # Update progress
                if 'time=' in line:
                    try:
                        time_part = line.split('time=')[1].split()[0]
                        h, m, s = time_part.split(':')
                        current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        
                        if duration and duration > 0:
                            percentage = min((current_time / duration) * 100, 100)
                            conversion_status.update({
                                'progress': round(percentage, 1),
                                'message': f'Converting... {percentage:.1f}% complete'
                            })
                        else:
                            conversion_status.update({
                                'message': f'Converting... Time: {time_part}'
                            })
                        
                        self.emit_progress(conversion_status)
                    except:
                        pass
            
            process.wait()
            
            # Clean up temporary concat file
            if concat_file and os.path.exists(concat_file):
                os.remove(concat_file)
            
            if process.returncode == 0:
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                conversion_status.update({
                    'active': False,
                    'progress': 100,
                    'status': 'completed',
                    'message': f'Conversion completed! File size: {file_size:.1f} MB',
                    'output_file': output_path
                })
                self.emit_progress(conversion_status)
                return True
            else:
                conversion_status.update({
                    'active': False,
                    'progress': 0,
                    'status': 'error',
                    'message': f'Conversion failed with return code: {process.returncode}',
                    'error': f'FFmpeg error code: {process.returncode}'
                })
                self.emit_progress(conversion_status)
                return False
                
        except Exception as e:
            conversion_status.update({
                'active': False,
                'progress': 0,
                'status': 'error',
                'message': f'Error during conversion: {str(e)}',
                'error': str(e)
            })
            self.emit_progress(conversion_status)
            return False

# Initialize converter
converter = WebDVDConverter(socketio_instance=socketio)

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')

@app.route('/api/detect_dvds')
def detect_dvds():
    """API endpoint to detect available DVDs."""
    try:
        dvd_drives = converter.find_all_dvd_drives()
        return jsonify({
            'success': True,
            'dvds': dvd_drives
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/analyze_dvd', methods=['POST'])
def analyze_dvd():
    """API endpoint to analyze DVD streams (audio, video, subtitles)."""
    try:
        data = request.get_json()
        dvd_path = data.get('dvd_path')
        
        if not dvd_path or not os.path.exists(dvd_path):
            return jsonify({
                'success': False,
                'error': 'Invalid DVD path'
            })
        
        # Get DVD information
        dvd_info = converter.get_dvd_info(dvd_path)
        
        return jsonify({
            'success': True,
            'dvd_info': dvd_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/start_conversion', methods=['POST'])
def start_conversion():
    """API endpoint to start DVD conversion."""
    global conversion_status
    
    if conversion_status['active']:
        return jsonify({
            'success': False,
            'error': 'Conversion already in progress'
        })
    
    data = request.get_json()
    dvd_path = data.get('dvd_path')
    output_filename = data.get('output_filename', 'converted_dvd')
    output_dir = data.get('output_dir', os.getcwd())
    output_format = data.get('output_format', 'mp4')
    audio_tracks = data.get('audio_tracks', 'all')  # 'all', 'first', or list of indices
    include_subtitles = data.get('include_subtitles', True)
    
    if not dvd_path:
        return jsonify({
            'success': False,
            'error': 'DVD path is required'
        })
    
    if not os.path.exists(dvd_path):
        return jsonify({
            'success': False,
            'error': f'DVD path does not exist: {dvd_path}'
        })
    
    # Ensure output filename has correct extension
    if not output_filename.endswith(f'.{output_format}'):
        output_filename += f'.{output_format}'
    
    # Start conversion in background thread
    def convert_thread():
        converter.convert_dvd_to_video_web(dvd_path, output_filename, output_dir, output_format, audio_tracks, include_subtitles)
    
    thread = threading.Thread(target=convert_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Conversion started'
    })

@app.route('/api/status')
def get_status():
    """API endpoint to get current conversion status."""
    return jsonify(conversion_status)

@app.route('/api/cancel_conversion', methods=['POST'])
def cancel_conversion():
    """API endpoint to cancel ongoing conversion."""
    global conversion_status
    
    # Note: This is a simple implementation. In production, you'd want to 
    # properly terminate the ffmpeg process
    conversion_status.update({
        'active': False,
        'progress': 0,
        'status': 'cancelled',
        'message': 'Conversion cancelled by user',
        'error': ''
    })
    
    return jsonify({
        'success': True,
        'message': 'Conversion cancelled'
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('conversion_progress', conversion_status)

@socketio.on('request_status')
def handle_status_request():
    """Handle status request from client."""
    emit('conversion_progress', conversion_status)

if __name__ == '__main__':
    print("🎬 DVD to MP4 Web Converter")
    print("=" * 40)
    print("Starting web server...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
