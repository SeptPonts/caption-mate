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
        dir_path = "/" + parts[1] if len(parts) > 1 else "/"

        return share_name, dir_path

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
