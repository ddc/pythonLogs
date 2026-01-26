import logging.handlers
import os
from pathlib import Path
from pythonLogs.core.constants import MB_TO_BYTES
from pythonLogs.core.log_utils import (
    check_directory_permissions,
    check_filename_instance,
    cleanup_logger_handlers,
    get_level,
    get_log_path,
    get_logger_and_formatter,
    get_stream_handler,
    gzip_file_with_sufix,
    remove_old_logs,
    write_stderr,
)
from pythonLogs.core.memory_utils import register_logger_weakref
from pythonLogs.core.settings import get_log_settings
from pythonLogs.core.thread_safety import auto_thread_safe
import re


@auto_thread_safe(['init'])
class SizeRotatingLog:
    """Size-based rotating logger with context manager support for automatic resource cleanup."""

    def __init__(
        self,
        level: str | None = None,
        name: str | None = None,
        directory: str | None = None,
        filenames: list | tuple | None = None,
        maxmbytes: int | None = None,
        daystokeep: int | None = None,
        encoding: str | None = None,
        datefmt: str | None = None,
        timezone: str | None = None,
        streamhandler: bool | None = None,
        showlocation: bool | None = None,
    ):
        _settings = get_log_settings()
        self.level = get_level(level or _settings.level)
        self.appname = name or _settings.appname
        self.directory = directory or _settings.directory
        self.filenames = filenames or (_settings.filename,)
        self.maxmbytes = maxmbytes or _settings.max_file_size_mb
        self.daystokeep = daystokeep or _settings.days_to_keep
        self.encoding = encoding or _settings.encoding
        self.datefmt = datefmt or _settings.date_format
        self.timezone = timezone or _settings.timezone
        self.streamhandler = streamhandler or _settings.stream_handler
        self.showlocation = showlocation or _settings.show_location
        self.logger = None

    def init(self):
        check_filename_instance(self.filenames)
        check_directory_permissions(self.directory)

        logger, formatter = get_logger_and_formatter(self.appname, self.datefmt, self.showlocation, self.timezone)
        if logger.level != self.level:
            logger.setLevel(self.level)

        for file in self.filenames:
            log_file_path = get_log_path(self.directory, file)

            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file_path,
                mode="a",
                maxBytes=self.maxmbytes * MB_TO_BYTES,
                backupCount=self.daystokeep,
                encoding=self.encoding,
                delay=False,
                errors=None,
            )
            file_handler.rotator = GZipRotatorSize(self.directory, self.daystokeep)
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
            cleanup_logger_handlers(self.logger)

    @staticmethod
    def cleanup_logger(logger: logging.Logger) -> None:
        """Static method for cleaning up logger resources."""
        cleanup_logger_handlers(logger)


class GZipRotatorSize:
    def __init__(self, dir_logs: str, daystokeep: int):
        self.directory = dir_logs
        self.daystokeep = daystokeep

    def __call__(self, source: str, dest: str) -> None:
        remove_old_logs(self.directory, self.daystokeep)
        if os.path.isfile(source) and os.stat(source).st_size > 0:
            source_filename, _ = os.path.basename(source).split(".")
            new_file_number = self._get_new_file_number(self.directory, source_filename)
            if os.path.isfile(source):
                gzip_file_with_sufix(source, str(new_file_number))

    @staticmethod
    def _get_new_file_number(directory: str, source_filename: str) -> int:
        pattern = re.compile(rf"{re.escape(source_filename)}_(\d+)\.log\.gz$")
        max_num = 0
        try:
            # Use pathlib for better performance with large directories
            dir_path = Path(directory)
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    match = pattern.match(file_path.name)
                    if match:
                        max_num = max(max_num, int(match.group(1)))
        except OSError as e:
            write_stderr(f"Unable to get previous gz log file number | {type(e).__name__}: {e}")
        return max_num + 1
