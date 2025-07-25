from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pythonLogs.constants import (
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


class LogSettings(BaseSettings):
    """If any ENV variable is omitted, it falls back to default values here"""

    level: Optional[LogLevel] = Field(default=LogLevel.INFO)
    timezone: Optional[str] = Field(default=DEFAULT_TIMEZONE)
    encoding: Optional[str] = Field(default=DEFAULT_ENCODING)
    appname: Optional[str] = Field(default="app")
    filename: Optional[str] = Field(default="app.log")
    directory: Optional[str] = Field(default="/app/logs")
    days_to_keep: Optional[int] = Field(default=DEFAULT_BACKUP_COUNT)
    date_format: Optional[str] = Field(default=DEFAULT_DATE_FORMAT)
    stream_handler: Optional[bool] = Field(default=True)
    show_location: Optional[bool] = Field(default=False)
    # Memory management
    max_loggers: Optional[int] = Field(default=100)
    logger_ttl_seconds: Optional[int] = Field(default=3600)

    # SizeRotatingLog
    max_file_size_mb: Optional[int] = Field(default=10)

    # TimedRotatingLog
    rotate_when: Optional[RotateWhen] = Field(default=RotateWhen.MIDNIGHT)
    rotate_at_utc: Optional[bool] = Field(default=True)
    rotate_file_sufix: Optional[str] = Field(default=DEFAULT_ROTATE_SUFFIX)

    model_config = SettingsConfigDict(env_prefix="LOG_", env_file=".env", extra="allow")


@lru_cache(maxsize=1)
def get_log_settings() -> LogSettings:
    """Get cached log settings instance to avoid repeated instantiation"""
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv()
        _dotenv_loaded = True
    return LogSettings()
