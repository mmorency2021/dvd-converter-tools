#!/bin/bash

# DVD to MP4 Web Converter Startup Script

echo "🎬 DVD to MP4 Web Converter"
echo "=========================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed. Installing with Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Homebrew not found. Please install ffmpeg manually:"
        echo "   Visit: https://ffmpeg.org/download.html"
        exit 1
    fi
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Make the script executable
chmod +x dvd_to_mp4.py
chmod +x web_dvd_converter.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting web server..."
echo "📱 Open your browser to: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

# Start the web application
python3 web_dvd_converter.py
