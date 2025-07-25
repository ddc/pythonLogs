import errno
import gzip
import logging.handlers
import os
import shutil
import sys
import threading
import time
from datetime import datetime, timedelta, timezone as dttz
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional, Set
from zoneinfo import ZoneInfo
from pythonLogs.constants import DEFAULT_FILE_MODE, LEVEL_MAP


# Global cache for checked directories with thread safety and size limits
_checked_directories: Set[str] = set()
_directory_lock = threading.Lock()
_max_cached_directories = 500  # Limit cache size to prevent unbounded growth


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
    timezone_: str,
) -> tuple[logging.Logger, logging.Formatter]:
    logger = logging.getLogger(name)

    # More efficient handler cleanup with context manager-like pattern
    handlers_to_remove = list(logger.handlers)
    for handler in handlers_to_remove:
        try:
            handler.close()
        except (OSError, ValueError):
            pass  # Ignore expected errors during cleanup
        finally:
            logger.removeHandler(handler)

    formatt = get_format(show_location, name, timezone_)
    formatter = logging.Formatter(formatt, datefmt=datefmt)
    formatter.converter = get_timezone_function(timezone_)
    return logger, formatter


def check_filename_instance(filenames: list | tuple) -> None:
    if not isinstance(filenames, (list, tuple)):
        err_msg = f"Unable to parse filenames. Filename instance is not list or tuple. | {filenames}"
        write_stderr(err_msg)
        raise TypeError(err_msg)


def check_directory_permissions(directory_path: str) -> None:
    # Thread-safe check with double-checked locking pattern
    if directory_path in _checked_directories:
        return

    with _directory_lock:
        # Check again inside the lock to avoid race conditions
        if directory_path in _checked_directories:
            return

        path_obj = Path(directory_path)

        if path_obj.exists():
            if not os.access(directory_path, os.W_OK | os.X_OK):
                err_msg = f"Unable to access directory | {directory_path}"
                write_stderr(err_msg)
                raise PermissionError(err_msg)
        else:
            try:
                path_obj.mkdir(mode=DEFAULT_FILE_MODE, parents=True, exist_ok=True)
            except PermissionError as e:
                err_msg = f"Unable to create directory | {directory_path}"
                write_stderr(f"{err_msg} | {repr(e)}")
                raise PermissionError(err_msg)

        # Add to cache with size limit enforcement
        if len(_checked_directories) >= _max_cached_directories:
            # Remove a random entry to make space (simple eviction strategy)
            _checked_directories.pop()
        _checked_directories.add(directory_path)


def remove_old_logs(logs_dir: str, days_to_keep: int) -> None:
    if days_to_keep <= 0:
        return

    cutoff_time = datetime.now() - timedelta(days=days_to_keep)

    try:
        for file_path in Path(logs_dir).glob("*.gz"):
            try:
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
            except (OSError, IOError) as e:
                write_stderr(f"Unable to delete old log | {file_path} | {repr(e)}")
    except OSError as e:
        write_stderr(f"Unable to scan directory for old logs | {logs_dir} | {repr(e)}")


def delete_file(path: str) -> bool:
    """Remove the given file and returns True if the file was successfully removed"""
    path_obj = Path(path)

    try:
        if path_obj.is_file():
            path_obj.unlink()
        elif path_obj.is_dir():
            shutil.rmtree(path_obj)
        elif path_obj.exists():
            # Handle special files
            path_obj.unlink()
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    except OSError as e:
        write_stderr(repr(e))
        raise e
    return True


def is_older_than_x_days(path: str, days: int) -> bool:
    """Check if a file or directory is older than the specified number of days"""
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

    try:
        if int(days) == 0:
            cutoff_time = datetime.now()
        else:
            cutoff_time = datetime.now() - timedelta(days=int(days))
    except ValueError as e:
        write_stderr(repr(e))
        raise e

    file_time = datetime.fromtimestamp(path_obj.stat().st_mtime)
    return file_time < cutoff_time


# Cache stderr timezone for better performance
@lru_cache(maxsize=1)
def get_stderr_timezone():
    timezone_name = os.getenv("LOG_TIMEZONE", "UTC")
    if timezone_name.lower() == "localtime":
        return None  # Use system local timezone
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        # Fallback to local timezone if requested timezone is not available
        return None


def write_stderr(msg: str) -> None:
    """Write msg to stderr with optimized timezone handling"""
    try:
        tz = get_stderr_timezone()
        if tz is None:
            # Use local timezone
            dt = datetime.now()
        else:
            dt = datetime.now(dttz.utc).astimezone(tz)
        dt_timezone = dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        sys.stderr.write(f"[{dt_timezone}]:[ERROR]:{msg}\n")
    except (OSError, ValueError, KeyError):
        # Fallback to simple timestamp if timezone fails
        sys.stderr.write(f"[{datetime.now().isoformat()}]:[ERROR]:{msg}\n")


def get_level(level: str) -> int:
    """Get logging level using enum values"""
    if not isinstance(level, str):
        write_stderr(f"Unable to get log level. Setting default level to: 'INFO' ({logging.INFO})")
        return logging.INFO

    return LEVEL_MAP.get(level.lower(), logging.INFO)


