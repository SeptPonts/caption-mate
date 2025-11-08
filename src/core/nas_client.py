import fnmatch
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from smb.SMBConnection import SMBConnection

from .config import Config


@dataclass
class FileEntry:
    """Represents a file or directory entry"""

    name: str
    path: str
    is_dir: bool
    size: int = 0
    modified_time: Optional[datetime] = None

    @property
    def size_human(self) -> str:
        """Human readable file size"""
        if self.size == 0:
            return "0B"

        size = float(self.size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"


class NASClient:
    """NAS client for file operations"""

    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[SMBConnection] = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self) -> None:
        """Establish connection to NAS"""
        if self.config.nas.protocol != "smb":
            raise NotImplementedError(
                f"Protocol {self.config.nas.protocol} not yet implemented"
            )

        try:
            self._connection = SMBConnection(
                username=self.config.nas.username or "",
                password=self.config.nas.password or "",
                my_name="caption-mate",  # Client name
                remote_name=self.config.nas.host,  # Server name
                domain=self.config.nas.domain or "WORKGROUP",
                use_ntlm_v2=True,
            )

            # Connect to the server
            connected = self._connection.connect(
                self.config.nas.host, self.config.nas.port or 445
            )

            if not connected:
                raise ConnectionError("Failed to establish SMB connection")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to NAS: {e}")

    def disconnect(self) -> None:
        """Close NAS connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def test_connection(self) -> bool:
        """Test if connection to NAS is working"""
        try:
            self.connect()
            # Try to list shares
            self.list_shares()
            return True  # If we get here, connection works
        except Exception:
            return False

    def list_shares(self) -> List[str]:
        """List available shares on the NAS"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            shares = self._connection.listShares()
            return [share.name for share in shares if not share.name.endswith("$")]
        except Exception as e:
            raise ConnectionError(f"Failed to list shares: {e}")

    def _parse_path(self, path: str) -> tuple[str, str]:
        """Parse path into share name and directory path"""
        path = path.strip("/")
        if not path:
            raise ValueError("Path must specify a share")

        parts = path.split("/", 1)
        share_name = parts[0]
        dir_path = parts[1] if len(parts) > 1 else "/"

        return share_name, dir_path

    def _parse_file_path(self, file_path: str) -> tuple[str, str]:
        """Parse file path into share name and file path relative to share"""
        path = file_path.strip("/")
        if not path:
            raise ValueError("File path must specify a share and file")

        parts = path.split("/", 1)
        share_name = parts[0]

        if len(parts) < 2:
            raise ValueError("File path must include filename")

        # For files, we need the full path relative to share (including filename)
        relative_path = parts[1]

        return share_name, relative_path

    def list_directory(
        self, path: str, pattern: Optional[str] = None
    ) -> List[FileEntry]:
        """List files and directories in the given path"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            if path == "/":
                # List shares at root
                shares = self.list_shares()
                entries = []
                for share in shares:
                    entries.append(
                        FileEntry(name=share, path=f"/{share}", is_dir=True, size=0)
                    )
                return entries

            share_name, dir_path = self._parse_path(path)

            try:
                file_list = self._connection.listPath(share_name, dir_path)
                entries = []

                for file_info in file_list:
                    # Skip . and .. entries
                    if file_info.filename in [".", ".."]:
                        continue

                    if pattern and not fnmatch.fnmatch(file_info.filename, pattern):
                        continue

                    is_dir = file_info.isDirectory
                    size = 0 if is_dir else file_info.file_size
                    modified_time = datetime.fromtimestamp(file_info.last_write_time)

                    item_path = f"{path.rstrip('/')}/{file_info.filename}"

                    entries.append(
                        FileEntry(
                            name=file_info.filename,
                            path=item_path,
                            is_dir=is_dir,
                            size=size,
                            modified_time=modified_time,
                        )
                    )

                return sorted(entries, key=lambda x: (not x.is_dir, x.name.lower()))

            except Exception as e:
                raise OSError(f"Failed to list directory {path}: {e}")

        except Exception as e:
            raise OSError(f"Failed to access path {path}: {e}")

    def get_directory_tree(
        self, path: str, max_depth: int = 3, current_depth: int = 0
    ) -> Dict[str, Any]:
        """Get directory tree structure"""
        if current_depth >= max_depth:
            return {}

        try:
            entries = self.list_directory(path)
            tree = {}

            for entry in entries:
                if entry.is_dir:
                    subtree = self.get_directory_tree(
                        entry.path, max_depth, current_depth + 1
                    )
                    tree[entry.name] = {
                        "type": "directory",
                        "path": entry.path,
                        "children": subtree,
                    }
                else:
                    tree[entry.name] = {
                        "type": "file",
                        "path": entry.path,
                        "size": entry.size,
                        "modified": entry.modified_time,
                    }

            return tree

        except Exception as e:
            raise OSError(f"Failed to build tree for {path}: {e}")

    def path_exists(self, path: str) -> bool:
        """Check if path exists on NAS"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            if path == "/":
                return True

            share_name, dir_path = self._parse_path(path)

            # Try to get file attributes
            try:
                self._connection.getAttributes(share_name, dir_path)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            if path == "/":
                return True

            share_name, dir_path = self._parse_path(path)

            try:
                attrs = self._connection.getAttributes(share_name, dir_path)
                return attrs.isDirectory
            except Exception:
                return False
        except Exception:
            return False

    def scan_video_files(self, path: str, recursive: bool = True) -> List[FileEntry]:
        """Scan for video files in the given path"""
        video_files = []
        extensions = self.config.scanning.video_extensions

        def should_include_file(name: str) -> bool:
            return any(name.lower().endswith(ext.lower()) for ext in extensions)

        try:
            entries = self.list_directory(path)

            for entry in entries:
                if entry.is_dir and recursive:
                    # Recursively scan subdirectories
                    try:
                        sub_files = self.scan_video_files(entry.path, recursive)
                        video_files.extend(sub_files)
                    except Exception:
                        # Skip directories we can't access
                        continue
                elif not entry.is_dir and should_include_file(entry.name):
                    video_files.append(entry)

            return sorted(video_files, key=lambda x: x.path)

        except Exception as e:
            raise OSError(f"Failed to scan video files in {path}: {e}")

    def rename_file(self, old_path: str, new_path: str) -> bool:
        """Rename a file on the NAS"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            # Parse file paths correctly
            old_share, old_file_path = self._parse_file_path(old_path)
            new_share, new_file_path = self._parse_file_path(new_path)

            # Must be in the same share
            if old_share != new_share:
                raise ValueError("Cannot rename across different shares")

            # Use SMB rename operation with correct file paths
            self._connection.rename(old_share, old_file_path, new_file_path)
            return True

        except Exception as e:
            raise OSError(f"Failed to rename {old_path} to {new_path}: {e}")

    def create_directory(self, path: str) -> bool:
        """Create a directory on the NAS"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            share_name, dir_path = self._parse_path(path)
            self._connection.createDirectory(share_name, dir_path)
            return True

        except Exception as e:
            # Directory might already exist
            if "STATUS_OBJECT_NAME_COLLISION" in str(e):
                return True
            raise OSError(f"Failed to create directory {path}: {e}")

    def upload_file(self, local_path: str, nas_path: str) -> bool:
        """Upload a local file to NAS"""
        try:
            if not self._connection:
                raise RuntimeError("Not connected to NAS")

            from pathlib import Path as LocalPath

            local_file = LocalPath(local_path)
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            if not local_file.is_file():
                raise ValueError(f"Not a file: {local_path}")

            # Determine target path
            if self.is_directory(nas_path):
                # Upload to directory with same filename
                target_path = f"{nas_path.rstrip('/')}/{local_file.name}"
            else:
                # Use as full path
                target_path = nas_path

            share_name, file_path = self._parse_file_path(target_path)

            # Ensure parent directory exists
            parent_dir = "/".join(file_path.split("/")[:-1])
            if parent_dir:
                try:
                    parent_path = f"/{share_name}/{parent_dir}"
                    if not self.path_exists(parent_path):
                        self.create_directory(parent_path)
                except Exception:
                    pass  # Directory might exist or creation failed

            # Upload file
            with open(local_file, "rb") as f:
                self._connection.storeFile(share_name, file_path, f)

            return True

        except Exception as e:
            raise OSError(f"Failed to upload {local_path} to {nas_path}: {e}")

    def upload_directory(
        self, local_path: str, nas_path: str, recursive: bool = True
    ) -> Dict[str, int]:
        """Upload a local directory to NAS"""
        try:
            from pathlib import Path as LocalPath

            local_dir = LocalPath(local_path)
            if not local_dir.exists():
                raise FileNotFoundError(f"Local directory not found: {local_path}")

            if not local_dir.is_dir():
                raise ValueError(f"Not a directory: {local_path}")

            stats = {"uploaded": 0, "skipped": 0, "failed": 0}

            # Ensure target directory exists
            if not self.path_exists(nas_path):
                self.create_directory(nas_path)

            # Upload files
            for item in local_dir.iterdir():
                if item.is_file():
                    try:
                        target = f"{nas_path.rstrip('/')}/{item.name}"
                        self.upload_file(str(item), target)
                        stats["uploaded"] += 1
                    except Exception:
                        stats["failed"] += 1
                elif item.is_dir() and recursive:
                    try:
                        target = f"{nas_path.rstrip('/')}/{item.name}"
                        sub_stats = self.upload_directory(str(item), target, recursive)
                        for key in stats:
                            stats[key] += sub_stats[key]
                    except Exception:
                        stats["failed"] += 1

            return stats

        except Exception as e:
            raise OSError(f"Failed to upload directory {local_path} to {nas_path}: {e}")
