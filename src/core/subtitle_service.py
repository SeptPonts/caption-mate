import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import httpx

from .config import Config


@dataclass
class SubtitleInfo:
    """Information about a subtitle"""

    id: str
    language: str
    filename: str
    download_count: int
    rating: float
    release_name: str
    download_url: str
    file_size: int
    source: str = "unknown"

    @property
    def size_human(self) -> str:
        """Human readable file size"""
        if self.file_size == 0:
            return "0B"

        size = float(self.file_size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"


class OpenSubtitlesAPI:
    """OpenSubtitles REST API client"""

    BASE_URL = "https://api.opensubtitles.com/api/v1"

    def __init__(self, config: Config):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize HTTP client and authenticate"""
        headers = {
            "Api-Key": self.config.opensubtitles.api_key,
            "User-Agent": self.config.opensubtitles.user_agent,
            "Content-Type": "application/json",
        }

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL, headers=headers, timeout=30.0
        )

        # If username/password are provided, get JWT token
        if self.config.opensubtitles.username and self.config.opensubtitles.password:
            await self._authenticate()

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _authenticate(self) -> None:
        """Authenticate with username/password to get JWT token"""
        if not self._client:
            raise RuntimeError("Client not initialized")

        data = {
            "username": self.config.opensubtitles.username,
            "password": self.config.opensubtitles.password,
        }

        try:
            response = await self._client.post("/login", json=data)
            response.raise_for_status()

            result = response.json()
            self._token = result.get("token")

            if self._token:
                # Update client headers with token
                self._client.headers["Authorization"] = f"Bearer {self._token}"

        except Exception as e:
            raise ConnectionError(f"Authentication failed: {e}")

    async def search_subtitles(
        self,
        query: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_size: Optional[int] = None,
        imdb_id: Optional[str] = None,
        languages: Optional[List[str]] = None,
    ) -> List[SubtitleInfo]:
        """Search for subtitles"""
        if not self._client:
            raise RuntimeError("Client not initialized")

        params = {}

        # Query parameters
        if query:
            params["query"] = query
        if file_hash:
            params["moviehash"] = file_hash
        if file_size:
            params["moviebytesize"] = str(file_size)
        if imdb_id:
            params["imdb_id"] = imdb_id

        # Languages
        if languages:
            params["languages"] = ",".join(languages)
        elif self.config.subtitles.languages:
            params["languages"] = ",".join(self.config.subtitles.languages)

        try:
            response = await self._client.get("/subtitles", params=params)
            response.raise_for_status()

            result = response.json()
            subtitles = []

            for item in result.get("data", []):
                attrs = item.get("attributes", {})
                files = attrs.get("files", [])

                if not files:
                    continue

                file_info = files[0]  # Take the first file

                subtitle = SubtitleInfo(
                    id=str(attrs.get("subtitle_id", "")),
                    language=attrs.get("language", ""),
                    filename=file_info.get("file_name", ""),
                    download_count=attrs.get("download_count", 0),
                    rating=float(attrs.get("rating", 0.0)),
                    release_name=attrs.get("release", ""),
                    download_url=file_info.get("link", ""),
                    file_size=file_info.get("file_size", 0),
                    source="opensubtitles",
                )

                subtitles.append(subtitle)

            # Sort by download count and rating
            subtitles.sort(key=lambda x: (x.download_count, x.rating), reverse=True)
            return subtitles

        except Exception as e:
            raise RuntimeError(f"Search failed: {e}")

    async def download_subtitle(
        self, subtitle: SubtitleInfo, output_path: Path
    ) -> bool:
        """Download subtitle file"""
        if not self._client:
            raise RuntimeError("Client not initialized")

        if not subtitle.download_url:
            raise ValueError("No download URL available")

        try:
            # First, prepare download (required by OpenSubtitles API)
            download_data = {"file_id": int(subtitle.id)}

            response = await self._client.post("/download", json=download_data)
            response.raise_for_status()

            result = response.json()
            download_link = result.get("link")

            if not download_link:
                raise RuntimeError("No download link received")

            # Download the actual file
            async with httpx.AsyncClient() as download_client:
                file_response = await download_client.get(download_link)
                file_response.raise_for_status()

                # Create output directory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write file
                with open(output_path, "wb") as f:
                    f.write(file_response.content)

                return True

        except Exception as e:
            raise RuntimeError(f"Download failed: {e}")


class AssrtAPI:
    """ASSRT REST API client"""

    def __init__(self, config: Config):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize HTTP client"""
        headers = {
            "Authorization": f"Bearer {self.config.assrt.api_token}",
            "User-Agent": self.config.assrt.user_agent,
            "Content-Type": "application/json",
        }

        self._client = httpx.AsyncClient(
            base_url=self.config.assrt.base_url, headers=headers, timeout=30.0
        )

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_subtitles(
        self,
        query: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_size: Optional[int] = None,
        imdb_id: Optional[str] = None,
        languages: Optional[List[str]] = None,
    ) -> List[SubtitleInfo]:
        """Search for subtitles"""
        if not self._client:
            raise RuntimeError("Client not initialized")

        if not query:
            return []  # ASSRT requires text search

        params = {
            "q": query,
            "cnt": 15,  # Max allowed by ASSRT
        }

        try:
            response = await self._client.get("/v1/sub/search", params=params)
            response.raise_for_status()

            result = response.json()

            # Check for API errors
            if result.get("status") != 0:
                error_msg = result.get("errmsg", "Unknown error")
                raise RuntimeError(f"ASSRT API error: {error_msg}")

            subtitles = []
            subs_data = result.get("sub", {}).get("subs", [])

            for item in subs_data:
                # Skip if languages filter is specified and doesn't match
                sub_lang = self._map_language(item.get("lang", {}).get("desc", ""))
                if languages and sub_lang not in languages:
                    continue

                # Get download URL - requires detail call
                detail_url = f"/v1/sub/detail?id={item.get('id')}"
                detail_response = await self._client.get(detail_url)
                detail_response.raise_for_status()

                detail_result = detail_response.json()
                if detail_result.get("status") != 0:
                    continue

                detail_data = detail_result.get("sub", {})
                download_url = detail_data.get("url", "")

                subtitle = SubtitleInfo(
                    id=str(item.get("id", "")),
                    language=sub_lang,
                    filename=item.get("filename", ""),
                    download_count=int(item.get("download_times", 0)),
                    rating=float(item.get("rank", 0.0))
                    / 5.0
                    * 10.0,  # Convert 5-scale to 10-scale
                    release_name=item.get("release_site", ""),
                    download_url=download_url,
                    file_size=int(item.get("size", 0)),
                    source="assrt",
                )

                subtitles.append(subtitle)

            # Sort by download count and rating
            subtitles.sort(key=lambda x: (x.download_count, x.rating), reverse=True)
            return subtitles

        except Exception as e:
            raise RuntimeError(f"ASSRT search failed: {e}")

    def _map_language(self, assrt_lang: str) -> str:
        """Map ASSRT language codes to standard codes"""
        lang_mapping = {
            "简体中文": "zh-cn",
            "繁體中文": "zh-tw",
            "English": "en",
            "English(US)": "en",
            "English(UK)": "en-gb",
            "日本語": "ja",
            "한국어": "ko",
            "Français": "fr",
            "Deutsch": "de",
            "Español": "es",
            "Português": "pt",
            "Italiano": "it",
            "русский": "ru",
        }
        return lang_mapping.get(assrt_lang, assrt_lang.lower())

    async def download_subtitle(
        self, subtitle: SubtitleInfo, output_path: Path
    ) -> bool:
        """Download subtitle file"""
        if not self._client:
            raise RuntimeError("Client not initialized")

        if not subtitle.download_url:
            raise ValueError("No download URL available")

        try:
            # Download the file directly using the URL from detail API
            async with httpx.AsyncClient() as download_client:
                file_response = await download_client.get(subtitle.download_url)
                file_response.raise_for_status()

                # Create output directory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write file
                with open(output_path, "wb") as f:
                    f.write(file_response.content)

                return True

        except Exception as e:
            raise RuntimeError(f"ASSRT download failed: {e}")


class SubtitleService:
    """High-level subtitle service"""

    def __init__(self, config: Config):
        self.config = config
        self.opensubtitles_api = OpenSubtitlesAPI(config)
        self.assrt_api = AssrtAPI(config)

    @staticmethod
    def calculate_file_hash(file_path: str) -> Optional[str]:
        """Calculate OpenSubtitles-compatible hash for a video file"""
        try:
            with open(file_path, "rb") as f:
                # Get file size
                f.seek(0, os.SEEK_END)
                filesize = f.tell()

                if filesize < 65536 * 2:
                    return None

                # Calculate hash as per OpenSubtitles spec
                hash_value = filesize

                # Read first and last 64KB
                for offset in [0, max(0, filesize - 65536)]:
                    f.seek(offset)
                    data = f.read(65536)

                    # Process in 8-byte chunks
                    for i in range(0, len(data), 8):
                        chunk = data[i : i + 8]
                        if len(chunk) == 8:
                            hash_value += int.from_bytes(
                                chunk, byteorder="little", signed=False
                            )
                            hash_value &= 0xFFFFFFFFFFFFFFFF  # Keep it 64-bit

                return f"{hash_value:016x}"

        except Exception:
            return None

    def extract_title_from_filename(self, filename: str) -> str:
        """Extract movie/show title from filename"""
        # Remove file extension
        name = Path(filename).stem

        # Remove common video tags and year patterns
        import re

        # Remove year patterns like (2023), [2023]
        name = re.sub(r"[\(\[](?:19|20)\d{2}[\)\]]", "", name)

        # Remove quality indicators
        patterns = [
            r"\b(?:1080p|720p|480p|4K|HD|BluRay|BrRip|DVDRip|WEBRip|HDTV)\b",
            r"\b(?:x264|x265|HEVC|DivX|XviD)\b",
            r"\b(?:AAC|AC3|DTS|MP3)\b",
            r"\b(?:YIFY|RARBG|ETRG)\b",
        ]

        for pattern in patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)

        # Replace dots, underscores with spaces
        name = re.sub(r"[._-]+", " ", name)

        # Clean up multiple spaces
        name = re.sub(r"\s+", " ", name).strip()

        return name

    def generate_subtitle_filename(
        self, video_filename: str, language: str, format_ext: str
    ) -> str:
        """Generate subtitle filename based on naming pattern"""
        video_stem = Path(video_filename).stem

        return self.config.subtitles.naming_pattern.format(
            filename=video_stem, lang=language, ext=format_ext
        )

    async def search_for_video(
        self, video_path: str, video_size: int, providers: Optional[List[str]] = None
    ) -> List[SubtitleInfo]:
        """Search subtitles for a specific video file using multiple providers"""
        if providers is None:
            providers = ["assrt", "opensubtitles"]

        all_results = []
        filename = Path(video_path).name
        title = self.extract_title_from_filename(filename)

        # Try ASSRT first (text search, good for Chinese content)
        if "assrt" in providers and self.config.assrt.api_token and title:
            try:
                async with self.assrt_api:
                    results = await self.assrt_api.search_subtitles(
                        query=title, languages=self.config.subtitles.languages
                    )
                    if results:
                        all_results.extend(results)
            except Exception as e:
                # Log error but continue
                print(f"ASSRT search failed: {e}")

        # Try OpenSubtitles (supports hash-based search)
        if "opensubtitles" in providers and self.config.opensubtitles.api_key:
            try:
                async with self.opensubtitles_api:
                    # 1. Hash-based search (most accurate)
                    file_hash = self.calculate_file_hash(video_path)
                    if file_hash:
                        results = await self.opensubtitles_api.search_subtitles(
                            file_hash=file_hash, file_size=video_size
                        )
                        if results:
                            all_results.extend(results)

                    # 2. Filename-based search if no hash results from OpenSubtitles
                    if title and not any(
                        r.source == "opensubtitles" for r in all_results
                    ):
                        results = await self.opensubtitles_api.search_subtitles(
                            query=title
                        )
                        if results:
                            all_results.extend(results)
            except Exception as e:
                # Log error but continue with other providers
                print(f"OpenSubtitles search failed: {e}")

        # Remove duplicates and sort by quality
        seen = set()
        unique_results = []
        for result in all_results:
            key = (result.language, result.filename, result.file_size)
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        # Sort by download count and rating
        unique_results.sort(key=lambda x: (x.download_count, x.rating), reverse=True)
        return unique_results

    async def download_best_subtitle(
        self, video_path: str, video_size: int, output_dir: Optional[str] = None
    ) -> Optional[Path]:
        """Find and download the best subtitle for a video"""
        # Search for subtitles
        subtitles = await self.search_for_video(video_path, video_size)

        if not subtitles:
            return None

        # Filter by preferred formats
        preferred_subtitles = [
            s
            for s in subtitles
            if any(
                s.filename.lower().endswith(f".{fmt}")
                for fmt in self.config.subtitles.formats
            )
        ]

        if preferred_subtitles:
            best_subtitle = preferred_subtitles[0]
        else:
            best_subtitle = subtitles[0]

        # Determine output path
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(video_path).parent

        # Generate subtitle filename
        video_filename = Path(video_path).name
        subtitle_ext = Path(best_subtitle.filename).suffix.lstrip(".")

        subtitle_filename = self.generate_subtitle_filename(
            video_filename, best_subtitle.language, subtitle_ext
        )

        full_output_path = output_path / subtitle_filename

        # Determine which API to use based on source
        success = await self._download_subtitle_with_provider(
            best_subtitle, full_output_path
        )

        if success:
            return full_output_path

        return None

    async def _download_subtitle_with_provider(
        self, subtitle: SubtitleInfo, output_path: Path
    ) -> bool:
        """Download subtitle using the appropriate provider"""
        # Determine provider from source field
        if subtitle.source == "assrt":
            try:
                async with self.assrt_api:
                    return await self.assrt_api.download_subtitle(subtitle, output_path)
            except Exception as e:
                print(f"ASSRT download failed: {e}")
                return False
        else:
            # Default to OpenSubtitles
            try:
                async with self.opensubtitles_api:
                    return await self.opensubtitles_api.download_subtitle(
                        subtitle, output_path
                    )
            except Exception as e:
                print(f"OpenSubtitles download failed: {e}")
                return False