def get_log_path(directory: str, filename: str) -> str:
    """Get log file path with optimized validation"""
    log_file_path = str(Path(directory) / filename)

    # Check directory permissions (cached)
    check_directory_permissions(directory)

    # Only validate write access to directory, not create the file
    if not os.access(directory, os.W_OK):
        err_message = f"Unable to write to log directory | {directory}"
        write_stderr(err_message)
        raise PermissionError(err_message)

    return log_file_path


@lru_cache(maxsize=32)
def get_timezone_offset(timezone_: str) -> str:
    """Cache timezone offset calculation with fallback for missing timezone data"""
    if timezone_.lower() == "localtime":
        return time.strftime("%z")
    else:
        try:
            return datetime.now(ZoneInfo(timezone_)).strftime("%z")
        except Exception:
            # Fallback to localtime if the requested timezone is not available,
            # This is common on Windows systems without full timezone data
            return time.strftime("%z")


def get_format(show_location: bool, name: str, timezone_: str) -> str:
    """Get log format string with cached timezone offset"""
    _debug_fmt = ""
    _logger_name = ""

    if name:
        _logger_name = f"[{name}]:"

    if show_location:
        _debug_fmt = "[%(filename)s:%(funcName)s:%(lineno)d]:"

    utc_offset = get_timezone_offset(timezone_)
    return f"[%(asctime)s.%(msecs)03d{utc_offset}]:[%(levelname)s]:{_logger_name}{_debug_fmt}%(message)s"


def gzip_file_with_sufix(file_path: str, sufix: str) -> str | None:
    """gzip file with improved error handling and performance"""
    path_obj = Path(file_path)

    if not path_obj.is_file():
        return None

    # Use pathlib for cleaner path operations
    renamed_dst = path_obj.with_name(f"{path_obj.stem}_{sufix}{path_obj.suffix}.gz")

    # Windows-specific retry mechanism for file locking issues
    max_retries = 3 if sys.platform == "win32" else 1
    retry_delay = 0.1  # 100ms delay between retries

    for attempt in range(max_retries):
        try:
            with open(file_path, "rb") as fin:
                with gzip.open(renamed_dst, "wb", compresslevel=6) as fout:  # Balanced compression
                    shutil.copyfileobj(fin, fout, length=64 * 1024)  # type: ignore # 64KB chunks for better performance
            break  # Success, exit retry loop
        except PermissionError as e:
            # Windows file locking issue - retry with delay
            if attempt < max_retries - 1 and sys.platform == "win32":
                time.sleep(retry_delay)
                continue
            # Final attempt failed or not Windows - treat as regular error
            write_stderr(f"Unable to gzip log file | {file_path} | {repr(e)}")
            raise e
        except (OSError, IOError) as e:
            write_stderr(f"Unable to gzip log file | {file_path} | {repr(e)}")
            raise e

    try:
        path_obj.unlink()  # Use pathlib for deletion
    except OSError as e:
        write_stderr(f"Unable to delete source log file | {file_path} | {repr(e)}")
        raise e

    return str(renamed_dst)


@lru_cache(maxsize=32)
def get_timezone_function(time_zone: str) -> Callable:
    """Get timezone function with caching and fallback for missing timezone data"""
    match time_zone.lower():
        case "utc":
            try:
                # Try to create UTC timezone to verify it's available
                ZoneInfo("UTC")
                return time.gmtime
            except Exception:
                # Fallback to localtime if UTC timezone data is missing
                return time.localtime
        case "localtime":
            return time.localtime
        case _:
            try:
                # Cache the timezone object
                tz = ZoneInfo(time_zone)
                return lambda *args: datetime.now(tz=tz).timetuple()
            except Exception:
                # Fallback to localtime if the requested timezone is not available
                return time.localtime


# Shared handler cleanup utility
def cleanup_logger_handlers(logger: Optional[logging.Logger]) -> None:
    """Clean up logger resources by closing all handlers.

    This is a centralized utility to ensure consistent cleanup behavior
    across all logger types and prevent code duplication.

    Args:
        logger: The logger to clean up (can be None)
    """
    if logger is None:
        return

    # Create a snapshot of handlers to avoid modification during iteration
    handlers_to_remove = list(logger.handlers)
    for handler in handlers_to_remove:
        try:
            handler.close()
        except (OSError, ValueError):
            # Ignore errors during cleanup to prevent cascading failures
            pass
        finally:
            logger.removeHandler(handler)


# Public API for directory cache management
def set_directory_cache_limit(max_directories: int) -> None:
    """Set the maximum number of directories to cache.

    Args:
        max_directories: Maximum number of directories to keep in cache
    """
    global _max_cached_directories
    
    with _directory_lock:
        _max_cached_directories = max_directories
        # Trim cache if it exceeds new limit
        while len(_checked_directories) > max_directories:
            _checked_directories.pop()


def clear_directory_cache() -> None:
    """Clear the directory cache to free memory."""
    with _directory_lock:
        _checked_directories.clear()


def get_directory_cache_stats() -> dict:
    """Get statistics about the directory cache.
    
    Returns:
        Dict with cache statistics including size and limit
    """
    with _directory_lock:
        return {
            "cached_directories": len(_checked_directories),
            "max_directories": _max_cached_directories,
            "directories": list(_checked_directories)
        }
