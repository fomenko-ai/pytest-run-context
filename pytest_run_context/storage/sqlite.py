import sqlite3
from pathlib import Path
from typing import Optional, Union

from .base import RunAlreadyExistsError, StoredRun


class SQLiteStorage:
    def __init__(self, database: Union[str, Path]) -> None:
        self._db = sqlite3.connect(str(database))
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, info TEXT NOT NULL, custom TEXT NOT NULL)"
        )
        self._db.commit()

    def create_run(self, run_id: str, info: str, custom: str) -> None:
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO runs VALUES (?, ?, ?)", (run_id, info, custom)
                )
        except sqlite3.IntegrityError as exc:
            raise RunAlreadyExistsError(run_id) from exc

    def save_run(self, run_id: str, info: str, custom: str) -> None:
        with self._db:
            cursor = self._db.execute(
                "UPDATE runs SET info=?, custom=? WHERE run_id=?",
                (info, custom, run_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(run_id)

    def load_run(self, run_id: str) -> Optional[StoredRun]:
        row = self._db.execute(
            "SELECT info, custom FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()
        return StoredRun(*row) if row else None

    def finish_run(self, run_id: str, info: str, custom: str) -> None:
        self.save_run(run_id, info, custom)

    def close(self) -> None:
        self._db.close()
