from pathlib import Path


class StorageService:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if self.root != candidate and self.root not in candidate.parents:
            raise ValueError("Storage path escapes configured root")
        return candidate

    def save_bytes(self, relative_path: str, content: bytes) -> str:
        destination = self._resolve(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return relative_path

    def open_path(self, relative_path: str) -> Path:
        path = self._resolve(relative_path)
        if not path.is_file():
            raise FileNotFoundError(relative_path)
        return path

    def exists(self, relative_path: str | None) -> bool:
        return bool(relative_path) and self._resolve(relative_path).is_file()
