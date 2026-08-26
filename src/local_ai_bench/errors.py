class BenchError(Exception):
    """Expected error that should be shown without a traceback."""


class ConfigError(BenchError):
    """Invalid suite or model configuration."""


class PreparationError(BenchError):
    """Runtime or model preparation failed."""


class ResultValidationError(BenchError):
    """A result directory is incomplete or inconsistent."""

