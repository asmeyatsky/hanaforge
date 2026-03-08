"""LocalFileStorageAdapter — dev-mode local filesystem implementation of FileStoragePort.

Stores files under /tmp/hanaforge-storage/ to keep the development loop free
of cloud dependencies.  A GCS-backed adapter will replace this for production.
"""

from __future__ import annotations

import os
from pathlib import Path


_BASE_DIR = Path("/tmp/hanaforge-storage")


class LocalFileStorageAdapter:
    """Implements FileStoragePort using the local filesystem."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or _BASE_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve a storage path to an absolute filesystem path."""
        resolved = (self._base_dir / path).resolve()
        # Prevent path traversal outside the base directory
        if not str(resolved).startswith(str(self._base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    async def upload(self, file_bytes: bytes, path: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes)
        return str(path)

    async def download(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_bytes()

    async def delete(self, path: str) -> bool:
        target = self._resolve(path)
        if target.exists():
            target.unlink()
            return True
        return False

    async def list_files(self, prefix: str) -> list[str]:
        prefix_path = self._resolve(prefix)
        if not prefix_path.exists():
            return []

        base_str = str(self._base_dir.resolve())
        results: list[str] = []

        if prefix_path.is_dir():
            for item in prefix_path.rglob("*"):
                if item.is_file():
                    relative = str(item.resolve())[len(base_str) + 1 :]
                    results.append(relative)
        else:
            # prefix_path is a file pattern — list siblings matching the prefix
            parent = prefix_path.parent
            prefix_name = prefix_path.name
            if parent.exists():
                for item in parent.iterdir():
                    if item.is_file() and item.name.startswith(prefix_name):
                        relative = str(item.resolve())[len(base_str) + 1 :]
                        results.append(relative)

        return sorted(results)
