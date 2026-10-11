from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExternalPreparationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[2] / ".env",
        env_prefix="PYTEST_RUN_CONTEXT_EXTERNAL_",
        extra="ignore",
    )

    # This explicit path is disposable example data, not a security-sensitive temporary file.
    db: Path = Path("/tmp/pytest-run-context-external-preparation.sqlite3")  # noqa: S108


settings = ExternalPreparationSettings()
