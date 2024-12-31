# -*- encoding: utf-8 -*-
import errno
import gzip
import logging.handlers
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone as dttz
from time import struct_time
from typing import Any, Callable
import pytz


def get_stream_handler(
    level: int,
    formatter: logging.Formatter,
) -> logging.StreamHandler:

    stream_hdlr = logging.StreamHandler()
    stream_hdlr.setFormatter(formatter)
    stream_hdlr.setLevel(level)
    return stream_hdlr


def get_logger_and_formatter(
    name: str,
    datefmt: str,
    show_location: bool,
    timezone: str,
) -> [logging.Logger, logging.Formatter]:

    logger = logging.getLogger(name)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    formatt = get_format(show_location, name, timezone)
    formatter = logging.Formatter(formatt, datefmt=datefmt)
    formatter.converter = get_timezone_function(timezone)
    return logger, formatter


def check_filename_instance(filenames: list | tuple) -> None:
    if not isinstance(filenames, list | tuple):
        err_msg = f"Unable to parse filenames. Filename instance is not list or tuple. | {filenames}"
        write_stderr(err_msg)
        raise TypeError(err_msg)


def check_directory_permissions(directory_path: str) -> None:
    if os.path.isdir(directory_path) and not os.access(directory_path, os.W_OK | os.X_OK):
        err_msg = f"Unable to access directory | {directory_path}"
        write_stderr(err_msg)
        raise PermissionError(err_msg)

    try:
        if not os.path.isdir(directory_path):
            os.makedirs(directory_path, mode=0o755, exist_ok=True)
    except PermissionError as e:
        err_msg = f"Unable to create directory | {directory_path}"
        write_stderr(f"{err_msg} | {repr(e)}")
        raise PermissionError(err_msg)


def remove_old_logs(logs_dir: str, days_to_keep: int) -> None:
    files_list = list_files(logs_dir, ends_with=".gz")
    for file in files_list:
        try:
            if is_older_than_x_days(file, days_to_keep):
                delete_file(file)
        except Exception as e:
            write_stderr(f"Unable to delete {days_to_keep} days old logs | {file} | {repr(e)}")


def list_files(directory: str, ends_with: str) -> tuple:
    """
    List all files in the given directory
        and returns them in a list sorted by creation time in ascending order
    :param directory:
    :param ends_with:
    :return: tuple
    """

    try:
        result: list = []
        if os.path.isdir(directory):
            result: list = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(ends_with)]
            result.sort(key=os.path.getmtime)
        return tuple(result)
    except Exception as e:
        write_stderr(repr(e))
        raise e


def delete_file(path: str) -> bool:
    """
    Remove the given file and returns True if the file was successfully removed
    :param path:
    :return: True
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.exists(path):
            shutil.rmtree(path)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    except OSError as e:
        write_stderr(repr(e))
        raise e
    return True


def is_older_than_x_days(path: str, days: int) -> bool:
    """
    Check if a file or directory is older than the specified number of days
    :param path:
    :param days:
    :return:
    """

    if not os.path.exists(path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

    try:
        if int(days) in (0, 1):
            cutoff_time = datetime.today()
        else:
            cutoff_time = datetime.today() - timedelta(days=int(days))
    except ValueError as e:
        write_stderr(repr(e))
        raise e

    file_timestamp = os.stat(path).st_mtime
    file_time = datetime.fromtimestamp(file_timestamp)

    if file_time < cutoff_time:
        return True
    return False


def write_stderr(msg: str) -> None:
    """
    Write msg to stderr
    :param msg:
    :return: None
    """

    obj = datetime.now(dttz.utc)
    dt = obj.astimezone(pytz.timezone(os.getenv("LOG_TIMEZONE", "UTC")))
    dt_timezone = dt.strftime("%Y-%m-%dT%H:%M:%S.%f:%z")
    sys.stderr.write(f"[{dt_timezone}]:[ERROR]:{msg}\n")


def get_level(level: str) -> logging:
    """
    Get logging level
    :param level:
    :return: level
    """

    if not isinstance(level, str):
        write_stderr(f"Unable to get log level. Setting default level to: 'INFO' ({logging.INFO})")
        return logging.INFO

    match level.lower():
        case "debug":
            return logging.DEBUG
        case "warning" | "warn":
            return logging.WARNING
        case "error":
            return logging.ERROR
        case "critical" | "crit":
            return logging.CRITICAL
        case _:
            return logging.INFO


def get_log_path(directory: str, filename: str) -> str:
    """
    Get log file path
    :param directory:
    :param filename:
    :return: path as str
    """

    log_file_path = str(os.path.join(directory, filename))
    err_message = f"Unable to open log file for writing | {log_file_path}"

    try:
        open(log_file_path, "a+").close()
    except PermissionError as e:
        write_stderr(f"{err_message} | {repr(e)}")
        raise PermissionError(err_message)
    except FileNotFoundError as e:
        write_stderr(f"{err_message} | {repr(e)}")
        raise FileNotFoundError(err_message)
    except OSError as e:
        write_stderr(f"{err_message} | {repr(e)}")
        raise e

    return log_file_path


def get_format(show_location: bool, name: str, timezone: str) -> str:
    _debug_fmt = ""
    _logger_name = ""

    if name:
        _logger_name = f"[{name}]:"

    if show_location:
        _debug_fmt = "[%(filename)s:%(funcName)s:%(lineno)d]:"

    if timezone == "localtime":
        utc_offset = time.strftime("%z")
    else:
        utc_offset = datetime.now(pytz.timezone(timezone)).strftime("%z")

    fmt = f"[%(asctime)s.%(msecs)03d{utc_offset}]:[%(levelname)s]:{_logger_name}{_debug_fmt}%(message)s"
    return fmt


def gzip_file_with_sufix(file_path, sufix) -> str | None:
    """
    gzip file
    :param file_path:
    :param sufix:
    :return: bool
    """

    if os.path.isfile(file_path):
        sfname, sext = os.path.splitext(file_path)
        renamed_dst = f"{sfname}_{sufix}{sext}.gz"

        try:
            with open(file_path, "rb") as fin:
                with gzip.open(renamed_dst, "wb") as fout:
                    fout.writelines(fin)
        except Exception as e:
            write_stderr(f"Unable to gzip log file | {file_path} | {repr(e)}")
            raise e

        try:
            delete_file(file_path)
        except OSError as e:
            write_stderr(f"Unable to delete source log file | {file_path} | {repr(e)}")
            raise e

        return renamed_dst


def get_timezone_function(
    time_zone: str,
) -> Callable[[float | None, Any], struct_time] | Callable[[Any], struct_time]:

    match time_zone.lower():
        case "utc":
            return time.gmtime
        case "localtime":
            return time.localtime
        case _:
            return lambda *args: datetime.now(tz=pytz.timezone(time_zone)).timetuple()
