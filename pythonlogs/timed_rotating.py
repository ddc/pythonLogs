import logging.handlers
import os
from pythonlogs.core.log_utils import (
    RotatingLogMixin,
    check_directory_permissions,
    check_filename_instance,
    get_level,
    get_log_path,
    get_logger_and_formatter,
    get_stream_handler,
    gzip_file_with_sufix,
    remove_old_logs,
)
from pythonlogs.core.memory_utils import register_logger_weakref
from pythonlogs.core.settings import get_log_settings
from pythonlogs.core.thread_safety import auto_thread_safe


@auto_thread_safe(["init"])
class TimedRotatingLog(RotatingLogMixin):
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
        level: str | None = None,
        name: str | None = None,
        directory: str | None = None,
        filenames: list | tuple | None = None,
        when: str | None = None,
        sufix: str | None = None,
        daystokeep: int | None = None,
        encoding: str | None = None,
        datefmt: str | None = None,
        timezone: str | None = None,
        streamhandler: bool | None = None,
        showlocation: bool | None = None,
        rotateatutc: bool | None = None,
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
        if logger.level != self.level:
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


class GZipRotatorTimed:
    def __init__(self, dir_logs: str, days_to_keep: int):
        self.dir = dir_logs
        self.days_to_keep = days_to_keep

    def __call__(self, source: str, dest: str) -> None:
        remove_old_logs(self.dir, self.days_to_keep)
        sufix = os.path.splitext(dest)[1].replace(".", "")
        gzip_file_with_sufix(source, sufix)
