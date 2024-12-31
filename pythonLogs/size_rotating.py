# -*- encoding: utf-8 -*-
import logging.handlers
import os
from typing import Optional
from pythonLogs.log_utils import (
    check_directory_permissions,
    check_filename_instance,
    get_level,
    get_log_path,
    get_logger_and_formatter,
    get_stream_handler,
    gzip_file_with_sufix,
    list_files,
    remove_old_logs,
    write_stderr,
)
from pythonLogs.settings import LogSettings


class SizeRotatingLog:
    def __init__(
        self,
        level: Optional[str] = None,
        name: Optional[str] = None,
        directory: Optional[str] = None,
        filenames: Optional[list | tuple] = None,
        maxmbytes: Optional[int] = None,
        daystokeep: Optional[int] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        streamhandler: Optional[bool] = None,
        showlocation: Optional[bool] = None,
    ):
        _settings = LogSettings()
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

    def init(self):
        check_filename_instance(self.filenames)
        check_directory_permissions(self.directory)

        logger, formatter = get_logger_and_formatter(self.appname, self.datefmt, self.showlocation, self.timezone)
        logger.setLevel(self.level)

        for file in self.filenames:
            log_file_path = get_log_path(self.directory, file)

            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file_path,
                mode="a",
                maxBytes=self.maxmbytes * 1024 * 1024,
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

        return logger


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
                gzip_file_with_sufix(source, new_file_number)

    @staticmethod
    def _get_new_file_number(directory, source_filename):
        new_file_number = 1
        previous_gz_files = list_files(directory, ends_with=".gz")
        for gz_file in previous_gz_files:
            if source_filename in gz_file:
                try:
                    oldest_file_name = gz_file.split(".")[0].split("_")
                    if len(oldest_file_name) > 1:
                        new_file_number = int(oldest_file_name[1]) + 1
                except ValueError as e:
                    write_stderr(f"Unable to get previous gz log file number | {gz_file} | {repr(e)}")
                    raise
        return new_file_number
