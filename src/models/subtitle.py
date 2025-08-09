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


@dataclass
class SubtitleSearchResult:
    """Result from subtitle search"""

    video_filename: str
    found_subtitles: list[SubtitleFile]
    search_methods_used: list[str]  # hash, filename, etc.
    search_time: datetime

    def __post_init__(self):
        if not hasattr(self, "search_time") or self.search_time is None:
            self.search_time = datetime.now()

    @property
    def has_results(self) -> bool:
        """Check if any subtitles were found"""
        return len(self.found_subtitles) > 0

    @property
    def languages_found(self) -> list[str]:
        """Get list of languages found"""
        return list(set(sub.language for sub in self.found_subtitles))

    def get_best_subtitle(self, language: str) -> Optional[SubtitleFile]:
        """Get the best subtitle for a specific language"""
        candidates = [sub for sub in self.found_subtitles if sub.language == language]
        if not candidates:
            return None

        # Sort by download count and rating
        candidates.sort(key=lambda x: (x.download_count, x.rating), reverse=True)
        return candidates[0]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "video_filename": self.video_filename,
            "found_subtitles": [sub.to_dict() for sub in self.found_subtitles],
            "search_methods_used": self.search_methods_used,
            "search_time": self.search_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubtitleSearchResult":
        """Create from dictionary"""
        data["found_subtitles"] = [
            SubtitleFile.from_dict(sub_data)
            for sub_data in data.get("found_subtitles", [])
        ]
        data["search_time"] = datetime.fromisoformat(data["search_time"])

        return cls(**data)


@dataclass
class DownloadResult:
    """Result from subtitle download"""

    video_filename: str
    subtitle_file: Optional[SubtitleFile]
    success: bool
    error_message: Optional[str] = None
    download_time: Optional[datetime] = None

    def __post_init__(self):
        if self.download_time is None:
            self.download_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "video_filename": self.video_filename,
            "subtitle_file": self.subtitle_file.to_dict()
            if self.subtitle_file
            else None,
            "success": self.success,
            "error_message": self.error_message,
            "download_time": self.download_time.isoformat()
            if self.download_time
            else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadResult":
        """Create from dictionary"""
        if data.get("subtitle_file"):
            data["subtitle_file"] = SubtitleFile.from_dict(data["subtitle_file"])
        if data.get("download_time"):
            data["download_time"] = datetime.fromisoformat(data["download_time"])

        return cls(**data)
