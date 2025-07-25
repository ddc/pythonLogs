#!/usr/bin/env python3
"""Utility functions for tests across different platforms."""
import os
import time
import sys
import pytest
import functools
import tempfile
from contextlib import contextmanager


def skip_if_no_zoneinfo_utc():
    """Skip test if zoneinfo or UTC timezone data is not available (common on Windows)."""
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("UTC")  # Test if UTC is available
    except Exception:
        pytest.skip("zoneinfo not available or UTC timezone data missing on this system")


def get_safe_timezone():
    """Get a timezone that works on all platforms."""
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("UTC")  # Test if UTC is available
        return "UTC"
    except Exception:
        return "localtime"  # Fallback to localtime which should always work


def requires_zoneinfo_utc(func):
    """Decorator to skip tests that require zoneinfo UTC support."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        skip_if_no_zoneinfo_utc()
        return func(*args, **kwargs)
    return wrapper


def requires_zoneinfo(timezone):
    """Decorator to skip tests that require a specific timezone."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(timezone)  # Test if timezone is available
            except Exception:
                pytest.skip(f"Timezone '{timezone}' not available on this system")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def patch_logger_kwargs_with_safe_timezone(kwargs):
    """Patch logger kwargs to use safe timezone if UTC is specified but not available."""
    if kwargs.get('timezone') == 'UTC':
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo("UTC")  # Test if UTC is available
        except Exception:
            kwargs['timezone'] = 'localtime'  # Fall back to localtime
    return kwargs


def safe_delete_file(filepath, max_attempts=3, delay=0.1):
    """
    Safely delete a file with Windows compatibility.
    
    On Windows, files can remain locked by processes even after being closed,
    leading to PermissionError. This function tries multiple times with delays.
    
    Args:
        filepath: Path to the file to delete
        max_attempts: Maximum number of deletion attempts (default: 3)
        delay: Delay between attempts in seconds (default: 0.1)
    
    Returns:
        bool: True if file was deleted successfully, False otherwise
    """
    if not os.path.exists(filepath):
        return True  # Already deleted
    
    for attempt in range(max_attempts):
        try:
            os.unlink(filepath)
            return True
        except PermissionError:
            if sys.platform == "win32":
                # On Windows, file might be locked - wait and retry
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt failed - log and return False
                    print(f"Warning: Could not delete {filepath} after {max_attempts} attempts")
                    return False
            else:
                # On non-Windows systems, permission error is probably real
                raise
        except (OSError, IOError) as e:
            # Other OS errors should be raised
            raise e
    
    return False


def safe_close_and_delete_file(file_handler, filepath, max_attempts=3, delay=0.1):
    """
    Safely close a file handler and delete the associated file.
    
    This function ensures proper closure of file handlers before attempting
    deletion, which is crucial on Windows systems.
    
    Args:
        file_handler: The file handler to close (can be None)
        filepath: Path to the file to delete
        max_attempts: Maximum number of deletion attempts (default: 3)
        delay: Delay between attempts in seconds (default: 0.1)
    
    Returns:
        bool: True if file was deleted successfully, False otherwise
    """
    # Close the handler first if it exists
    if file_handler is not None:
        try:
            file_handler.close()
        except (OSError, AttributeError):
            # Handler might already be closed or not have a close method
            pass
    
    # Small delay to ensure file handle is fully released
    if sys.platform == "win32":
        time.sleep(0.05)
    
    return safe_delete_file(filepath, max_attempts, delay)


def cleanup_logger_handlers(logger):
    """
    Safely close and remove all handlers from a logger.
    
    This is crucial on Windows to ensure file handles are released
    before attempting to delete temporary directories.
    
    Args:
        logger: The logger whose handlers should be cleaned up
    """
    if logger is None:
        return
    
    # Get a copy of handlers to avoid modifying list while iterating
    handlers = logger.handlers.copy()
    
    for handler in handlers:
        try:
            # Close the handler first
            handler.close()
        except (OSError, AttributeError):
            # Handler might already be closed or not have a close method
            pass
        finally:
            # Remove the handler from the logger
            try:
                logger.removeHandler(handler)
            except (ValueError, AttributeError):
                # Handler might already be removed
                pass
    
    # Small delay on Windows to ensure handles are fully released
    if sys.platform == "win32":
        time.sleep(0.05)


