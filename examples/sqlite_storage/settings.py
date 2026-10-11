from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class SQLiteSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[2] / ".env",
        env_prefix="PYTEST_RUN_CONTEXT_SQLITE_",
        extra="ignore",
    )

    # This explicit path is disposable example data, not a security-sensitive temporary file.
    path: Path = Path("/tmp/pytest-run-context-example/runs.sqlite3")  # noqa: S108


settings = SQLiteSettings()
