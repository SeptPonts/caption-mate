import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ..models.subtitle import SubtitleFile
from ..models.video import VideoFile


@dataclass
class MatchResult:
    """Result of matching a video file with subtitle files"""

    video_file: VideoFile
    matched_subtitle: Optional[SubtitleFile]
    similarity_score: float
    all_candidates: List[Tuple[SubtitleFile, float]]
    match_method: str  # "exact", "normalized", "fuzzy"

    @property
    def has_match(self) -> bool:
        """Check if a match was found"""
        return self.matched_subtitle is not None

    @property
    def confidence_level(self) -> str:
        """Human readable confidence level"""
        if self.similarity_score >= 0.95:
            return "high"
        elif self.similarity_score >= 0.8:
            return "medium"
        else:
            return "low"


@dataclass
class RenameOperation:
    """Represents a subtitle file rename operation"""

    subtitle_file: SubtitleFile
    old_name: str
    new_name: str
    target_video: VideoFile
    confidence: float

    @property
    def needs_rename(self) -> bool:
        """Check if rename is actually needed"""
        return self.old_name != self.new_name


class SubtitleMatcher:
    """Matches subtitle files to video files using filename similarity"""

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold

    def normalize_filename(self, filename: str) -> str:
        """Normalize filename for matching by removing common patterns"""
        # Remove file extension
        name = Path(filename).stem

        # Remove common patterns in brackets and parentheses
        # Examples: [1080p], (2023), [BluRay], (Director's Cut)
        name = re.sub(r"\[.*?\]", "", name)
        name = re.sub(r"\(.*?\)", "", name)

        # Remove common release tags
        # Examples: .HDTV, .WEB-DL, .BluRay, .x264, .h264
        patterns = [
            r"\.(?:HDTV|WEB-DL|BluRay|BDRip|DVDRip|WEBRip|REMUX)",
            r"\.(?:x264|h264|x265|h265|HEVC|AVC)",
            r"\.(?:AAC|DTS|AC3|MP3|FLAC)",
            r"\.(?:1080p|720p|480p|4K|UHD)",
            r"\-(?:RARBG|YTS|ETRG|FGT|SPARKS|DIMENSION)",
        ]

        for pattern in patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)

        # Clean up multiple spaces and dots
        name = re.sub(r"[.\s]+", " ", name)
        name = name.strip()

        return name.lower()

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two normalized filenames"""
        norm1 = self.normalize_filename(name1)
        norm2 = self.normalize_filename(name2)

        # Exact match after normalization
        if norm1 == norm2:
            return 1.0

        # Simple word-based similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def find_best_match(
        self, video_file: VideoFile, subtitle_files: List[SubtitleFile]
    ) -> MatchResult:
        """Find the best matching subtitle for a video file"""
        if not subtitle_files:
            return MatchResult(
                video_file=video_file,
                matched_subtitle=None,
                similarity_score=0.0,
                all_candidates=[],
                match_method="none",
            )

        candidates = []
        for subtitle in subtitle_files:
            similarity = self.calculate_similarity(
                video_file.filename, subtitle.filename
            )
            candidates.append((subtitle, similarity))

        # Sort by similarity score
        candidates.sort(key=lambda x: x[1], reverse=True)

        best_subtitle, best_score = candidates[0]
        match_method = "none"

        if best_score >= 0.95:
            match_method = "exact"
        elif best_score >= self.similarity_threshold:
            match_method = "normalized"
        elif best_score > 0.0:
            match_method = "fuzzy"

        # Only return match if it meets threshold
        matched_subtitle = (
            best_subtitle if best_score >= self.similarity_threshold else None
        )

        return MatchResult(
            video_file=video_file,
            matched_subtitle=matched_subtitle,
            similarity_score=best_score,
            all_candidates=candidates,
            match_method=match_method,
        )

    def generate_subtitle_filename(
        self, video_filename: str, language: str, subtitle_extension: str
    ) -> str:
        """Generate proper subtitle filename for a video"""
        video_stem = Path(video_filename).stem
        return f"{video_stem}.{language}.{subtitle_extension}"

    def plan_rename_operations(
        self, match_results: List[MatchResult], target_directory: str
    ) -> List[RenameOperation]:
        """Plan rename operations for matched subtitles"""
        operations = []

        for result in match_results:
            if not result.has_match or result.matched_subtitle is None:
                continue

            subtitle = result.matched_subtitle
            video = result.video_file

            # Generate new filename
            new_filename = self.generate_subtitle_filename(
                video.filename,
                subtitle.language,
                Path(subtitle.filename).suffix.lstrip("."),
            )

            operation = RenameOperation(
                subtitle_file=subtitle,
                old_name=subtitle.filename,
                new_name=new_filename,
                target_video=video,
                confidence=result.similarity_score,
            )

            operations.append(operation)

        return operations

    def match_directory(
        self, video_files: List[VideoFile], subtitle_files: List[SubtitleFile]
    ) -> List[MatchResult]:
        """Match all videos with available subtitles in a directory"""
        results = []

        for video in video_files:
            # Find potential subtitle matches
            # Filter subtitles that might belong to this video
            candidates = [
                sub
                for sub in subtitle_files
                if self.calculate_similarity(video.filename, sub.filename) > 0.1
            ]

            match_result = self.find_best_match(video, candidates)
            results.append(match_result)

        return results
