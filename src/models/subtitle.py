from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class SubtitleFile:
    """Represents a subtitle file"""

    filename: str
    file_path: str
    language: str
    format: str  # srt, ass, vtt, etc.
    video_filename: str  # Associated video file

    # Download metadata
    source: str = "opensubtitles"  # Source of the subtitle
    source_id: Optional[str] = None  # ID from the source
    download_time: Optional[datetime] = None
    file_size: int = 0

    # Quality metrics
    download_count: int = 0
    rating: float = 0.0

    def __post_init__(self):
        if self.download_time is None:
            self.download_time = datetime.now()

    @property
    def size_human(self) -> str:
        """Human readable file size"""
        if self.file_size == 0:
            return "0B"

        size = float(self.file_size)
        for unit in ["B", "KB", "MB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}MB"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "language": self.language,
            "format": self.format,
            "video_filename": self.video_filename,
            "source": self.source,
            "source_id": self.source_id,
            "download_time": self.download_time.isoformat()
            if self.download_time
            else None,
            "file_size": self.file_size,
            "download_count": self.download_count,
            "rating": self.rating,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubtitleFile":
        """Create from dictionary"""
        if data.get("download_time"):
            data["download_time"] = datetime.fromisoformat(data["download_time"])

        return cls(**data)
