from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import ffmpeg

from .config import Config


@dataclass
class VideoInfo:
    """Video file information"""

    filename: str
    file_path: str
    file_size: int
    duration: Optional[float] = None  # Duration in seconds
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    fps: Optional[float] = None

    @property
    def size_human(self) -> str:
        """Human readable file size"""
        if self.file_size == 0:
            return "0B"

        size = float(self.file_size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    @property
    def duration_human(self) -> str:
        """Human readable duration"""
        if self.duration is None:
            return "Unknown"

        td = timedelta(seconds=int(self.duration))
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if td.days > 0:
            return f"{td.days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def resolution(self) -> str:
        """Resolution string"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"


class VideoAnalyzer:
    """Analyzer for video file metadata"""

    def __init__(self, config: Config):
        self.config = config

    def is_video_file(self, filename: str) -> bool:
        """Check if file is a video file based on extension"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.config.scanning.video_extensions

    def analyze_file(self, file_path: str, file_size: int) -> VideoInfo:
        """Analyze a video file and extract metadata"""
        filename = Path(file_path).name

        video_info = VideoInfo(
            filename=filename, file_path=file_path, file_size=file_size
        )

        try:
            # Use ffprobe to get video metadata
            probe = ffmpeg.probe(file_path)

            # Find video stream
            video_streams = [
                stream
                for stream in probe.get("streams", [])
                if stream.get("codec_type") == "video"
            ]

            if video_streams:
                video_stream = video_streams[0]

                # Extract video information
                video_info.width = video_stream.get("width")
                video_info.height = video_stream.get("height")
                video_info.codec = video_stream.get("codec_name")

                # Frame rate
                fps_str = video_stream.get("r_frame_rate", "0/1")
                if "/" in fps_str:
                    try:
                        num, den = fps_str.split("/")
                        if int(den) != 0:
                            video_info.fps = float(num) / float(den)
                    except (ValueError, ZeroDivisionError):
                        pass

                # Duration (try video stream first, then format)
                duration = video_stream.get("duration")
                if duration:
                    video_info.duration = float(duration)

            # Get format information
            format_info = probe.get("format", {})

            # Duration from format if not found in stream
            if video_info.duration is None:
                duration = format_info.get("duration")
                if duration:
                    video_info.duration = float(duration)

            # Bitrate
            bitrate = format_info.get("bit_rate")
            if bitrate:
                video_info.bitrate = int(bitrate)

        except Exception:
            # If ffprobe fails, we still return basic info
            pass

        return video_info

    def analyze_local_file(self, local_path: str) -> VideoInfo:
        """Analyze a local video file"""
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        file_size = path.stat().st_size
        return self.analyze_file(str(path), file_size)

    def has_subtitles(self, video_path: str) -> Dict[str, bool]:
        """Check if video file already has subtitle files"""
        video_path_obj = Path(video_path)
        video_dir = video_path_obj.parent
        video_stem = video_path_obj.stem

        subtitle_formats = self.config.subtitles.formats
        languages = self.config.subtitles.languages

        found_subtitles = {}

        for lang in languages:
            found_subtitles[lang] = False

            for fmt in subtitle_formats:
                # Check for different naming patterns
                patterns = [
                    f"{video_stem}.{lang}.{fmt}",
                    f"{video_stem}.{fmt}",
                    f"{video_stem}-{lang}.{fmt}",
                ]

                for pattern in patterns:
                    subtitle_path = video_dir / pattern
                    if subtitle_path.exists():
                        found_subtitles[lang] = True
                        break

                if found_subtitles[lang]:
                    break

        return found_subtitles

    def should_skip_video(self, video_path: str) -> bool:
        """Determine if video should be skipped based on config"""
        if not self.config.scanning.skip_existing:
            return False

        # Check if any preferred language subtitles exist
        subtitle_status = self.has_subtitles(video_path)

        # Skip if at least one preferred language has subtitles
        return any(subtitle_status.values())

    def extract_metadata_for_matching(self, video_info: VideoInfo) -> Dict[str, Any]:
        """Extract metadata useful for subtitle matching"""
        metadata = {
            "filename": video_info.filename,
            "file_size": video_info.file_size,
            "duration": video_info.duration,
        }

        # Extract title from filename (remove common patterns)
        import re

        filename_stem = Path(video_info.filename).stem

        # Remove year patterns
        title = re.sub(r"[\(\[](?:19|20)\d{2}[\)\]]", "", filename_stem)

        # Remove quality indicators and release group tags
        quality_patterns = [
            r"\b(?:1080p|720p|480p|4K|HD|BluRay|BrRip|DVDRip|WEBRip|HDTV)\b",
            r"\b(?:x264|x265|HEVC|DivX|XviD)\b",
            r"\b(?:AAC|AC3|DTS|MP3)\b",
            r"\b(?:YIFY|RARBG|ETRG|SPARKS)\b",
        ]

        for pattern in quality_patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Clean up separators and extra spaces
        title = re.sub(r"[._-]+", " ", title)
        title = re.sub(r"\s+", " ", title).strip()

        metadata["extracted_title"] = title

        # Extract season/episode info if it's a TV show
        episode_match = re.search(r"[Ss](\d+)[Ee](\d+)", filename_stem)
        if episode_match:
            metadata["season"] = int(episode_match.group(1))
            metadata["episode"] = int(episode_match.group(2))
            metadata["is_tv_show"] = True
        else:
            metadata["is_tv_show"] = False

        # Extract year if present
        year_match = re.search(r"[\(\[]?(19|20)(\d{2})[\)\]]?", filename_stem)
        if year_match:
            metadata["year"] = int(year_match.group(1) + year_match.group(2))

        return metadata
