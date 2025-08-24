# 🎬 DVD Converter Tools

A comprehensive, professional-grade DVD conversion suite with both command-line and web interfaces. Convert DVDs to multiple formats with advanced compression, multi-language support, and real-time progress tracking.

## ✨ Features

### 🌐 **Web Interface**
- **Modern, responsive UI** with real-time progress tracking
- **Automatic DVD detection** - finds mounted DVDs instantly
- **Multiple output formats**: MP4, 3GP, MKV, WebM
- **Advanced compression options** with target file sizes
- **Multi-language audio support** with track selection
- **Real-time WebSocket updates** for conversion progress
- **Custom filename and directory selection**

### 💻 **Command Line Interface**
- **Flexible DVD input** - auto-detection or manual path
- **Multiple output formats** with format-specific optimization
- **Comprehensive DVD analysis** - audio tracks, subtitles, streams
- **Progress monitoring** with detailed statistics
- **Batch processing capabilities**

### 🎵 **Multi-Language Support**
- **Automatic detection** of all audio tracks and subtitles
- **Language metadata preservation** with proper tagging
- **Channel separation tools** for dual-language DVDs
- **Subtitle extraction and embedding**

### 🗜️ **Advanced Compression**
- **Format-specific optimization**:
  - **MP4**: Ultra-compressed (<200MB) with H.264
  - **3GP**: Mobile-optimized (80-120MB) 
  - **MKV**: High-quality with efficient compression
  - **WebM**: Web-optimized with VP9 codec
- **Intelligent bitrate control** with quality preservation
- **Resolution scaling** for optimal file sizes

## 🚀 Quick Start

### Web Interface (Recommended)
```bash
# Quick start script
./start_web_converter.sh

# Or manually
pip3 install -r requirements.txt
python3 web_dvd_converter.py
```

Open your browser to: **http://localhost:5000**

### Command Line
```bash
# Basic conversion (auto-detects DVD)
python3 dvd_to_mp4.py

# Specify format and compression
python3 dvd_to_mp4.py --format mp4 --filename "movie.mp4"

# Analyze DVD content first
python3 dvd_to_mp4.py --analyze-only
```

## 📋 Prerequisites

### Required Software
```bash
# macOS (using Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows - Download from https://ffmpeg.org/download.html
```

### Python Dependencies
```bash
pip3 install -r requirements.txt
```

**Dependencies include:**
- `Flask` - Web framework
- `Flask-SocketIO` - Real-time communication
- `psutil` - System monitoring

## 🎯 Usage Examples

### Web Interface Workflow
1. **🔍 Detect DVDs** - Automatically finds mounted DVDs
2. **📝 Set filename** - Choose your output filename
3. **🎬 Select format** - Pick from MP4, 3GP, MKV, WebM
4. **📁 Choose directory** - Set output location
5. **🔬 Analyze (optional)** - Preview audio/subtitle tracks
6. **⚙️ Configure options** - Select audio tracks and subtitles
7. **▶️ Start conversion** - Watch real-time progress

### Command Line Options
```bash
# Format selection
python3 dvd_to_mp4.py --format mp4|3gp|mkv|webm

# Custom paths
python3 dvd_to_mp4.py --dvd-path "/Volumes/DVD_NAME" --output-dir "/path/to/output"

# Analysis mode
python3 dvd_to_mp4.py --analyze-only --dvd-path "/Volumes/DVD_NAME"

# All audio tracks
python3 dvd_to_mp4.py --audio-tracks all --format mkv
```

## 🎵 Multi-Language Features

### Audio Track Handling
- **Automatic detection** of all available audio streams
- **Language identification** and metadata tagging
- **Multiple track preservation** in supported formats
- **Channel separation** for dual-language DVDs

### Subtitle Support
- **Automatic subtitle detection** and extraction
- **Language metadata** preservation
- **Multiple subtitle track** embedding
- **Format compatibility** optimization

