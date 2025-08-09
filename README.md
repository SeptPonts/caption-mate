# Caption-Mate

A powerful CLI tool for automatically searching and downloading subtitles for video files stored on NAS (Network Attached Storage) devices.

## Features

- **NAS Integration**: Connect to your NAS via SMB/CIFS protocol
- **Directory Browsing**: List and explore NAS directories with `ls` and `tree` commands
- **Video Scanning**: Automatically find video files in specified directories
- **Subtitle Search**: Search subtitles using OpenSubtitles API with multiple matching strategies:
  - File hash matching (most accurate)
  - Filename + filesize matching
  - Title-based fuzzy matching
- **Batch Processing**: Download subtitles for entire video libraries
- **Smart Filtering**: Skip videos that already have subtitles
- **Multi-language Support**: Download subtitles in multiple languages simultaneously
- **Progress Tracking**: Beautiful progress bars and status indicators

## Installation

### Prerequisites

- Python 3.11 or higher
- uv (recommended) or pip
- FFmpeg (for video metadata analysis)

### Install with uv

```bash
git clone https://github.com/yourusername/caption-mate.git
cd caption-mate
make install
```

### Install with pip

```bash
git clone https://github.com/yourusername/caption-mate.git
cd caption-mate
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
uv run caption-mate config init
```

This will interactively set up:
- OpenSubtitles API credentials
- NAS connection details (host, username, password)
- Preferred subtitle languages
- Download preferences

### 2. Test NAS Connection

```bash
uv run caption-mate nas test
```

### 3. Browse Your NAS

```bash
# List shares
uv run caption-mate nas ls /

# Browse a directory
uv run caption-mate nas ls /Movies

# Show directory tree
uv run caption-mate nas tree /Movies --depth 3
```

### 4. Scan for Videos

```bash
# Scan for video files
uv run caption-mate nas scan /Movies

# Scan with custom extensions
uv run caption-mate nas scan /Movies --extensions "mp4,mkv,avi"
```

### 5. Download Subtitles

```bash
# Auto mode: scan and download subtitles for all videos
uv run caption-mate auto /Movies

# Dry run to preview what would be processed
uv run caption-mate auto /Movies --dry-run

# Download for specific video
uv run caption-mate subtitles download /Movies/example.mp4

# Batch download for directory
uv run caption-mate subtitles batch /Movies
```

## Commands Reference

### Configuration Commands

```bash
caption-mate config init          # Interactive setup
caption-mate config show          # Show current configuration
caption-mate config set nas.host 192.168.1.100  # Set specific values
caption-mate config path          # Show config file location
```

### NAS Commands

```bash
caption-mate nas test             # Test connection
caption-mate nas ls [path]        # List directory contents
caption-mate nas tree [path]      # Show directory tree
caption-mate nas scan [path]      # Scan for video files
```

### Subtitle Commands

```bash
caption-mate subtitles search "Movie Name"  # Search by name
caption-mate subtitles download /path/video.mp4  # Download for single video
caption-mate subtitles batch /path/         # Batch download
```

### Auto Mode

```bash
caption-mate auto /path/          # Automatically process directory
caption-mate auto /path/ --dry-run # Preview what would be processed
```

## Configuration

Configuration is stored in `~/.caption-mate/config.yaml`:

```yaml
opensubtitles:
  api_key: "your_api_key"
  user_agent: "caption-mate-v1.0"
  username: "optional_username"
  password: "optional_password"

nas:
  protocol: "smb"
  host: "192.168.1.100"
  port: 445
  username: "your_nas_user"
  password: "your_nas_password"
  domain: "WORKGROUP"

subtitles:
  languages: ["zh-cn", "en"]
  formats: ["srt", "ass"]
  output_dir: null  # Same as video directory
  naming_pattern: "{filename}.{lang}.{ext}"

scanning:
  video_extensions: [".mp4", ".mkv", ".avi", ".mov", ".wmv"]
  recursive: true
  skip_existing: true
  cache_duration: 3600
```

## OpenSubtitles API Setup

1. Create an account at [OpenSubtitles.com](https://www.opensubtitles.com/)
2. Go to your profile and create an API key in the "API Consumers" section
3. Use the API key in your configuration

## Examples

### Example 1: Process Movie Collection

```bash
# Set up configuration
uv run caption-mate config init

# Test connection and browse
uv run caption-mate nas test
uv run caption-mate nas ls /

# Process entire movie collection
uv run caption-mate auto /Movies --recursive
```

### Example 2: Selective Processing

```bash
# Scan specific directory
uv run caption-mate nas scan /TV-Shows/Season-1

# Download only English subtitles
uv run caption-mate subtitles batch /TV-Shows/Season-1 -l en

# Search for specific movie
uv run caption-mate subtitles search "The Matrix 1999"
```

### Example 3: Dry Run and Verification

```bash
# Preview what would be processed
uv run caption-mate auto /Movies --dry-run

# Check existing subtitles
uv run caption-mate nas ls /Movies -l  # Show detailed file info
```

## Troubleshooting

### Connection Issues

- Ensure your NAS allows SMB connections
- Check firewall settings on both client and NAS
- Verify username/password and domain settings
- Try connecting to NAS IP address instead of hostname

### API Issues

- Verify your OpenSubtitles API key is correct and active
- Check if you've exceeded rate limits (wait and retry)
- Ensure internet connectivity

### Video File Issues

- Make sure FFmpeg is installed for video metadata analysis
- Check that video file extensions are in the configured list
- Verify file permissions on the NAS

## Development

```bash
git clone https://github.com/yourusername/caption-mate.git
cd caption-mate
make install
make test
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