def cleanup_all_loggers():
    """
    Clean up all loggers by closing their handlers.
    
    This function iterates through all existing loggers and closes
    their handlers to prevent file locking issues on Windows.
    """
    import logging
    
    # Get all existing loggers
    loggers_to_cleanup = []
    
    # Get the root logger
    root_logger = logging.getLogger()
    if root_logger.handlers:
        loggers_to_cleanup.append(root_logger)
    
    # Get all named loggers from the logger manager
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        if logger.handlers:
            loggers_to_cleanup.append(logger)
    
    # Clean up all loggers
    for logger in loggers_to_cleanup:
        cleanup_logger_handlers(logger)
    
    # Additional delay on Windows
    if sys.platform == "win32":
        time.sleep(0.1)


def safe_delete_directory(directory_path, max_attempts=5, delay=0.2):
    """
    Safely delete a directory with Windows compatibility.
    
    On Windows, directories can remain locked by processes even after
    file handles are closed, leading to PermissionError.
    
    Args:
        directory_path: Path to the directory to delete  
        max_attempts: Maximum number of deletion attempts (default: 5)
        delay: Delay between attempts in seconds (default: 0.2)
    
    Returns:
        bool: True if directory was deleted successfully, False otherwise
    """
    import shutil
    
    if not os.path.exists(directory_path):
        return True  # Already deleted
    
    for attempt in range(max_attempts):
        try:
            shutil.rmtree(directory_path)
            return True
        except PermissionError:
            if sys.platform == "win32":
                # On Windows, directory might be locked - wait and retry
                if attempt < max_attempts - 1:
                    # Clean up any remaining logger handlers
                    cleanup_all_loggers()
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt failed - log and return False
                    print(f"Warning: Could not delete directory {directory_path} after {max_attempts} attempts")
                    return False
            else:
                # On non-Windows systems, permission error is probably real
                raise
        except (OSError, IOError) as e:
            # Other OS errors should be raised
            raise e
    
    return False


@contextmanager
def windows_safe_temp_directory(**kwargs):
    """
    Context manager for creating temporary directories that are safely cleaned up on Windows.
    
    This context manager handles Windows-specific file locking issues by ensuring
    all logger handlers are cleaned up before attempting directory deletion.
    
    Args:
        **kwargs: Arguments passed to tempfile.TemporaryDirectory
        
    Yields:
        str: Path to the temporary directory
    """
    # Clean up any existing loggers before creating temp directory
    cleanup_all_loggers()
    
    temp_dir_obj = tempfile.TemporaryDirectory(**kwargs)
    temp_dir = temp_dir_obj.__enter__()
    
    try:
        yield temp_dir
    finally:
        try:
            # Clean up all loggers and their handlers before directory deletion
            cleanup_all_loggers()
            
            # Attempt normal cleanup first
            temp_dir_obj.__exit__(None, None, None)
        except (OSError, PermissionError):
            # On Windows, if normal cleanup fails, use safe deletion
            try:
                safe_delete_directory(temp_dir)
            except Exception:
                # If all else fails, just log the issue
                print(f"Warning: Could not clean up temporary directory {temp_dir}")


def create_windows_safe_temp_file(suffix="", prefix="tmp", dir=None, text=False):
    """
    Create a temporary file with Windows-safe cleanup.
    
    Args:
        suffix: File suffix (default: "")
        prefix: File prefix (default: "tmp")
        dir: Directory to create file in (default: None)
        text: Whether to open in text mode (default: False)
        
    Returns:
        tuple: (file_handle, file_path)
    """
    import tempfile
    
    # Create temporary file
    fd, filepath = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
    
    # Convert file descriptor to file handle
    mode = 'w' if text else 'wb'
    file_handle = os.fdopen(fd, mode)
    
    return file_handle, filepath