### Dual-Language DVD Support
For DVDs with languages on separate channels:
```bash
# Creates version with separated left/right channels
ffmpeg -i input.mp4 -filter_complex "[0:a]channelsplit" output_dual.mp4
```

## 📊 Output Formats & Compression

| Format | Target Size | Quality | Use Case |
|--------|-------------|---------|----------|
| **MP4** | <200MB | High | General purpose, streaming |
| **3GP** | 80-120MB | Mobile | Phones, limited storage |
| **MKV** | 400-600MB | Highest | Archival, quality priority |
| **WebM** | 200-300MB | Web-optimized | Web streaming, modern browsers |

### Compression Settings
- **MP4**: H.264, CRF 30, 640x480, baseline profile
- **3GP**: H.264, CRF 32, 320x240, mobile-optimized  
- **MKV**: H.264, CRF 26, 720x576, high quality
- **WebM**: VP9, CRF 32, 640x480, web-optimized

## 🔧 Advanced Features

### DVD Analysis
```bash
# Comprehensive DVD analysis
python3 dvd_to_mp4.py --analyze-only --dvd-path "/path/to/dvd"
```

**Analysis includes:**
- VOB file inventory and sizes
- Video stream information (codec, resolution, framerate)
- Audio track details (codec, channels, language)
- Subtitle track enumeration
- Total duration calculation

### Progress Tracking
- **Real-time percentage** completion
- **Time estimates** (elapsed/remaining)
- **Bitrate monitoring** and statistics
- **Error detection** and reporting

### Quality Control
- **Automatic quality optimization** per format
- **Bitrate limiting** for target file sizes
- **Resolution scaling** with aspect ratio preservation
- **Fast start optimization** for streaming

## 🌐 Web Interface Features

### Dashboard
- **DVD Detection Panel** - Auto-discovers mounted DVDs
- **Configuration Panel** - Format, filename, directory selection
- **Analysis Panel** - Preview DVD content and tracks
- **Progress Panel** - Real-time conversion monitoring

### Real-Time Updates
- **WebSocket communication** for instant updates
- **Progress bars** with percentage completion
- **Status messages** and error notifications
- **Conversion statistics** and time estimates

### Mobile Support
- **Responsive design** works on all devices
- **Touch-friendly interface** for tablets/phones
- **Optimized layouts** for different screen sizes

## 🛠️ Troubleshooting

### Common Issues

**"ffmpeg not found"**
```bash
# Verify installation
ffmpeg -version

# Install if missing
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Linux
```

**"No DVD detected"**
- Ensure DVD is properly mounted
- Check `/Volumes/` (macOS) or `/media/` (Linux)
- Use `--dvd-path` to specify manually

**"Conversion failed"**
- Check DVD is not copy-protected
- Verify sufficient disk space
- Try different output format

**"Port 5000 in use"**
```bash
# Kill existing processes
lsof -ti:5000 | xargs kill -9

# Or use different port
python3 web_dvd_converter.py --port 8080
```

### Performance Optimization
- **SSD storage** recommended for faster I/O
- **Sufficient RAM** (4GB+ recommended)
- **Close other applications** during conversion
- **Use wired connection** for network storage

## 📁 Project Structure

```
dvd-converter-tools/
├── dvd_to_mp4.py              # Core conversion script
├── web_dvd_converter.py       # Flask web application
├── templates/
│   └── index.html            # Web interface template
├── requirements.txt          # Python dependencies
├── start_web_converter.sh    # Quick start script
├── README.md                # This file
└── temp_concat.txt          # Temporary VOB list (auto-generated)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FFmpeg** - The backbone of video conversion
- **Flask** - Web framework powering the interface
- **Socket.IO** - Real-time communication
- **Bootstrap** - UI components and styling

## 🔗 Links

- **Repository**: https://github.com/mmorency2021/dvd-converter-tools
- **Issues**: https://github.com/mmorency2021/dvd-converter-tools/issues
- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html

---

**Made with ❤️ for preserving your DVD collection in the digital age**