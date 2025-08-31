import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import jsonschema
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from ..models.subtitle import SubtitleFile
from ..models.video import VideoFile


def _robust_json_parse(
    content: str, video_names: List[str]
) -> Dict[str, Optional[str]]:
    """Robust JSON parsing with multiple fallback strategies"""

    # Define expected schema for validation
    schema = {
        "type": "object",
        "patternProperties": {".*": {"type": ["string", "null"]}},
        "additionalProperties": False,
    }

    # Strategy 1: Direct JSON parsing
    try:
        matches = json.loads(content)
        jsonschema.validate(matches, schema)
        return _filter_valid_matches(matches, video_names)
    except (json.JSONDecodeError, jsonschema.ValidationError):
        pass

    # Strategy 2: Extract from markdown code block
    try:
        # Remove markdown code blocks
        markdown_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(markdown_pattern, content, re.MULTILINE)
        if match:
            json_content = match.group(1).strip()
            matches = json.loads(json_content)
            jsonschema.validate(matches, schema)
            return _filter_valid_matches(matches, video_names)
    except (json.JSONDecodeError, jsonschema.ValidationError):
        pass

    # Strategy 3: Extract JSON object using regex
    try:
        # Find JSON object pattern
        json_pattern = r"\{[\s\S]*\}"
        match = re.search(json_pattern, content)
        if match:
            json_str = match.group(0)
            matches = json.loads(json_str)
            jsonschema.validate(matches, schema)
            return _filter_valid_matches(matches, video_names)
    except (json.JSONDecodeError, jsonschema.ValidationError):
        pass

    # Strategy 4: Line-by-line parsing for partial recovery
    try:
        return _parse_partial_json(content, video_names)
    except Exception:
        pass

    # Final fallback: empty matches with error logging
    print(f"Warning: Could not parse AI response: {content[:200]}...")
    return {}


def _filter_valid_matches(
    matches: Dict[str, Optional[str]], video_names: List[str]
) -> Dict[str, Optional[str]]:
    """Filter matches to only include valid video names"""
    filtered = {}
    for video_name in video_names:
        if video_name in matches:
            filtered[video_name] = matches[video_name]
        else:
            filtered[video_name] = None
    return filtered


def _parse_partial_json(
    content: str, video_names: List[str]
) -> Dict[str, Optional[str]]:
    """Parse partial/malformed JSON by extracting key-value pairs"""
    matches = {}

    # Extract quoted key-value pairs
    pattern = r'"([^"]+)"\s*:\s*(?:"([^"]*)"|null)'

    for match in re.finditer(pattern, content):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else None

        # Only include if key is a valid video name
        if key in video_names:
            matches[key] = value

    # Ensure all video names are present
    for video_name in video_names:
        if video_name not in matches:
            matches[video_name] = None

    return matches


@dataclass
class MatchResult:
    """Result of matching a video file with subtitle files"""

    video_file: VideoFile
    matched_subtitle: Optional[SubtitleFile]
    similarity_score: float
    all_candidates: List[Tuple[SubtitleFile, float]]
    match_method: str  # "exact", "normalized", "fuzzy", "ai_semantic"

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

    def __init__(self, similarity_threshold: float = 0.8, mode: str = "regex"):
        self.similarity_threshold = similarity_threshold
        self.mode = mode

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

    async def match_directory_async(
        self, video_files: List[VideoFile], subtitle_files: List[SubtitleFile]
    ) -> List[MatchResult]:
        """Async version supporting AI matching"""
        if self.mode == "ai":
            return await self._ai_match_directory(video_files, subtitle_files)
        else:
            return self.match_directory(video_files, subtitle_files)

    async def _ai_match_directory(
        self, video_files: List[VideoFile], subtitle_files: List[SubtitleFile]
    ) -> List[MatchResult]:
        """AI-powered batch matching"""
        if not video_files or not subtitle_files:
            return []

        video_names = [v.filename for v in video_files]
        subtitle_names = [s.filename for s in subtitle_files]

        ai_results = await self._fetch_ai_match_results(video_names, subtitle_names)
        return self._parse_ai_results(video_files, subtitle_files, ai_results)

    async def _fetch_ai_match_results(
        self, video_names: List[str], subtitle_names: List[str]
    ) -> Dict[str, Optional[str]]:
        """Magic function using deepseek-reasoner for batch matching"""

        class MatchingState(TypedDict):
            video_names: List[str]
            subtitle_names: List[str]
            matches: Dict[str, Optional[str]]

        def analyze_matches(state: MatchingState) -> MatchingState:
            """Analyze and generate matches using AI"""
            llm = ChatOpenAI(
                model=os.getenv("OAI_MODEL"),
                api_key=os.getenv("OAI_API_KEY"),
                base_url=os.getenv("OAI_BASE_URL"),
                temperature=0,
            )

            prompt = f"""
Match video files to subtitle files based on semantic similarity.

Video files:
{json.dumps(state["video_names"], indent=2)}

Subtitle files:
{json.dumps(state["subtitle_names"], indent=2)}

For each video file, find the best matching subtitle file (if any).
Output ONLY a JSON object with this exact format:
{{
  "video1.mp4": "subtitle1.srt",
  "video2.mkv": "subtitle2.ass",
  "video3.avi": null
}}

Rules:
- Match based on title, season/episode numbers, release info
- If no good match exists, use null
- Be conservative - only match when confident
- Output must be valid JSON only
"""

            response = llm.invoke(prompt)
            matches = _robust_json_parse(response.content, state["video_names"])
            state["matches"] = matches

            return state

        workflow = StateGraph(MatchingState)
        workflow.add_node("analyze", analyze_matches)
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", END)

        app = workflow.compile()

        initial_state = {
            "video_names": video_names,
            "subtitle_names": subtitle_names,
            "matches": {},
        }

        result = await app.ainvoke(initial_state)
        return result["matches"]

    def _parse_ai_results(
        self,
        video_files: List[VideoFile],
        subtitle_files: List[SubtitleFile],
        ai_matches: Dict[str, Optional[str]],
    ) -> List[MatchResult]:
        """Convert AI results to MatchResult objects"""
        results = []
        subtitle_map = {s.filename: s for s in subtitle_files}

        for video in video_files:
            matched_subtitle_name = ai_matches.get(video.filename)
            matched_subtitle = None
            similarity_score = 0.0
            match_method = "none"

            if matched_subtitle_name and matched_subtitle_name in subtitle_map:
                matched_subtitle = subtitle_map[matched_subtitle_name]
                similarity_score = 0.95  # AI match assumed high confidence
                match_method = "ai_semantic"

            candidates = [
                (subtitle_map[name], 0.95)
                for name in ai_matches.values()
                if name and name in subtitle_map
            ]

            result = MatchResult(
                video_file=video,
                matched_subtitle=matched_subtitle,
                similarity_score=similarity_score,
                all_candidates=candidates,
                match_method=match_method,
            )
            results.append(result)

        return results
