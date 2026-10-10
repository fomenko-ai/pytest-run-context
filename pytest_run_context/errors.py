class RunNotFoundError(LookupError):
    """Raised when a requested run does not exist in storage."""


class InvalidStoredRunError(ValueError):
    """Raised when persisted run data cannot be restored safely."""


class RunAlreadyFinishedError(RuntimeError):
    """Raised when an operation requires an active run."""
