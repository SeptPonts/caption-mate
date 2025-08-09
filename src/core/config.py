from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union

import yaml


@dataclass
class OpenSubtitlesConfig:
    api_key: Optional[str] = None
    user_agent: str = "caption-mate-v1.0"
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class AssrtConfig:
    api_token: Optional[str] = None
    base_url: str = "https://api.assrt.net"
    user_agent: str = "caption-mate-v1.0"


@dataclass
class NASConfig:
    protocol: str = "smb"
    host: Optional[str] = None
    port: int = 445
    username: Optional[str] = None
    password: Optional[str] = None
    domain: str = "WORKGROUP"


@dataclass
class SubtitlesConfig:
    languages: List[str] = field(default_factory=lambda: ["zh-cn", "en"])
    formats: List[str] = field(default_factory=lambda: ["srt", "ass"])
    output_dir: Optional[str] = None
    naming_pattern: str = "{filename}.{lang}.{ext}"


@dataclass
class ScanningConfig:
    video_extensions: List[str] = field(
        default_factory=lambda: [
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".m4v",
            ".flv",
            ".webm",
        ]
    )
    recursive: bool = True
    skip_existing: bool = True
    cache_duration: int = 3600


@dataclass
class Config:
    opensubtitles: OpenSubtitlesConfig = field(default_factory=OpenSubtitlesConfig)
    assrt: AssrtConfig = field(default_factory=AssrtConfig)
    nas: NASConfig = field(default_factory=NASConfig)
    subtitles: SubtitlesConfig = field(default_factory=SubtitlesConfig)
    scanning: ScanningConfig = field(default_factory=ScanningConfig)

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get default config file path"""
        return Path.home() / ".caption-mate" / "config.yaml"

    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "Config":
        """Load config from file"""
        if config_path is None:
            config_path = cls.get_default_config_path()
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            return cls(
                opensubtitles=OpenSubtitlesConfig(**data.get("opensubtitles", {})),
                assrt=AssrtConfig(**data.get("assrt", {})),
                nas=NASConfig(**data.get("nas", {})),
                subtitles=SubtitlesConfig(**data.get("subtitles", {})),
                scanning=ScanningConfig(**data.get("scanning", {})),
            )
        except Exception as e:
            raise ValueError(f"Error loading config from {config_path}: {e}")

    def save(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Save config to file"""
        if config_path is None:
            config_path = self.get_default_config_path()
        else:
            config_path = Path(config_path)

        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "opensubtitles": {
                "api_key": self.opensubtitles.api_key,
                "user_agent": self.opensubtitles.user_agent,
                "username": self.opensubtitles.username,
                "password": self.opensubtitles.password,
            },
            "assrt": {
                "api_token": self.assrt.api_token,
                "base_url": self.assrt.base_url,
                "user_agent": self.assrt.user_agent,
            },
            "nas": {
                "protocol": self.nas.protocol,
                "host": self.nas.host,
                "port": self.nas.port,
                "username": self.nas.username,
                "password": self.nas.password,
                "domain": self.nas.domain,
            },
            "subtitles": {
                "languages": self.subtitles.languages,
                "formats": self.subtitles.formats,
                "output_dir": self.subtitles.output_dir,
                "naming_pattern": self.subtitles.naming_pattern,
            },
            "scanning": {
                "video_extensions": self.scanning.video_extensions,
                "recursive": self.scanning.recursive,
                "skip_existing": self.scanning.skip_existing,
                "cache_duration": self.scanning.cache_duration,
            },
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)

    def set_value(self, key: str, value: Any) -> None:
        """Set a config value using dot notation (e.g., 'nas.host')"""
        keys = key.split(".")
        if len(keys) != 2:
            raise ValueError("Key must be in format 'section.key'")

        section_name, key_name = keys
        section = getattr(self, section_name, None)
        if section is None:
            raise ValueError(f"Unknown config section: {section_name}")

        if not hasattr(section, key_name):
            raise ValueError(f"Unknown config key: {key}")

        # Convert string values to appropriate types
        field_type = type(getattr(section, key_name))
        if field_type is bool:
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes", "on")
        elif field_type is int:
            value = int(value)
        elif field_type is list and isinstance(value, str):
            # Handle comma-separated list values
            value = [item.strip() for item in value.split(",")]

        setattr(section, key_name, value)

    def get_value(self, key: str) -> Any:
        """Get a config value using dot notation"""
        keys = key.split(".")
        if len(keys) != 2:
            raise ValueError("Key must be in format 'section.key'")

        section_name, key_name = keys
        section = getattr(self, section_name, None)
        if section is None:
            raise ValueError(f"Unknown config section: {section_name}")

        return getattr(section, key_name, None)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate OpenSubtitles config
        if not self.opensubtitles.api_key:
            errors.append("OpenSubtitles API key is required")

        # Validate NAS config
        if not self.nas.host:
            errors.append("NAS host is required")
        if self.nas.protocol not in ["smb", "nfs", "sftp"]:
            errors.append("NAS protocol must be 'smb', 'nfs', or 'sftp'")

        return errors
