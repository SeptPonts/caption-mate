"""MCP Server for Caption-Mate NAS operations."""

import json
from pathlib import Path

from mcp.server import Server
from mcp.types import TextContent, Tool

from .core.config import Config
from .core.nas_client import NASClient
from .core.subtitle_matcher import SubtitleMatcher
from .models.subtitle import SubtitleFile
from .models.video import VideoFile

app = Server("caption-mate")


def _load_config() -> Config:
    """Load configuration from default location."""
    try:
        config = Config.load(None)
        errors = config.validate()
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        return config
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")


def _detect_language_from_filename(filename: str, config: Config) -> str:
    """Detect language from subtitle filename."""
    name = filename.lower()

    language_patterns = {
        "zh-cn": [".zh.", ".chi.", ".chs.", ".chinese.", "chinese", ".中文.", ".简体."],
        "zh-tw": [".cht.", ".繁体.", ".traditional."],
        "en": [".en.", ".eng.", ".english.", "english"],
        "ja": [".jp.", ".jpn.", ".japanese.", "japanese"],
        "ko": [".ko.", ".kor.", ".korean.", "korean"],
    }

    for lang_code, patterns in language_patterns.items():
        if any(pattern in name for pattern in patterns):
            return lang_code

    return config.subtitles.languages[0] if config.subtitles.languages else "zh-cn"


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available NAS operation tools."""
    return [
        Tool(
            name="nas_test",
            description="Test NAS connection and list available shares",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="nas_ls",
            description="List files and directories in a NAS path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Path to list (e.g., '/Movies' or "
                            "'/sata11-156XXXX6325/TV Series')"
                        ),
                    },
                    "long": {
                        "type": "boolean",
                        "description": (
                            "Show detailed information including size and modified time"
                        ),
                        "default": False,
                    },
                    "pattern": {
                        "type": "string",
                        "description": (
                            "Filter files by pattern (e.g., '*.mp4', '*.srt')"
                        ),
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="nas_tree",
            description="Show directory tree structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to show tree for",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse",
                        "default": 2,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="nas_scan",
            description="Scan for video files in a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to scan for video files",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Scan subdirectories recursively",
                        "default": True,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="nas_match",
            description="Match subtitle files to video files and rename them",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path containing video and subtitle files",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["ai", "regex"],
                        "description": (
                            "Matching mode: 'ai' for semantic matching or "
                            "'regex' for pattern-based"
                        ),
                        "default": "ai",
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Similarity threshold (0.0-1.0)",
                        "default": 0.8,
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview matches without renaming files",
                        "default": False,
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Overwrite existing subtitle files",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "nas_test":
            return await _handle_nas_test()
        elif name == "nas_ls":
            return await _handle_nas_ls(arguments)
        elif name == "nas_tree":
            return await _handle_nas_tree(arguments)
        elif name == "nas_scan":
            return await _handle_nas_scan(arguments)
        elif name == "nas_match":
            return await _handle_nas_match(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_nas_test() -> list[TextContent]:
    """Handle nas_test tool."""
    config = _load_config()

    with NASClient(config) as client:
        success = client.test_connection()

        if success:
            shares = client.list_shares()
            result = {
                "status": "success",
                "message": "NAS connection successful",
                "shares": shares,
            }
        else:
            result = {"status": "failed", "message": "NAS connection failed"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_nas_ls(arguments: dict) -> list[TextContent]:
    """Handle nas_ls tool."""
    path = arguments["path"]
    long = arguments.get("long", False)
    pattern = arguments.get("pattern")

    config = _load_config()

    with NASClient(config) as client:
        if not client.path_exists(path):
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Path does not exist: {path}"}),
                )
            ]

        entries = client.list_directory(path, pattern)

        result = {
            "path": path,
            "count": len(entries),
            "entries": [],
        }

        for entry in entries:
            entry_data = {
                "name": entry.name,
                "type": "directory" if entry.is_dir else "file",
            }
            if long:
                entry_data.update(
                    {
                        "size": entry.size,
                        "size_human": entry.size_human,
                        "modified": (
                            entry.modified_time.isoformat()
                            if entry.modified_time
                            else None
                        ),
                    }
                )
            result["entries"].append(entry_data)

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_nas_tree(arguments: dict) -> list[TextContent]:
    """Handle nas_tree tool."""
    path = arguments["path"]
    depth = arguments.get("depth", 2)

    config = _load_config()

    with NASClient(config) as client:
        if not client.path_exists(path):
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Path does not exist: {path}"}),
                )
            ]

        tree_data = client.get_directory_tree(path, max_depth=depth)

        result = {"path": path, "depth": depth, "tree": tree_data}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_nas_scan(arguments: dict) -> list[TextContent]:
    """Handle nas_scan tool."""
    path = arguments["path"]
    recursive = arguments.get("recursive", True)

    config = _load_config()

    with NASClient(config) as client:
        if not client.path_exists(path):
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Path does not exist: {path}"}),
                )
            ]

        video_files = client.scan_video_files(path, recursive)

        result = {
            "path": path,
            "recursive": recursive,
            "count": len(video_files),
            "videos": [
                {
                    "name": vf.name,
                    "path": vf.path,
                    "size": vf.size,
                    "size_human": vf.size_human,
                }
                for vf in video_files
            ],
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_nas_match(arguments: dict) -> list[TextContent]:
    """Handle nas_match tool."""
    path = arguments["path"]
    mode = arguments.get("mode", "ai")
    threshold = arguments.get("threshold", 0.8)
    dry_run = arguments.get("dry_run", False)
    force = arguments.get("force", False)

    config = _load_config()

    with NASClient(config) as nas_client:
        if not nas_client.path_exists(path):
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Path does not exist: {path}"}),
                )
            ]

        # Scan directory for files
        all_entries = nas_client.list_directory(path)
        video_extensions = set(config.scanning.video_extensions)
        subtitle_extensions = {".srt", ".ass", ".ssa", ".vtt", ".sub"}

        video_files = []
        subtitle_files = []

        for entry in all_entries:
            if entry.is_dir:
                continue

            file_ext = Path(entry.name).suffix.lower()
            if file_ext in video_extensions:
                video_file = VideoFile(
                    filename=entry.name,
                    file_path=entry.path,
                    file_size=entry.size,
                    nas_path=entry.path,
                    modified_time=entry.modified_time,
                )
                video_files.append(video_file)
            elif file_ext in subtitle_extensions:
                detected_language = _detect_language_from_filename(entry.name, config)
                subtitle_file = SubtitleFile(
                    filename=entry.name,
                    file_path=entry.path,
                    language=detected_language,
                    format=file_ext.lstrip("."),
                    video_filename="",
                    file_size=entry.size,
                )
                subtitle_files.append(subtitle_file)

    if not video_files:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "No video files found in directory"}),
            )
        ]

    if not subtitle_files:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "No subtitle files found in directory"}),
            )
        ]

    # Perform matching
    matcher = SubtitleMatcher(similarity_threshold=threshold, mode=mode)

    if mode == "ai":
        match_results = await matcher.match_directory_async(video_files, subtitle_files)
    else:
        match_results = matcher.match_directory(video_files, subtitle_files)

    successful_matches = [result for result in match_results if result.has_match]

    if not successful_matches:
        return [
            TextContent(
                type="text",
                text=json.dumps({"message": "No matches found above threshold"}),
            )
        ]

    rename_operations = matcher.plan_rename_operations(successful_matches, "")

    # Prepare result
    result = {
        "path": path,
        "mode": mode,
        "threshold": threshold,
        "dry_run": dry_run,
        "matches_found": len(rename_operations),
        "matches": [],
    }

    if not dry_run:
        # Execute renames
        renamed_count = 0
        skipped_count = 0
        error_count = 0

        with NASClient(config) as nas_client:
            for operation in rename_operations:
                if not operation.needs_rename:
                    skipped_count += 1
                    continue

                old_path = operation.subtitle_file.file_path
                new_path = str(Path(path) / operation.new_name)

                try:
                    if nas_client.path_exists(new_path) and not force:
                        skipped_count += 1
                        result["matches"].append(
                            {
                                "video": operation.target_video.filename,
                                "old_subtitle": operation.old_name,
                                "new_subtitle": operation.new_name,
                                "confidence": operation.confidence,
                                "status": "skipped",
                                "reason": "file exists",
                            }
                        )
                    else:
                        success = nas_client.rename_file(old_path, new_path)
                        if success:
                            renamed_count += 1
                            result["matches"].append(
                                {
                                    "video": operation.target_video.filename,
                                    "old_subtitle": operation.old_name,
                                    "new_subtitle": operation.new_name,
                                    "confidence": operation.confidence,
                                    "status": "renamed",
                                }
                            )
                        else:
                            error_count += 1
                            result["matches"].append(
                                {
                                    "video": operation.target_video.filename,
                                    "old_subtitle": operation.old_name,
                                    "new_subtitle": operation.new_name,
                                    "confidence": operation.confidence,
                                    "status": "error",
                                }
                            )
                except Exception as e:
                    error_count += 1
                    result["matches"].append(
                        {
                            "video": operation.target_video.filename,
                            "old_subtitle": operation.old_name,
                            "new_subtitle": operation.new_name,
                            "confidence": operation.confidence,
                            "status": "error",
                            "error": str(e),
                        }
                    )

        result["summary"] = {
            "renamed": renamed_count,
            "skipped": skipped_count,
            "errors": error_count,
        }
    else:
        # Dry run - just show what would be done
        for operation in rename_operations:
            result["matches"].append(
                {
                    "video": operation.target_video.filename,
                    "old_subtitle": operation.old_name,
                    "new_subtitle": operation.new_name,
                    "confidence": operation.confidence,
                    "needs_rename": operation.needs_rename,
                }
            )

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def main():
    """Run the MCP server."""
    import asyncio

    from mcp.server.stdio import stdio_server

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
