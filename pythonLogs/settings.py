# -*- encoding: utf-8 -*-
from enum import Enum
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class LogLevel(str, Enum):
    """log levels"""

    CRITICAL = "CRITICAL"
    CRIT = "CRIT"
    ERROR = "ERROR"
    WARNING = "WARNING"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


class LogSettings(BaseSettings):
    """If any ENV variable is omitted, it falls back to default values here"""

    load_dotenv()

    level: Optional[LogLevel] = Field(default=LogLevel.INFO)
    appname: Optional[str] = Field(default="app")
    directory: Optional[str] = Field(default="/app/logs")
    filename: Optional[str] = Field(default="app.log")
    encoding: Optional[str] = Field(default="UTF-8")
    date_format: Optional[str] = Field(default="%Y-%m-%dT%H:%M:%S")
    days_to_keep: Optional[int] = Field(default=30)
    timezone: Optional[str] = Field(default="UTC")
    stream_handler: Optional[bool] = Field(default=True)
    show_location: Optional[bool] = Field(default=False)

    # SizeRotatingLog
    max_file_size_mb: Optional[int] = Field(default=10)

    # TimedRotatingLog
    rotate_when: Optional[str] = Field(default="midnight")
    rotate_at_utc: Optional[bool] = Field(default=True)
    rotate_file_sufix: Optional[str] = Field(default="%Y%m%d")

    model_config = SettingsConfigDict(env_prefix="LOG_", env_file=".env", extra="allow")
