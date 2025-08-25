#!/usr/bin/env python3
"""
Fixed DVD to MP4 Converter - Handles VOB files correctly
Converts each VOB file individually then concatenates the results
"""

import os
import subprocess
import argparse
import json
import tempfile
from datetime import datetime

class DVDConverterFixed:
    def __init__(self, output_dir="."):
        self.output_dir = output_dir
    
    def is_dvd_volume(self, path):
        """Check if the path is a DVD volume"""
        return os.path.exists(os.path.join(path, "VIDEO_TS"))
    
    def get_main_vob_files(self, dvd_path):
        """Get main VOB files (excluding menu/navigation files)"""
        vob_files = []
        
        if self.is_dvd_volume(dvd_path):
            video_ts_path = os.path.join(dvd_path, "VIDEO_TS")
            if os.path.exists(video_ts_path):
                # Find main VOB files (VTS_xx_1.VOB, VTS_xx_2.VOB, etc.)
                for file in sorted(os.listdir(video_ts_path)):
                    if (file.startswith("VTS_") and file.endswith(".VOB") and 
                        not file.endswith("_0.VOB")):  # Exclude menu files
                        vob_files.append(os.path.join(video_ts_path, file))
        
        return vob_files
    
    def convert_vob_to_mp4(self, vob_file, output_file, format_settings):
        """Convert a single VOB file to MP4"""
        cmd = ['ffmpeg', '-i', vob_file]
        cmd.extend(format_settings)
        cmd.extend([output_file, '-y'])
        
        print(f"Converting {os.path.basename(vob_file)}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def concatenate_mp4_files(self, mp4_files, output_file):
        """Concatenate multiple MP4 files"""
        # Create temporary concat file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for mp4_file in mp4_files:
                abs_path = os.path.abspath(mp4_file)
                f.write(f"file '{abs_path}'\n")
            concat_file = f.name
        
        try:
            cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file, 
                   '-c', 'copy', output_file, '-y']
            
            print("Concatenating MP4 files...")
            print(f"DEBUG: Concatenation command: {' '.join(cmd)}")
            print(f"DEBUG: Output file: {output_file}")
            print(f"DEBUG: Input files: {mp4_files}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ERROR: Concatenation failed with return code {result.returncode}")
                print(f"STDERR: {result.stderr}")
                print(f"STDOUT: {result.stdout}")
                return False
            
            print(f"SUCCESS: Concatenation completed. Output file: {output_file}")
            return True
        finally:
            os.unlink(concat_file)
    
    def get_format_settings(self, output_format):
        """Get format-specific encoding settings"""
        if output_format == 'mp4':
            return [
                '-c:v', 'libx264',
                '-preset', 'veryslow',
                '-crf', '30',
                '-maxrate', '300k',
                '-bufsize', '600k',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-movflags', '+faststart',
                '-vf', 'scale=640:480',
                '-c:a', 'aac',
                '-b:a', '48k'
            ]
        elif output_format == '3gp':
            return [
                '-c:v', 'libx264',
                '-preset', 'veryslow',
                '-crf', '32',
                '-maxrate', '200k',
                '-bufsize', '400k',
                '-profile:v', 'baseline',
                '-level', '1.3',
                '-vf', 'scale=320:240',
                '-c:a', 'aac',
                '-b:a', '32k'
            ]
        elif output_format == 'mkv':
            return [
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '26',
                '-maxrate', '500k',
                '-bufsize', '1000k',
                '-vf', 'scale=720:576',
                '-c:a', 'aac',
                '-b:a', '128k'
            ]
        elif output_format == 'webm':
            return [
                '-c:v', 'libvpx-vp9',
                '-crf', '32',
                '-b:v', '300k',
                '-vf', 'scale=640:480',
                '-c:a', 'aac',
                '-b:a', '64k'
            ]
        else:
            # Default MP4 settings
            return ['-c:v', 'libx264', '-c:a', 'aac', '-crf', '23']
    
    def convert_dvd_fixed(self, dvd_path, output_filename, output_format='mp4'):
        """Convert DVD using the fixed method: individual VOB conversion + concatenation"""
        
        # Get main VOB files
        vob_files = self.get_main_vob_files(dvd_path)
        
        if not vob_files:
            print("❌ No main VOB files found!")
            return False
        
        print(f"📀 Found {len(vob_files)} main VOB files:")
        for vob in vob_files:
            size_mb = os.path.getsize(vob) / (1024*1024)
            print(f"  • {os.path.basename(vob)} ({size_mb:.1f} MB)")
        
        # Get format settings
        format_settings = self.get_format_settings(output_format)
        
        # Convert each VOB to MP4
        temp_mp4_files = []
        try:
            for i, vob_file in enumerate(vob_files):
                temp_mp4 = f"temp_vob_{i+1}.mp4"
                temp_mp4_files.append(temp_mp4)
                
                if not self.convert_vob_to_mp4(vob_file, temp_mp4, format_settings):
                    print(f"❌ Failed to convert {os.path.basename(vob_file)}")
                    return False
            
            # Concatenate all MP4 files
            output_path = os.path.join(self.output_dir, output_filename)
            if not self.concatenate_mp4_files(temp_mp4_files, output_path):
                print("❌ Failed to concatenate MP4 files")
                return False
            
            print(f"✅ Conversion completed successfully!")
            print(f"Output file: {output_path}")
            
            # Show final file info
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024*1024)
                print(f"Final file size: {size_mb:.1f} MB")
                
                # Get duration
                try:
                    result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_format', 
                                           '-print_format', 'json', output_path], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        duration = float(data['format']['duration'])
                        minutes = int(duration // 60)
                        seconds = int(duration % 60)
                        print(f"Duration: {minutes}:{seconds:02d}")
                except:
                    pass
            
            return True
            
        finally:
            # Clean up temporary files
            for temp_file in temp_mp4_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

def main():
    parser = argparse.ArgumentParser(description='Fixed DVD to MP4 Converter')
    parser.add_argument('--dvd-path', required=True, help='Path to DVD or VIDEO_TS folder')
    parser.add_argument('--filename', default='dvd_conversion.mp4', help='Output filename')
    parser.add_argument('--format', choices=['mp4', '3gp', 'mkv', 'webm'], 
                       default='mp4', help='Output format')
    
    args = parser.parse_args()
    
    # Ensure filename has correct extension
    base_name = os.path.splitext(args.filename)[0]
    output_filename = f"{base_name}.{args.format}"
    
    converter = DVDConverterFixed()
    success = converter.convert_dvd_fixed(args.dvd_path, output_filename, args.format)
    
    if not success:
        exit(1)

if __name__ == "__main__":
    main()
