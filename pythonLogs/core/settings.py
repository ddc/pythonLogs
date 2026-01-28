from dotenv import load_dotenv
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pythonLogs.core.constants import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_DATE_FORMAT,
    DEFAULT_ENCODING,
    DEFAULT_ROTATE_SUFFIX,
    DEFAULT_TIMEZONE,
    LogLevel,
    RotateWhen,
)

# Lazy loading flag for dotenv
_dotenv_loaded = False


def _ensure_dotenv_loaded() -> None:
    """Ensure dotenv is loaded only once."""
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv()
        _dotenv_loaded = True


class LogSettings(BaseSettings):
    """If any ENV variable is omitted, it falls back to default values here"""

    model_config = SettingsConfigDict(env_prefix="LOG_", env_file=".env", extra="allow")

    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level (debug, info, warning, error, critical)",
    )
    timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        description="Timezone for log timestamps (e.g., 'UTC', 'localtime', 'America/New_York')",
    )
    encoding: str = Field(
        default=DEFAULT_ENCODING,
        description="File encoding for log files",
    )
    appname: str = Field(
        default="app",
        description="Application name used as logger name",
    )
    filename: str = Field(
        default="app.log",
        description="Log filename",
    )
    directory: str = Field(
        default="./logs",
        description="Directory path for log files",
    )
    days_to_keep: int = Field(
        default=DEFAULT_BACKUP_COUNT,
        description="Number of days to keep old log files",
    )
    date_format: str = Field(
        default=DEFAULT_DATE_FORMAT,
        description="Date format string for log timestamps",
    )
    stream_handler: bool = Field(
        default=True,
        description="Enable console output via StreamHandler",
    )
    show_location: bool = Field(
        default=False,
        description="Show source file location (filename, function, line number) in logs",
    )

    # Memory management
    max_loggers: int = Field(
        default=100,
        description="Maximum number of loggers to track in memory",
    )
    logger_ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live in seconds for logger references",
    )

    # SizeRotatingLog
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum log file size in megabytes before rotation",
    )

    # TimedRotatingLog
    rotate_when: RotateWhen = Field(
        default=RotateWhen.MIDNIGHT,
        description="When to rotate log files (midnight, hourly, daily, weekly)",
    )
    rotate_at_utc: bool = Field(
        default=True,
        description="Use UTC time for rotation timing",
    )
    rotate_file_sufix: str = Field(
        default=DEFAULT_ROTATE_SUFFIX,
        description="Date suffix format for rotated log files",
    )


@lru_cache(maxsize=1)
def get_log_settings() -> LogSettings:
    """Get cached log settings instance to avoid repeated instantiation."""
    _ensure_dotenv_loaded()
    return LogSettings()


def clear_settings_cache(reload_env: bool = True) -> None:
    """Clear log settings cache. Next call to get_log_settings() will create fresh instance.

    Args:
        reload_env: If True, also reset dotenv loaded flag to reload .env on next access
    """
    global _dotenv_loaded
    get_log_settings.cache_clear()
    if reload_env:
        _dotenv_loaded = False
