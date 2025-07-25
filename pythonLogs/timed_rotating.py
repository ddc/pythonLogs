import logging.handlers
import os
from typing import Optional
from pythonLogs.log_utils import (
    check_directory_permissions,
    check_filename_instance,
    cleanup_logger_handlers,
    get_level,
    get_log_path,
    get_logger_and_formatter,
    get_stream_handler,
    gzip_file_with_sufix,
    remove_old_logs,
)
from pythonLogs.memory_utils import register_logger_weakref
from pythonLogs.settings import get_log_settings
from pythonLogs.thread_safety import auto_thread_safe


@auto_thread_safe(['init', '_cleanup_logger'])
class TimedRotatingLog:
    """
    Time-based rotating logger with context manager support for automatic resource cleanup.

    Current 'rotating_when' events supported for TimedRotatingLogs:
    Use RotateWhen enum values:
        RotateWhen.MIDNIGHT - roll over at midnight
        RotateWhen.MONDAY through RotateWhen.SUNDAY - roll over on specific days
        RotateWhen.HOURLY - roll over every hour
        RotateWhen.DAILY - roll over daily
    """

    def __init__(
        self,
        level: Optional[str] = None,
        name: Optional[str] = None,
        directory: Optional[str] = None,
        filenames: Optional[list | tuple] = None,
        when: Optional[str] = None,
        sufix: Optional[str] = None,
        daystokeep: Optional[int] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        streamhandler: Optional[bool] = None,
        showlocation: Optional[bool] = None,
        rotateatutc: Optional[bool] = None,
    ):
        _settings = get_log_settings()
        self.level = get_level(level or _settings.level)
        self.appname = name or _settings.appname
        self.directory = directory or _settings.directory
        self.filenames = filenames or (_settings.filename,)
        self.when = when or _settings.rotate_when
        self.sufix = sufix or _settings.rotate_file_sufix
        self.daystokeep = daystokeep or _settings.days_to_keep
        self.encoding = encoding or _settings.encoding
        self.datefmt = datefmt or _settings.date_format
        self.timezone = timezone or _settings.timezone
        self.streamhandler = streamhandler or _settings.stream_handler
        self.showlocation = showlocation or _settings.show_location
        self.rotateatutc = rotateatutc or _settings.rotate_at_utc
        self.logger = None

    def init(self):
        check_filename_instance(self.filenames)
        check_directory_permissions(self.directory)

        logger, formatter = get_logger_and_formatter(self.appname, self.datefmt, self.showlocation, self.timezone)
        logger.setLevel(self.level)

        for file in self.filenames:
            log_file_path = get_log_path(self.directory, file)

            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_file_path,
                encoding=self.encoding,
                when=self.when,
                utc=self.rotateatutc,
                backupCount=self.daystokeep,
            )
            file_handler.suffix = self.sufix
            file_handler.rotator = GZipRotatorTimed(self.directory, self.daystokeep)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self.level)
            logger.addHandler(file_handler)

        if self.streamhandler:
            stream_hdlr = get_stream_handler(self.level, formatter)
            logger.addHandler(stream_hdlr)

        self.logger = logger
        # Register weak reference for memory tracking
        register_logger_weakref(logger)
        return logger

    def __enter__(self):
        """Context manager entry."""
        if not hasattr(self, 'logger') or self.logger is None:
            self.init()
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        if hasattr(self, 'logger'):
            self._cleanup_logger(self.logger)

    def _cleanup_logger(self, logger: logging.Logger) -> None:
        """Clean up logger resources by closing all handlers with thread safety."""
        cleanup_logger_handlers(logger)

    @staticmethod
    def cleanup_logger(logger: logging.Logger) -> None:
        """Static method for cleaning up logger resources (backward compatibility)."""
        cleanup_logger_handlers(logger)


class GZipRotatorTimed:
    def __init__(self, dir_logs: str, days_to_keep: int):
        self.dir = dir_logs
        self.days_to_keep = days_to_keep

    def __call__(self, source: str, dest: str) -> None:
        remove_old_logs(self.dir, self.days_to_keep)
        sufix = os.path.splitext(dest)[1].replace(".", "")
        gzip_file_with_sufix(source, sufix)
