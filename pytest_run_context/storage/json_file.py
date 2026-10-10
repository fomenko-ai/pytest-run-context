import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Union

from .base import RunAlreadyExistsError, StoredRun


class JSONStorage:
    """One JSON file per run. Intended for single-process, sequential pytest runs."""

    def __init__(self, directory: Union[str, Path]) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        # IDs are UUIDs or user strings; use a stable safe filename.
        import hashlib

        return self._directory / (hashlib.sha256(run_id.encode()).hexdigest() + ".json")

    def _write(self, path: Path, run_id: str, info: str, custom: str) -> None:
        payload = json.dumps({"run_id": run_id, "info": info, "custom": custom})
        name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=self._directory, encoding="utf-8", delete=False
            ) as stream:
                name = stream.name
                stream.write(payload)
            os.replace(name, path)
        finally:
            if name is not None and os.path.exists(name):
                os.unlink(name)

    def create_run(self, run_id: str, info: str, custom: str) -> None:
        path = self._path(run_id)
        # Exclusive reservation prevents silently overwriting existing runs.
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump({"run_id": run_id, "info": info, "custom": custom}, stream)
        except FileExistsError as exc:
            raise RunAlreadyExistsError(run_id) from exc

    def save_run(self, run_id: str, info: str, custom: str) -> None:
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(run_id)
        self._write(path, run_id, info, custom)

    def load_run(self, run_id: str) -> Optional[StoredRun]:
        path = self._path(run_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
        return StoredRun(payload["info"], payload["custom"])

    def finish_run(self, run_id: str, info: str, custom: str) -> None:
        self.save_run(run_id, info, custom)

    def close(self) -> None:
        pass
