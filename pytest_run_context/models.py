from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RunInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class BaseCustomContext(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    def on_run_start(self, info: RunInfo) -> None:
        pass

    def on_run_finish(self, info: RunInfo) -> None:
        pass
