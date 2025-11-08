# Caption-Mate

[English](README.md) | [中文](README_zh.md)

A powerful CLI tool for intelligent subtitle matching on NAS devices, featuring AI-powered semantic matching for accurate subtitle-to-video pairing.

## Features

- **🤖 AI-Powered Matching**: Smart semantic matching using DeepSeek/OpenAI for accurate subtitle-to-video pairing
- **📁 NAS Integration**: Connect to your NAS via SMB/CIFS protocol for seamless file management
- **🔌 MCP Integration**: Use Caption-Mate directly from Claude Code via Model Context Protocol
- **🔍 Dual Matching Modes**: Choose between AI semantic matching and traditional regex-based matching
- **⚡ Batch Processing**: Process entire video libraries with intelligent matching and user confirmation
- **🎯 Smart Filtering**: Customizable similarity thresholds for precise matching
- **🌐 Multi-language Support**: Handle subtitle files in multiple languages
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

## MCP Integration

Caption-Mate can be used directly from Claude Code through the Model Context Protocol (MCP), enabling conversational subtitle management.

### What is MCP Mode?

MCP mode allows Claude to operate your NAS subtitle system through natural conversation:
- **CLI Mode**: You type terminal commands manually
- **MCP Mode**: You describe what you want, Claude executes the operations

### Installation

**Method 1: Quick Setup**
```bash
make mcp-install
```

**Method 2: Manual Configuration**

Add to your Claude Code MCP settings:
```json
{
  "caption-mate": {
    "command": "uv",
    "args": ["run", "--directory", "/path/to/caption-mate", "caption-mate-mcp"]
  }
}
```

Replace `/path/to/caption-mate` with your actual project path.

### Available Tools

The MCP server provides 5 tools for Claude to use:

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `nas_test` | Test NAS connection and list shares | None |
| `nas_ls` | List files and directories | `path`, `long`, `pattern` |
| `nas_tree` | Show directory tree structure | `path`, `depth` |
| `nas_scan` | Scan for video files | `path`, `recursive` |
| `nas_match` | **Match and rename subtitles** | `path`, `mode`, `threshold`, `dry_run` |

### Usage Examples

**Interactive Workflow:**

```
You: "Check if my NAS is connected"
Claude: [Calls nas_test tool]
→ Shows connection status and available shares

You: "What videos are in /Movies/Season1?"
Claude: [Calls nas_scan with path="/Movies/Season1"]
→ Lists all video files found

You: "Match subtitles using AI mode, show me preview first"
Claude: [Calls nas_match with mode="ai", dry_run=true]
→ Shows planned subtitle matches

You: "Looks good, execute it"
Claude: [Calls nas_match with mode="ai", dry_run=false]
→ Renames subtitle files to match videos
```

### MCP vs CLI Comparison

| Aspect | MCP Mode | CLI Mode |
|--------|----------|----------|
| **Interface** | Natural language conversation | Terminal commands |
| **Best For** | Interactive exploration, one-off tasks | Automation, scripting, cron jobs |
| **Learning Curve** | Low (just describe what you want) | Medium (need to know commands) |
| **Flexibility** | High (Claude adapts to your requests) | High (full command control) |
| **Use Case** | "Find and match all subtitles" | `caption-mate nas match /path --mode ai` |

**When to use MCP:**
- Exploring new directories on your NAS
- Testing different matching thresholds
- One-time cleanup tasks
- Learning how the tool works

**When to use CLI:**
- Automated scripts and cron jobs
- Batch processing pipelines
- CI/CD integration
- Reproducible workflows

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
                                                         ▼
                                                ┌─────────────────┐
                                                │ Match Results   │
                                                │ (User Confirm)  │
                                                └─────────────────┘
```

### Core Components

- **NAS Client**: SMB/CIFS connection management
- **Video Scanner**: Recursive video file discovery
- **Subtitle Matcher**: AI semantic matching + regex fallback
- **Safe Operations**: Dry-run preview + user confirmation

## API Setup

### For AI Matching Mode

Set up OpenAI-compatible API (DeepSeek recommended):

```bash
export OAI_MODEL="deepseek-reasoner"
export OAI_API_KEY="your_api_key"
export OAI_BASE_URL="https://api.deepseek.com"
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