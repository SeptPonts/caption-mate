from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class VideoFile:
    """Represents a video file with its metadata"""

    filename: str
    file_path: str
    file_size: int
    nas_path: str  # Original path on NAS

    # Video metadata
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    fps: Optional[float] = None

    # File metadata
    modified_time: Optional[datetime] = None
    scanned_time: Optional[datetime] = None

    # Subtitle matching metadata
    extracted_title: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    is_tv_show: bool = False

    # Subtitle status
    has_subtitles: Dict[str, bool] = None

    def __post_init__(self):
        if self.has_subtitles is None:
            self.has_subtitles = {}

        if self.scanned_time is None:
            self.scanned_time = datetime.now()

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

        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    @property
    def resolution(self) -> str:
        """Resolution string"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"

    @property
    def display_name(self) -> str:
        """Display name for the video"""
        if self.extracted_title:
            if self.is_tv_show and self.season and self.episode:
                return f"{self.extracted_title} S{self.season:02d}E{self.episode:02d}"
            elif self.year:
                return f"{self.extracted_title} ({self.year})"
            else:
                return self.extracted_title
        else:
            return Path(self.filename).stem

    def needs_subtitles(self, languages: list[str]) -> bool:
        """Check if video needs subtitles for any of the specified languages"""
        for lang in languages:
            if not self.has_subtitles.get(lang, False):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "nas_path": self.nas_path,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "fps": self.fps,
            "modified_time": self.modified_time.isoformat()
            if self.modified_time
            else None,
            "scanned_time": self.scanned_time.isoformat()
            if self.scanned_time
            else None,
            "extracted_title": self.extracted_title,
            "year": self.year,
            "season": self.season,
            "episode": self.episode,
            "is_tv_show": self.is_tv_show,
            "has_subtitles": self.has_subtitles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoFile":
        """Create from dictionary"""
        # Handle datetime parsing
        if data.get("modified_time"):
            data["modified_time"] = datetime.fromisoformat(data["modified_time"])
        if data.get("scanned_time"):
            data["scanned_time"] = datetime.fromisoformat(data["scanned_time"])

        return cls(**data)
