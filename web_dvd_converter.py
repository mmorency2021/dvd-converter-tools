#!/usr/bin/env python3
"""
Web DVD Converter - Fixed Version
Uses the corrected VOB conversion method for proper 34+ minute conversions
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
from dvd_to_mp4 import DVDConverterFixed

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dvd_converter_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global conversion status
conversion_status = {
    'active': False,
    'progress': 0,
    'status': 'idle',
    'message': '',
    'output_file': '',
    'error': ''
}

class WebDVDConverterFixed(DVDConverterFixed):
    """Extended DVD converter with web interface support using fixed conversion method."""
    
    def __init__(self, output_dir=None, socketio_instance=None):
        super().__init__(output_dir or ".")
        self.socketio = socketio_instance
    
    def emit_progress(self, status):
        """Emit progress update via WebSocket"""
        if self.socketio:
            self.socketio.emit('conversion_progress', status)
    
    def detect_dvd_drives(self):
        """Detect mounted DVD drives"""
        dvd_drives = []
        
        if platform.system() == "Darwin":  # macOS
            volumes_path = "/Volumes"
            if os.path.exists(volumes_path):
                for item in os.listdir(volumes_path):
                    volume_path = os.path.join(volumes_path, item)
                    if os.path.isdir(volume_path) and self.is_dvd_volume(volume_path):
                        dvd_drives.append({
                            'path': volume_path,
                            'name': item,
                            'type': 'DVD'
                        })
        
        elif platform.system() == "Windows":
            import string
            for letter in string.ascii_uppercase:
                drive_path = f"{letter}:\\\\"
                if os.path.exists(drive_path) and self.is_dvd_volume(drive_path):
                    dvd_drives.append({
                        'path': drive_path,
                        'name': f"Drive {letter}:",
                        'type': 'DVD'
                    })
        
        elif platform.system() == "Linux":
            media_paths = ["/media", "/mnt"]
            for media_path in media_paths:
                if os.path.exists(media_path):
                    for item in os.listdir(media_path):
                        mount_path = os.path.join(media_path, item)
                        if os.path.isdir(mount_path) and self.is_dvd_volume(mount_path):
                            dvd_drives.append({
                                'path': mount_path,
                                'name': item,
                                'type': 'DVD'
                            })
        
        return dvd_drives
    
    def convert_dvd_web(self, dvd_path, output_filename, output_dir=None, output_format='mp4'):
        """Convert DVD using the fixed method with web progress tracking"""
        global conversion_status
        
        if not output_dir:
            output_dir = self.output_dir
        
        # Ensure filename has correct extension
        base_name = os.path.splitext(output_filename)[0]
        output_filename = f"{base_name}.{output_format}"
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"DEBUG: Web converter paths:")
        print(f"  output_dir: '{output_dir}'")
        print(f"  output_filename: '{output_filename}'")
        print(f"  output_path: '{output_path}'")
        print(f"  absolute output_path: '{os.path.abspath(output_path)}'")
        print(f"  output_dir exists: {os.path.exists(output_dir)}")
        print(f"  output_dir writable: {os.access(output_dir, os.W_OK)}")
        
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
        
        try:
            # Get VOB files
            vob_files = self.get_main_vob_files(dvd_path)
            
            if not vob_files:
                conversion_status.update({
                    'active': False,
                    'status': 'error',
                    'error': 'No main VOB files found!'
                })
                self.emit_progress(conversion_status)
                return False
            
            conversion_status.update({
                'progress': 10,
                'message': f'Found {len(vob_files)} VOB files to convert'
            })
            self.emit_progress(conversion_status)
            
            # Get format settings
            format_settings = self.get_format_settings(output_format)
            
            # Convert each VOB file
            temp_mp4_files = []
            total_vobs = len(vob_files)
            
            for i, vob_file in enumerate(vob_files):
                temp_mp4 = f"temp_vob_{i+1}.mp4"
                temp_mp4_files.append(temp_mp4)
                
                conversion_status.update({
                    'progress': 20 + (i * 60 // total_vobs),
                    'message': f'Converting {os.path.basename(vob_file)} ({i+1}/{total_vobs})'
                })
                self.emit_progress(conversion_status)
                
                if not self.convert_vob_to_mp4(vob_file, temp_mp4, format_settings):
                    conversion_status.update({
                        'active': False,
                        'status': 'error',
                        'error': f'Failed to convert {os.path.basename(vob_file)}'
                    })
                    self.emit_progress(conversion_status)
                    return False
            
            # Concatenate MP4 files
            conversion_status.update({
                'progress': 85,
                'message': 'Combining converted files...'
            })
            self.emit_progress(conversion_status)
            
            print(f"DEBUG: About to concatenate:")
            print(f"  current working directory: {os.getcwd()}")
            print(f"  temp_mp4_files: {temp_mp4_files}")
            print(f"  output_path: {output_path}")
            print(f"  output_path absolute: {os.path.abspath(output_path)}")
            for i, temp_file in enumerate(temp_mp4_files):
                exists = os.path.exists(temp_file)
                size = os.path.getsize(temp_file) if exists else 0
                abs_temp = os.path.abspath(temp_file)
                print(f"  temp_file_{i+1}: {temp_file} (exists: {exists}, size: {size})")
                print(f"    absolute: {abs_temp} (exists: {os.path.exists(abs_temp)})")
            
            # Convert all paths to absolute to avoid working directory issues
            abs_temp_files = [os.path.abspath(f) for f in temp_mp4_files]
            abs_output_path = os.path.abspath(output_path)
            
            print(f"DEBUG: Using absolute paths for concatenation:")
            print(f"  abs_temp_files: {abs_temp_files}")
            print(f"  abs_output_path: {abs_output_path}")
            
            # GUARANTEED FIX: Use subprocess directly to avoid any context issues
            import tempfile
            import subprocess
            
            # Create concat file with absolute paths
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for abs_temp_file in abs_temp_files:
                    f.write(f"file '{abs_temp_file}'\n")
                concat_file = f.name
            
            try:
                print(f"DEBUG: DIRECT concatenation using subprocess...")
                cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file, 
                       '-c', 'copy', abs_output_path, '-y']
                print(f"DEBUG: Command: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    print(f"SUCCESS: Direct concatenation completed!")
                    concatenation_success = True
                else:
                    print(f"ERROR: Direct concatenation failed: {result.stderr}")
                    concatenation_success = False
            finally:
                os.unlink(concat_file)
            
            if not concatenation_success:
                conversion_status.update({
                    'active': False,
                    'status': 'error',
                    'error': 'Failed to combine MP4 files'
                })
                self.emit_progress(conversion_status)
                return False
            
            # Success
            conversion_status.update({
                'active': False,
                'progress': 100,
                'status': 'completed',
                'message': f'Conversion completed successfully! Output: {output_filename}'
            })
            self.emit_progress(conversion_status)
            
            # Clean up temporary files
            for temp_file in temp_mp4_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            return True
            
        except Exception as e:
            conversion_status.update({
                'active': False,
                'status': 'error',
                'error': f'Conversion failed: {str(e)}'
            })
            self.emit_progress(conversion_status)
            
            # Clean up temporary files
            for temp_file in temp_mp4_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            return False

# Create converter instance
converter = WebDVDConverterFixed(socketio_instance=socketio)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/detect_dvds')
def detect_dvds():
    """Detect available DVD drives"""
    try:
        dvd_drives = converter.detect_dvd_drives()
        return jsonify({'success': True, 'drives': dvd_drives})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/start_conversion', methods=['POST'])
def start_conversion():
    """Start DVD conversion"""
    global conversion_status
    
    if conversion_status['active']:
        return jsonify({'success': False, 'error': 'Conversion already in progress'})
    
    data = request.get_json()
    print(f"DEBUG: Received data: {data}")
    dvd_path = data.get('dvdPath')
    output_filename = data.get('outputFilename', 'converted_dvd.mp4')
    output_dir = data.get('outputDirectory', '.')
    output_format = data.get('outputFormat', 'mp4')
    
    # Handle paths that include /VIDEO_TS
    if dvd_path and dvd_path.endswith('/VIDEO_TS'):
        dvd_path = dvd_path[:-10]  # Remove /VIDEO_TS from the end
        print(f"DEBUG: Adjusted DVD Path (removed /VIDEO_TS): '{dvd_path}'")
    
    print(f"DEBUG: DVD Path: '{dvd_path}'")
    print(f"DEBUG: Output Filename: '{output_filename}'")
    
    if not dvd_path:
        return jsonify({'success': False, 'error': 'DVD path is required'})
    
    # Start conversion in background thread
    def conversion_thread():
        converter.convert_dvd_web(dvd_path, output_filename, output_dir, output_format)
    
    thread = threading.Thread(target=conversion_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Conversion started'})

@app.route('/api/conversion_status')
def get_conversion_status():
    """Get current conversion status"""
    return jsonify(conversion_status)

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('conversion_progress', conversion_status)

if __name__ == '__main__':
    print("🌐 Starting Fixed DVD Converter Web Interface...")
    print("📱 Open your browser to: http://localhost:5000")
    print("✨ Now with corrected 34+ minute DVD conversion!")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
