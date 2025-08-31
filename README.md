# Caption-Mate

[English](README.md) | [中文](README_zh.md)

A powerful CLI tool for intelligent subtitle management on NAS devices, featuring AI-powered semantic matching and multi-source subtitle integration.

## Features

- **🤖 AI-Powered Matching**: Smart semantic matching using DeepSeek/OpenAI for accurate subtitle-to-video pairing
- **📁 NAS Integration**: Connect to your NAS via SMB/CIFS protocol for seamless file management
- **🔍 Dual Matching Modes**: Choose between AI semantic matching and traditional regex-based matching
- **📊 Multi-Source Support**: Automatic fallback between ASSRT (Chinese content) and OpenSubtitles (International)
- **⚡ Batch Processing**: Process entire video libraries with intelligent matching and user confirmation
- **🎯 Smart Filtering**: Skip videos that already have subtitles, customizable similarity thresholds
- **🌐 Multi-language Support**: Download subtitles in multiple languages simultaneously
- **✅ Safe Operations**: Dry-run preview and user confirmation before file operations

## Quick Start

### Installation

```bash
git clone https://github.com/SeptPonts/caption-mate.git
cd caption-mate
make install
```

### Setup

```bash
# Initialize configuration
uv run caption-mate config init

# Test NAS connection
uv run caption-mate nas test
```

### Basic Usage

```bash
# Smart subtitle matching (AI mode - recommended)
uv run caption-mate nas match /Movies/Season1 --mode ai --dry-run

# Traditional regex matching
uv run caption-mate nas match /Movies/Season1 --mode regex --dry-run

# Execute after preview
uv run caption-mate nas match /Movies/Season1 --mode ai
```

## Core Commands

### NAS Management

```bash
# Browse NAS directories
uv run caption-mate nas ls /Movies
uv run caption-mate nas tree /Movies --depth 3

# Scan for video files
uv run caption-mate nas scan /Movies
```

### Intelligent Matching (⭐ Key Feature)

```bash
# AI semantic matching (best for mixed content)
uv run caption-mate nas match /path/to/videos --mode ai --threshold 0.8

# Traditional regex matching (fast, rule-based)
uv run caption-mate nas match /path/to/videos --mode regex --threshold 0.8

# Preview before execution
uv run caption-mate nas match /path/to/videos --mode ai --dry-run

# Force overwrite existing subtitles
uv run caption-mate nas match /path/to/videos --mode ai --force
```

### Subtitle Download

```bash
# Auto mode: scan and download
uv run caption-mate auto /Movies --dry-run

# Manual download for specific video
uv run caption-mate subtitles download /Movies/example.mp4

# Batch processing
uv run caption-mate subtitles batch /Movies
```

### Configuration

```bash
uv run caption-mate config init          # Interactive setup
uv run caption-mate config show          # Show current config
uv run caption-mate config set nas.host 192.168.1.100
```

## AI vs Regex Matching

### AI Mode (Recommended)
- **Best for**: Mixed language content, TV series with complex naming
- **Advantages**: Understands semantic meaning, handles season/episode info, cross-language matching
- **Use cases**: "The Man in the High Castle S01E01" ↔ "高堡奇人.S01E01.新世界.zh-hans.srt"

### Regex Mode (Traditional)
- **Best for**: Consistent naming patterns, performance-critical scenarios
- **Advantages**: Fast processing, predictable results, no API dependencies
- **Use cases**: Standard release group formats with clear patterns

## Configuration

Create `~/.caption-mate/config.yaml` or use environment variables:

```yaml
# AI Configuration (for AI matching mode)
# Environment: OAI_MODEL, OAI_API_KEY, OAI_BASE_URL

nas:
  protocol: "smb"
  host: "192.168.1.100"
  username: "your_nas_user"
  password: "your_nas_password"

subtitles:
  languages: ["zh-cn", "en"]
  formats: ["srt", "ass"]
  naming_pattern: "{filename}.{lang}.{ext}"

# Subtitle providers
assrt:
  api_token: "your_assrt_token"    # For Chinese content
opensubtitles:
  api_key: "your_opensubtitles_key" # For international content
```

## Examples

### TV Series Processing

```bash
# Preview AI matching for TV series
uv run caption-mate nas match "/TV Shows/The Office Season 1" --mode ai --dry-run

# Execute with user confirmation
uv run caption-mate nas match "/TV Shows/The Office Season 1" --mode ai

# Batch process entire series
uv run caption-mate nas scan "/TV Shows/The Office" --recursive
uv run caption-mate nas match "/TV Shows/The Office" --mode ai --threshold 0.9
```

### Movie Collection

```bash
# Process movie directory with high accuracy threshold
uv run caption-mate nas match "/Movies/Action" --mode ai --threshold 0.95

# Use regex for consistent naming patterns
uv run caption-mate nas match "/Movies/YIFY" --mode regex --threshold 0.8
```

### Mixed Content

```bash
# AI excels at mixed language content
uv run caption-mate nas match "/Asian Movies" --mode ai --dry-run
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   NAS Client    │───▶│  Video Scanner   │───▶│ Subtitle Matcher│
│   (SMB/CIFS)    │    │                  │    │   (AI/Regex)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Subtitle Sources│◀───│  Download Engine │◀───│ Match Results   │
│ (ASSRT/OpenSubs)│    │                  │    │ (User Confirm)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Core Components

- **NAS Client**: SMB/CIFS connection management
- **Video Scanner**: Recursive video file discovery
- **Subtitle Matcher**: AI semantic matching + regex fallback
- **Multi-Source Engine**: ASSRT (Chinese) + OpenSubtitles (International)
- **Safe Operations**: Dry-run preview + user confirmation

## API Setup

### For AI Matching Mode

Set up OpenAI-compatible API (DeepSeek recommended):

```bash
export OAI_MODEL="deepseek-reasoner"
export OAI_API_KEY="your_api_key"
export OAI_BASE_URL="https://api.deepseek.com"
```

### For Subtitle Sources

**ASSRT (Chinese content)**:
```bash
uv run caption-mate config set assrt.api_token "your_32_char_token"
```

**OpenSubtitles (International)**:
```bash
uv run caption-mate config set opensubtitles.api_key "your_api_key"
```

## Troubleshooting

### AI Mode Issues
- Verify API credentials and model availability
- Check network connectivity to AI service
- Try regex mode as fallback for debugging

### Matching Accuracy
- Lower `--threshold` value for more matches
- Use `--dry-run` to preview results
- AI mode generally provides better accuracy for complex cases

### NAS Connection
- Verify SMB/CIFS is enabled on your NAS
- Check firewall settings
- Test with IP address instead of hostname

## Development

```bash
git clone https://github.com/SeptPonts/caption-mate.git
cd caption-mate
make install
make test
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see the LICENSE file for details.