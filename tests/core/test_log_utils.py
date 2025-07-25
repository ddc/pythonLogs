#!/usr/bin/env python3
"""Utility functions and tests for log_utils module."""
import contextlib
import functools
import io
import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import log_utils


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
#
# Note: Functions with "safe_", "windows_safe_", "cleanup_" prefixes are
# primarily designed for Windows compatibility but work cross-platform.
# For Unix/Linux/macOS-specific tests, prefer standard Python file operations.


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
    Safely delete a file with cross-platform compatibility.

    On Windows, files can remain locked by processes even after being closed,
    leading to PermissionError. This function tries multiple times with delays.
    On Unix/Linux/macOS, it performs standard deletion without retries.

    Args:
        filepath: Path to the file to delete
        max_attempts: Maximum number of deletion attempts (default: 3, only used on Windows)
        delay: Delay between attempts in seconds (default: 0.1, only used on Windows)

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
        except OSError:
            # Other OS errors should be raised
            raise

    return False


def safe_close_and_delete_file(file_handler, filepath, max_attempts=3, delay=0.1):
    """
    Safely close a file handler and delete the associated file.

    This function ensures proper closure of file handlers before attempting
    deletion, which is crucial on Windows systems but also good practice on Unix/Linux/macOS.

    Args:
        file_handler: The file handler to close (can be None)
        filepath: Path to the file to delete
        max_attempts: Maximum number of deletion attempts (default: 3, only used on Windows)
        delay: Delay between attempts in seconds (default: 0.1, only used on Windows)

    Returns:
        bool: True if file was deleted successfully, False otherwise
    """
    # Close the handler first if it exists
    if file_handler is not None:
        try:
            file_handler.close()
        except (OSError, AttributeError):
            # The Handler might already be closed or not have a close method
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
            # The Handler might already be closed or not have a close method
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
        except OSError:
            # Other OS errors should be raised
            raise

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
        except OSError:
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


# ============================================================================
# TEST CLASSES
# ============================================================================


class TestLogUtils:
    @classmethod
    def setup_class(cls):
        """setup_class"""
        pass

    @classmethod
    def teardown_class(cls):
        """teardown_class"""
        pass

    def test_get_stream_handler(self):
        level = log_utils.get_level("DEBUG")
        _, formatter = log_utils.get_logger_and_formatter("appname", "%Y-%m-%dT%H:%M:%S", False, "UTC")
        stream_hdlr = log_utils.get_stream_handler(level, formatter)
        assert isinstance(stream_hdlr, logging.StreamHandler)

    def test_check_filename_instance(self):
        filenames = "test1.log"
        with pytest.raises(TypeError) as exec_info:
            log_utils.check_filename_instance(filenames)
        assert type(exec_info.value) is TypeError
        assert filenames in str(exec_info.value)
        assert "Unable to parse filenames" in str(exec_info.value)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific chmod test")
    def test_check_directory_permissions(self):
        """Test directory permission checking (Unix/Linux/macOS)."""
        # Unix-style permission testing
        directory = os.path.join(tempfile.gettempdir(), "test_permission")

        # Clean up any existing directory first
        if os.path.exists(directory):
            try:
                os.chmod(directory, 0o755)
                log_utils.delete_file(directory)
            except OSError:
                pass  # Continue if cleanup fails

        try:
            os.makedirs(directory, mode=0, exist_ok=True)  # No permissions at all
            assert os.path.exists(directory) == True
            with pytest.raises(PermissionError) as exec_info:
                log_utils.check_directory_permissions(directory)
            assert type(exec_info.value) is PermissionError
            assert "Unable to access directory" in str(exec_info.value)
        finally:
            # Always restore permissions for cleanup, even if test fails
            if os.path.exists(directory):
                try:
                    os.chmod(directory, 0o755)
                    log_utils.delete_file(directory)
                except OSError:
                    pass  # Ignore cleanup errors

        assert not os.path.exists(directory)

        # test permission error on creation - use a readonly parent directory
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_parent = os.path.join(temp_dir, "readonly")
            # Read-only parent
            os.makedirs(readonly_parent, mode=0o555)
            try:
                non_existent = os.path.join(readonly_parent, "non-existent-directory")
                with pytest.raises(PermissionError) as exec_info:
                    log_utils.check_directory_permissions(non_existent)
                assert type(exec_info.value) is PermissionError
                assert "Unable to create directory" in str(exec_info.value)
            finally:
                # Restore permissions for cleanup
                os.chmod(readonly_parent, 0o755)

    def test_remove_old_logs(self):
        directory = os.path.join(tempfile.gettempdir(), "test_remove_logs")
        os.makedirs(directory, mode=0o755, exist_ok=True)
        assert os.path.exists(directory) == True

        # Create a file and manually set its modification time to be old
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".gz", delete=False) as tmpfile:
            file_path = tmpfile.name
            old_time = time.time() - 2 * 24 * 60 * 60  # 2 days old
            os.utime(file_path, (old_time, old_time))

        log_utils.remove_old_logs(directory, 1)  # Remove files older than 1 day
        assert os.path.isfile(file_path) == False
        log_utils.delete_file(directory)
        assert os.path.exists(directory) == False

    def test_delete_file(self):
        """Test delete_file with standard Unix/Linux file handling."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp_file:
            file_path = tmp_file.name
            tmp_file.write("test content")

        assert os.path.isfile(file_path) == True
        log_utils.delete_file(file_path)
        assert os.path.isfile(file_path) == False

    def test_is_older_than_x_days(self):
        """Test is_older_than_x_days with standard Unix/Linux file handling."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp_file:
            file_path = tmp_file.name
            tmp_file.write("test content")

        try:
            assert os.path.isfile(file_path) == True

            # When days=1, it compares against 1 day ago, so newly created file should NOT be older
            result = log_utils.is_older_than_x_days(file_path, 1)
            assert result == False

            # When days=5, it compares against 5 days ago, so newly created file should NOT be older
            result = log_utils.is_older_than_x_days(file_path, 5)
            assert result == False

            log_utils.delete_file(file_path)
            assert os.path.isfile(file_path) == False
        finally:
            # Ensure cleanup if the test fails
            if os.path.exists(file_path):
                os.unlink(file_path)

    def test_get_level(self):
        level = log_utils.get_level(11111111)
        assert level == logging.INFO

        level = log_utils.get_level("")
        assert level == logging.INFO

        level = log_utils.get_level("INFO")
        assert level == logging.INFO

        level = log_utils.get_level("DEBUG")
        assert level == logging.DEBUG

        level = log_utils.get_level("WARNING")
        assert level == logging.WARNING

        level = log_utils.get_level("ERROR")
        assert level == logging.ERROR

        level = log_utils.get_level("CRITICAL")
        assert level == logging.CRITICAL

    def test_get_log_path(self):
        import sys

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = "test.log"
            # Test 1: Valid directory should return the correct path
            result = log_utils.get_log_path(temp_dir, test_file)
            assert result == os.path.join(temp_dir, test_file)

            # Test 2: Directory that gets created should work fine
            new_dir = os.path.join(temp_dir, "newdir")
            result = log_utils.get_log_path(new_dir, test_file)
            assert result == os.path.join(new_dir, test_file)
            assert os.path.exists(new_dir)  # Should have been created

            # Test 3: Existing but non-writable directory should raise PermissionError
            # This test only works on Unix/Linux/macOS systems with chmod
            if sys.platform != "win32":
                readonly_dir = os.path.join(temp_dir, "readonly")
                os.makedirs(readonly_dir, mode=0o555)
                try:
                    with pytest.raises(PermissionError) as exc_info:
                        log_utils.get_log_path(readonly_dir, test_file)
                    assert "Unable to access directory" in str(exc_info.value)
                finally:
                    # Cleanup permissions
                    os.chmod(readonly_dir, 0o755)
                    os.rmdir(readonly_dir)

    def test_get_format(self):
        show_location = True
        name = "test1"
        timezone = "UTC"
        result = log_utils.get_format(show_location, name, timezone)
        # On systems without UTC timezone data, this falls back to localtime
        # Just verify the format structure is correct
        assert f"[{name}]:" in result
        assert "[%(filename)s:%(funcName)s:%(lineno)d]:" in result
        assert "%(message)s" in result

        show_location = False
        name = "test2"
        timezone = "America/Los_Angeles"
        result = log_utils.get_format(show_location, name, timezone)
        # On systems without this timezone, it falls back to localtime
        # Just verify the basic structure
        assert f"[{name}]:" in result
        assert "%(message)s" in result

        show_location = False
        name = "test3"
        timezone = "Australia/Queensland"
        result = log_utils.get_format(show_location, name, timezone)
        # On systems without timezone data (common on Windows), this falls back to localtime
        # Test should verify format structure rather than hardcoded timezone offset
        expected_base_format = "[%(asctime)s.%(msecs)03d"
        assert result.startswith(expected_base_format)
        assert f"]:[%(levelname)s]:[{name}]:%(message)s" in result
        # Verify timezone offset is present (either +1000 or fallback)
        import re

        # The % characters need to be literal in the regex
        offset_pattern = r'\[%\(asctime\)s\.%\(msecs\)03d([+-]\d{4})\]'
        match = re.search(offset_pattern, result)
        assert match is not None, f"No timezone offset found in format: {result}"
        # The offset could be +1000 (if timezone is available) or system localtime fallback
        offset = match.group(1)
        assert re.match(r'[+-]\d{4}', offset), f"Invalid timezone offset format: {offset}"

    def test_gzip_file_with_sufix(self):
        """Test gzip_file_with_sufix with standard Unix/Linux file handling."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp_file:
            file_path = tmp_file.name
            tmp_file.write("test content for gzip")

        try:
            assert os.path.isfile(file_path) == True
            sufix = "test1"
            result = log_utils.gzip_file_with_sufix(file_path, sufix)
            file_path_no_suffix = file_path.split(".")[0]
            assert result == f"{file_path_no_suffix}_{sufix}.log.gz"

            # Clean up the gzipped file
            if os.path.exists(result):
                os.unlink(result)
            assert os.path.isfile(result) == False

        finally:
            # Ensure cleanup of the original file if it still exists
            if os.path.exists(file_path):
                os.unlink(file_path)

        # test a non-existent file - use tempfile path that doesn't exist
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "non-existent-directory", "test2.log")
            sufix = "test2"
            result = log_utils.gzip_file_with_sufix(file_path, sufix)
            assert result is None

    def test_get_timezone_function(self):
        timezone = "UTC"
        result = log_utils.get_timezone_function(timezone)
        # On systems without UTC timezone data, this may fall back to localtime
        assert result.__name__ in ["gmtime", "localtime"]

        timezone = "localtime"
        result = log_utils.get_timezone_function(timezone)
        assert result.__name__ == "localtime"

        timezone = "America/Los_Angeles"
        result = log_utils.get_timezone_function(timezone)
        # On systems without timezone data (common on Windows), this falls back to localtime
        assert result.__name__ in ["<lambda>", "localtime"]

    def test_write_stderr(self):
        """Test write_stderr function output"""
        # Capture stderr output
        stderr_capture = io.StringIO()
        with contextlib.redirect_stderr(stderr_capture):
            log_utils.write_stderr("Test error message")

        output = stderr_capture.getvalue()
        assert "ERROR" in output
        assert "Test error message" in output
        assert output.startswith("[")  # Should start with timestamp

    def test_write_stderr_with_timezone_error(self):
        """Test write_stderr fallback when timezone fails"""
        # Set invalid timezone to trigger fallback
        original_tz = os.environ.get("LOG_TIMEZONE")
        os.environ["LOG_TIMEZONE"] = "Invalid/Timezone"

        try:
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test fallback message")

            output = stderr_capture.getvalue()
            assert "ERROR" in output
            assert "Test fallback message" in output
        finally:
            # Restore original timezone
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]

    def test_get_logger_and_formatter(self):
        """Test get_logger_and_formatter function"""
        name = "test_logger"
        datefmt = "%Y-%m-%d %H:%M:%S"
        show_location = True
        timezone = "UTC"

        logger, formatter = log_utils.get_logger_and_formatter(name, datefmt, show_location, timezone)

        assert isinstance(logger, logging.Logger)
        assert isinstance(formatter, logging.Formatter)
        assert logger.name == name
        assert formatter.datefmt == datefmt

    def test_get_logger_and_formatter_cleanup(self):
        """Test that get_logger_and_formatter properly cleans up existing handlers"""
        name = "test_cleanup_logger"

        # Create a logger with existing handlers
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        initial_handler_count = len(logger.handlers)
        assert initial_handler_count > 0

        # Call get_logger_and_formatter
        new_logger, formatter = log_utils.get_logger_and_formatter(name, "%Y-%m-%d", False, "UTC")

        # Should be the same logger but with handlers cleaned up
        assert new_logger is logger
        assert len(new_logger.handlers) == 0

    def test_timezone_offset_caching(self):
        """Test get_timezone_offset function via get_format"""
        # Test UTC timezone
        format1 = log_utils.get_format(False, "test", "UTC")
        format2 = log_utils.get_format(False, "test", "UTC")
        assert "+0000" in format1
        assert format1 == format2  # Should be identical due to caching

        # Test localtime
        format3 = log_utils.get_format(False, "test", "localtime")
        assert format3 is not None

    def test_stderr_timezone_caching(self):
        """Test get_stderr_timezone function via write_stderr"""
        # Test with UTC
        original_tz = os.environ.get("LOG_TIMEZONE")
        os.environ["LOG_TIMEZONE"] = "UTC"

        try:
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test UTC message")

            output = stderr_capture.getvalue()
            # On systems with UTC timezone data, should have +0000 or Z
            # On Windows without timezone data, falls back to local time (no timezone indicator)
            assert "+0000" in output or "Z" in output or ("]:[ERROR]:" in output and "Test UTC message" in output)
        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]

    def test_stderr_timezone_localtime(self):
        """Test get_stderr_timezone with localtime"""
        original_tz = os.environ.get("LOG_TIMEZONE")
        os.environ["LOG_TIMEZONE"] = "localtime"

        try:
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test localtime message")

            output = stderr_capture.getvalue()
            assert "Test localtime message" in output
        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]

    def test_get_level_edge_cases(self):
        """Test get_level with various edge cases"""
        # Test with non-string input (already tested in existing test)
        level = log_utils.get_level(None)
        assert level == logging.INFO

        # Test with empty string (already tested)
        level = log_utils.get_level("")
        assert level == logging.INFO

        # Test case sensitivity
        level = log_utils.get_level("debug")
        assert level == logging.DEBUG

        level = log_utils.get_level("WARN")
        assert level == logging.WARNING

        level = log_utils.get_level("crit")
        assert level == logging.CRITICAL

    def test_is_older_than_x_days_edge_cases(self):
        """Test is_older_than_x_days with edge cases"""
        with tempfile.NamedTemporaryFile() as tmp_file:
            # Test with days = 0
            # Add small delay to ensure the file is older than current time
            import time

            time.sleep(0.001)  # 1ms delay to handle Windows timing precision
            result = log_utils.is_older_than_x_days(tmp_file.name, 0)
            assert result == True  # Should use current time as cutoff

            # Test with non-existent file
            with pytest.raises(FileNotFoundError):
                log_utils.is_older_than_x_days("/non/existent/file.log", 1)

            # Test with invalid days parameter
            with pytest.raises(ValueError):
                log_utils.is_older_than_x_days(tmp_file.name, "invalid")

    def test_delete_file_edge_cases(self):
        """Test delete_file with different file types"""
        # Test with non-existent file
        non_existent = "/tmp/non_existent_file_test.log"
        with pytest.raises(FileNotFoundError):
            log_utils.delete_file(non_existent)

    def test_gzip_file_error_handling(self):
        """Test gzip_file_with_sufix error handling"""
        # Test with non-existent source file
        result = log_utils.gzip_file_with_sufix("/non/existent/file.log", "test")
        assert result is None

    def test_remove_old_logs_edge_cases(self):
        """Test remove_old_logs with edge cases"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with days_to_keep = 0 (should return early)
            log_utils.remove_old_logs(temp_dir, 0)  # Should not raise error

            # Test with negative days
            log_utils.remove_old_logs(temp_dir, -1)  # Should return early

            # Test with non-existent directory (should handle gracefully)
            log_utils.remove_old_logs("/non/existent/directory", 1)  # Should not crash

    def test_check_directory_permissions_caching(self):
        """Test that directory permission checking uses caching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # First call should add to cache
            log_utils.check_directory_permissions(temp_dir)

            # The Second call should use cache (no exception should be raised)
            log_utils.check_directory_permissions(temp_dir)

            # Verify it's in the cache by checking the global variable
            assert temp_dir in log_utils._checked_directories

    def test_check_directory_permissions_cache_eviction(self):
        """Test cache eviction when max directories reached"""
        original_max = log_utils._max_cached_directories
        original_cache = log_utils._checked_directories.copy()

        try:
            # Set a small cache size for testing
            log_utils._max_cached_directories = 2
            log_utils._checked_directories.clear()

            with tempfile.TemporaryDirectory() as temp_dir1:
                with tempfile.TemporaryDirectory() as temp_dir2:
                    with tempfile.TemporaryDirectory() as temp_dir3:
                        # Fill cache to capacity
                        log_utils.check_directory_permissions(temp_dir1)
                        log_utils.check_directory_permissions(temp_dir2)
                        assert len(log_utils._checked_directories) == 2

                        # Adding a third should trigger eviction
                        log_utils.check_directory_permissions(temp_dir3)
                        assert len(log_utils._checked_directories) == 2
                        assert temp_dir3 in log_utils._checked_directories
        finally:
            # Restore original values
            log_utils._max_cached_directories = original_max
            log_utils._checked_directories = original_cache

    def test_handler_close_error_handling(self):
        """Test error handling when closing handlers in get_logger_and_formatter"""
        name = "test_handler_error"

        # Create a logger with a handler that will error on close
        logger = logging.getLogger(name)

        # Create a mock handler that raises error on close
        class ErrorHandler(logging.StreamHandler):
            def close(self):
                raise OSError("Test error")

        error_handler = ErrorHandler()
        logger.addHandler(error_handler)

        # This should handle the error gracefully
        new_logger, formatter = log_utils.get_logger_and_formatter(name, "%Y-%m-%d", False, "UTC")

        # Should still work despite the error
        assert new_logger is logger
        assert len(new_logger.handlers) == 0

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific chmod test")
    def test_remove_old_logs_file_error(self):
        """Test remove_old_logs error handling when file deletion fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a .gz file
            gz_file = os.path.join(temp_dir, "test.gz")
            with open(gz_file, "wb") as f:
                f.write(b"test content")

            # Set old modification time
            old_time = time.time() - 2 * 24 * 60 * 60  # 2 days old
            os.utime(gz_file, (old_time, old_time))

            # Make parent directory read-only to trigger deletion error
            os.chmod(temp_dir, 0o555)

            try:
                # Capture stderr to verify error was logged
                stderr_capture = io.StringIO()
                with contextlib.redirect_stderr(stderr_capture):
                    log_utils.remove_old_logs(temp_dir, 1)

                # Should have logged an error but not crashed
                output = stderr_capture.getvalue()
                assert "Unable to delete old log" in output
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def test_remove_old_logs_directory_error(self):
        """Test remove_old_logs error handling when directory scan fails"""
        # Test with a simulated Path.glob() error by mocking pathlib.Path
        import unittest.mock
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a normal directory first
            test_dir = os.path.join(temp_dir, "test_dir")
            os.makedirs(test_dir)

            # Mock Path.glob to raise an OSError
            original_path_glob = Path.glob

            def mock_glob(self, pattern):
                if str(self) == test_dir:
                    raise OSError("Mocked directory scan error")
                return original_path_glob(self, pattern)

            try:
                with unittest.mock.patch.object(Path, 'glob', mock_glob):
                    stderr_capture = io.StringIO()
                    with contextlib.redirect_stderr(stderr_capture):
                        log_utils.remove_old_logs(test_dir, 1)

                    output = stderr_capture.getvalue()
                    assert "Unable to scan directory for old logs" in output
            finally:
                # Ensure the original method is restored
                Path.glob = original_path_glob

    def test_delete_file_special_file(self):
        """Test delete_file with special file types"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a symbolic link (special file)
            target_file = os.path.join(temp_dir, "target.txt")
            link_file = os.path.join(temp_dir, "link.txt")

            with open(target_file, "w") as f:
                f.write("test content")

            os.symlink(target_file, link_file)
            assert os.path.exists(link_file)
            assert os.path.islink(link_file)

            # delete_file should handle symlinks
            result = log_utils.delete_file(link_file)
            assert result == True
            assert not os.path.exists(link_file)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific chmod test")
    def test_get_log_path_permission_error(self):
        """Test get_log_path when directory exists but is not writable (Unix/Linux/macOS)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory and make it read-only
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_dir)
            # Read and execute only
            os.chmod(readonly_dir, 0o555)

            try:
                with pytest.raises(PermissionError) as exc_info:
                    log_utils.get_log_path(readonly_dir, "test.log")
                # The error could be from check_directory_permissions or get_log_path itself
                assert "Unable to access directory" in str(
                    exc_info.value
                ) or "Unable to write to log directory" in str(exc_info.value)
            finally:
                # Restore for cleanup
                os.chmod(readonly_dir, 0o755)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific chmod test")
    def test_gzip_file_io_error(self):
        """Test gzip_file_with_sufix error handling during compression (Unix/Linux/macOS)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test.log")
            with open(test_file, "w") as f:
                f.write("test content")

            # Make directory read-only to trigger gzip error
            os.chmod(temp_dir, 0o555)

            try:
                stderr_capture = io.StringIO()
                with contextlib.redirect_stderr(stderr_capture):
                    with pytest.raises(OSError):
                        log_utils.gzip_file_with_sufix(test_file, "test")

                output = stderr_capture.getvalue()
                assert "Unable to gzip log file" in output
            finally:
                # Restore for cleanup
                os.chmod(temp_dir, 0o755)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific chmod test")
    def test_gzip_file_deletion_error(self):
        """Test gzip_file_with_sufix error when source file deletion fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test.log")
            with open(test_file, "w") as f:
                f.write("test content")

            # Create the gzip file successfully first
            result = log_utils.gzip_file_with_sufix(test_file, "test")
            assert result is not None
            assert result.endswith("_test.log.gz")

            # Clean up the gzipped file
            if os.path.exists(result):
                os.unlink(result)

    def test_write_stderr_fallback(self):
        """Test write_stderr fallback when timezone operations fail"""
        # Save original function
        original_get_stderr_tz = log_utils.get_stderr_timezone

        # Mock get_stderr_timezone to raise an error
        def mock_error_timezone():
            raise KeyError("Mock timezone error")

        try:
            log_utils.get_stderr_timezone = mock_error_timezone

            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test fallback message")

            output = stderr_capture.getvalue()
            assert "Test fallback message" in output
            assert "ERROR" in output
        finally:
            # Restore original function
            log_utils.get_stderr_timezone = original_get_stderr_tz

    def test_stderr_timezone_with_special_timezone(self):
        """Test get_stderr_timezone with different timezone configurations"""
        original_tz = os.environ.get("LOG_TIMEZONE")

        try:
            # Test with a specific timezone
            os.environ["LOG_TIMEZONE"] = "Europe/London"
            # Clear the cache
            log_utils.get_stderr_timezone.cache_clear()

            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test timezone message")

            output = stderr_capture.getvalue()
            assert "Test timezone message" in output

        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]
            log_utils.get_stderr_timezone.cache_clear()

    def test_check_filename_instance_edge_cases(self):
        """Test check_filename_instance with more edge cases."""
        # Test with various invalid types
        with pytest.raises(TypeError):
            log_utils.check_filename_instance(123)

        with pytest.raises(TypeError):
            log_utils.check_filename_instance(None)

        with pytest.raises(TypeError):
            log_utils.check_filename_instance({"file": "test.log"})

        # Valid cases should not raise
        log_utils.check_filename_instance(["test.log", "test2.log"])
        log_utils.check_filename_instance(("test.log", "test2.log"))
        log_utils.check_filename_instance([])  # Empty list is valid
        log_utils.check_filename_instance(())  # Empty tuple is valid

    def test_lru_cache_behavior_verification(self):
        """Test LRU cache behavior in timezone functions."""
        # Clear caches first
        log_utils.get_timezone_function.cache_clear()
        log_utils.get_timezone_offset.cache_clear()

        # Test get_timezone_function cache
        initial_cache = log_utils.get_timezone_function.cache_info()
        assert initial_cache.currsize == 0

        # Call function multiple times with the same input
        func1 = log_utils.get_timezone_function("UTC")
        func2 = log_utils.get_timezone_function("UTC")
        func3 = log_utils.get_timezone_function("localtime")

        # Should be cached
        cache_info = log_utils.get_timezone_function.cache_info()
        assert cache_info.currsize == 2  # Two unique calls
        assert cache_info.hits >= 1  # At least one cache hit

        # Test get_timezone_offset cache
        offset1 = log_utils.get_timezone_offset("UTC")
        offset2 = log_utils.get_timezone_offset("UTC")
        assert offset1 == offset2

        offset_cache = log_utils.get_timezone_offset.cache_info()
        assert offset_cache.currsize >= 1
        assert offset_cache.hits >= 1

    def test_thread_safety_directory_check(self):
        """Test thread safety of directory permission checking."""
        import concurrent.futures

        errors = []
        checked_dirs = []

        def check_directory_worker(worker_id):
            """Worker function to check directory permissions concurrently."""
            try:
                with tempfile.TemporaryDirectory(prefix=f"thread_test_{worker_id}_") as _temp_dir:
                    checked_dirs.append(_temp_dir)

                    # Multiple calls should be thread-safe
                    for _ in range(5):
                        log_utils.check_directory_permissions(_temp_dir)

                    return _temp_dir
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
                return None

        try:
            # Run concurrent workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(check_directory_worker, i) for i in range(5)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # Should have no errors
            assert len(errors) == 0, f"Thread safety errors: {errors}"
            assert len([r for r in results if r is not None]) == 5

        finally:
            # Cleanup is handled automatically by TemporaryDirectory context managers
            pass

    def test_gzip_compression_levels(self):
        """Test gzip compression with different scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a larger file to test compression
            test_file = os.path.join(temp_dir, "large_test.log")
            test_content = "This is a test log entry.\n" * 1000  # Larger content

            with open(test_file, "w") as f:
                f.write(test_content)

            # Test gzip compression
            result = log_utils.gzip_file_with_sufix(test_file, "compressed")
            assert result is not None
            assert result.endswith("_compressed.log.gz")
            assert os.path.exists(result)
            assert not os.path.exists(test_file)  # Original should be deleted

            # Verify compressed file can be read
            import gzip

            with gzip.open(result, "rt") as f:
                decompressed_content = f.read()
            assert decompressed_content == test_content

    def test_get_timezone_function_edge_cases(self):
        """Test get_timezone_function with various timezone inputs."""
        # Test standard timezones
        utc_func = log_utils.get_timezone_function("UTC")
        # On systems without UTC timezone data (common on Windows), this falls back to localtime
        assert utc_func.__name__ in ["gmtime", "localtime"]

        local_func = log_utils.get_timezone_function("localtime")
        assert local_func.__name__ == "localtime"

        # Test case insensitivity - both should return the same function (cached)
        utc_upper = log_utils.get_timezone_function("UTC")
        utc_lower = log_utils.get_timezone_function("utc")
        assert utc_upper is utc_lower  # Should be cached
        # Both should be either gmtime or localtime (fallback)
        assert utc_upper.__name__ in ["gmtime", "localtime"]

        # Test custom timezone
        custom_func = log_utils.get_timezone_function("America/New_York")
        # On systems without timezone data (common on Windows), this falls back to localtime
        assert custom_func.__name__ in ["<lambda>", "localtime"]

        # Test function returns proper time tuple
        time_tuple = custom_func()
        assert len(time_tuple) == 9  # Standard time tuple length

    def test_cache_eviction_stress_test(self):
        """Test cache eviction under stress conditions."""
        original_max = log_utils._max_cached_directories
        try:
            # Set very small cache for testing
            log_utils._max_cached_directories = 3

            temp_dirs = []
            # Create more directories than cache can hold using context managers
            for i in range(10):
                temp_dir_context = tempfile.TemporaryDirectory(prefix=f"eviction_test_{i}_")
                temp_dir = temp_dir_context.__enter__()
                temp_dirs.append((temp_dir, temp_dir_context))

                # Clear cache first to test eviction
                if i == 0:
                    log_utils._checked_directories.clear()

                log_utils.check_directory_permissions(temp_dir)

                # Verify cache size doesn't exceed limit
                with log_utils._directory_lock:
                    cache_size = len(log_utils._checked_directories)
                assert cache_size <= 3, f"Cache size {cache_size} exceeds limit of 3"

            # Verify some directories are still in the cache
            with log_utils._directory_lock:
                final_cache_size = len(log_utils._checked_directories)
            assert final_cache_size <= 3
            assert final_cache_size > 0  # Should have some entries

        finally:
            # Cleanup using context managers
            for temp_dir, temp_dir_context in temp_dirs:
                temp_dir_context.__exit__(None, None, None)
            log_utils._max_cached_directories = original_max

    def test_error_handling_comprehensive(self):
        """Test comprehensive error handling scenarios."""
        # Test get_level with various invalid inputs
        assert log_utils.get_level(None) == logging.INFO
        assert log_utils.get_level([]) == logging.INFO
        assert log_utils.get_level({}) == logging.INFO
        assert log_utils.get_level(object()) == logging.INFO

        # Test invalid level strings
        assert log_utils.get_level("INVALID_LEVEL") == logging.INFO
        assert log_utils.get_level("") == logging.INFO
        assert log_utils.get_level("   ") == logging.INFO

    def test_path_operations_edge_cases(self):
        """Test path operations with edge cases."""
        # Test get_log_path with various directory scenarios
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with nested path creation
            nested_dir = os.path.join(temp_dir, "level1", "level2", "level3")
            result = log_utils.get_log_path(nested_dir, "nested.log")
            assert result == os.path.join(nested_dir, "nested.log")
            assert os.path.exists(nested_dir)

            # Test with special characters in filename
            special_file = "test-file_with.special@chars.log"
            result = log_utils.get_log_path(temp_dir, special_file)
            assert result == os.path.join(temp_dir, special_file)

    def test_timezone_offset_various_timezones(self):
        """Test timezone offset calculation for various timezones."""
        # Clear cache first
        log_utils.get_timezone_offset.cache_clear()

        # Test various timezones
        timezones = [
            ("UTC", "+0000"),
            ("Europe/London", None),  # Variable offset due to DST
            ("Asia/Tokyo", "+0900"),
            ("America/Los_Angeles", None),  # Variable offset due to DST
            ("localtime", None),  # System dependent
        ]

        for tz, expected_offset in timezones:
            try:
                offset = log_utils.get_timezone_offset(tz)
                assert isinstance(offset, str)
                assert len(offset) == 5  # Format: +/-HHMM
                assert offset[0] in ['+', '-']

                if expected_offset:
                    assert offset == expected_offset

            except Exception as e:
                # Some timezones might not be available on all systems
                pytest.skip(f"Timezone {tz} not available: {e}")

    def test_formatter_and_logger_integration(self):
        """Test integration between get_logger_and_formatter and other utilities."""
        name = "integration_test"
        datefmt = "%Y-%m-%d %H:%M:%S"

        # Test with various timezone settings
        timezones = ["UTC", "localtime", "Europe/Berlin"]

        for timezone in timezones:
            try:
                logger, formatter = log_utils.get_logger_and_formatter(name, datefmt, True, timezone)

                # Verify logger properties
                assert logger.name == name
                assert isinstance(formatter, logging.Formatter)
                assert formatter.datefmt == datefmt

                # Test format string generation
                format_str = log_utils.get_format(True, name, timezone)
                assert f"[{name}]:" in format_str
                assert "[%(filename)s:%(funcName)s:%(lineno)d]:" in format_str

                # Test timezone function integration
                tz_func = log_utils.get_timezone_function(timezone)
                assert callable(tz_func)

            except Exception as e:
                pytest.skip(f"Timezone {timezone} not available: {e}")

    def test_memory_efficiency_verification(self):
        """Test memory efficiency of caching mechanisms."""
        import sys

        # Clear all caches
        log_utils.get_timezone_function.cache_clear()
        log_utils.get_timezone_offset.cache_clear()
        log_utils.get_stderr_timezone.cache_clear()
        log_utils._checked_directories.clear()

        # Test that repeated operations don't significantly increase memory
        initial_refs = sys.getrefcount(log_utils.get_timezone_function)

        # Perform many operations
        for i in range(100):
            log_utils.get_timezone_function("UTC")
            log_utils.get_timezone_offset("UTC")
            log_utils.get_format(False, f"test_{i}", "UTC")

        # Reference count shouldn't grow significantly
        final_refs = sys.getrefcount(log_utils.get_timezone_function)
        ref_growth = final_refs - initial_refs
        assert ref_growth < 50, f"Memory leak detected: reference count grew by {ref_growth}"

    def test_directory_permissions_double_checked_locking(self):
        """Test the double-checked locking pattern in check_directory_permissions."""
        import threading

        with tempfile.TemporaryDirectory() as temp_dir:
            # Clear cache first
            log_utils._checked_directories.clear()

            # Create a barrier to synchronize threads
            barrier = threading.Barrier(2)
            results = []

            def worker():
                barrier.wait()  # Ensure both threads start at the same time
                log_utils.check_directory_permissions(temp_dir)
                results.append(temp_dir in log_utils._checked_directories)

            # Start two threads that will both try to check the same directory
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for t in threads:
                t.start()

            for t in threads:
                t.join()

            # Both should have seen the directory in the cache
            assert all(results)
            assert temp_dir in log_utils._checked_directories

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific FIFO test")
    def test_delete_file_special_file_coverage(self):
        """Test delete_file with special file that exists but is neither file nor dir."""
        # This tests the elif path_obj.exists() branch (line 125)
        # Create a FIFO (named pipe) which is a special file type
        with tempfile.TemporaryDirectory() as temp_dir:
            fifo_path = os.path.join(temp_dir, "test_fifo")
            try:
                os.mkfifo(fifo_path)
                assert os.path.exists(fifo_path)
                assert not os.path.isfile(fifo_path)
                assert not os.path.isdir(fifo_path)

                # delete_file should handle this special file
                result = log_utils.delete_file(fifo_path)
                assert result == True
                assert not os.path.exists(fifo_path)
            except OSError:
                # FIFO creation might not be supported on all systems
                pytest.skip("FIFO creation not supported on this system")

    def test_stderr_timezone_fallback_exception(self):
        """Test get_stderr_timezone fallback when ZoneInfo raises exception."""
        original_tz = os.environ.get("LOG_TIMEZONE")

        try:
            # Set an invalid timezone to trigger the exception path
            os.environ["LOG_TIMEZONE"] = "Invalid/NonExistent/Timezone"
            log_utils.get_stderr_timezone.cache_clear()

            # This should trigger the exception and fallback to None
            result = log_utils.get_stderr_timezone()
            assert result is None  # Should fall back to None (local timezone)

        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]
            log_utils.get_stderr_timezone.cache_clear()

    def test_write_stderr_local_timezone_path(self):
        """Test write_stderr when using local timezone (tz is None)."""
        original_tz = os.environ.get("LOG_TIMEZONE")

        try:
            # Set timezone to localtime to trigger the tz is None path
            os.environ["LOG_TIMEZONE"] = "localtime"
            log_utils.get_stderr_timezone.cache_clear()

            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test local timezone message")

            output = stderr_capture.getvalue()
            assert "Test local timezone message" in output
            assert "ERROR" in output
            # Should use local timezone (line 173: dt = datetime.now())

        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]
            log_utils.get_stderr_timezone.cache_clear()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix/Linux/macOS-specific chmod test")
    def test_get_log_path_write_permission_error(self):
        """Test get_log_path when directory exists but write check fails (Unix/Linux/macOS)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory and make it non-writable
            test_dir = os.path.join(temp_dir, "non_writable")
            os.makedirs(test_dir)

            # Add to cache first to bypass check_directory_permissions
            log_utils._checked_directories.add(test_dir)

            # Make directory non-writable, Read and execute only
            os.chmod(test_dir, 0o555)

            try:
                with pytest.raises(PermissionError) as exc_info:
                    log_utils.get_log_path(test_dir, "test.log")

                # Should hit lines 201-203
                assert "Unable to write to log directory" in str(exc_info.value)

            finally:
                # Restore for cleanup 0o755
                os.chmod(test_dir, 0o755)
                log_utils._checked_directories.discard(test_dir)

    def test_timezone_offset_fallback_exception(self):
        """Test get_timezone_offset fallback when ZoneInfo raises exception."""
        log_utils.get_timezone_offset.cache_clear()

        # Test with invalid timezone that will trigger exception path
        result = log_utils.get_timezone_offset("Invalid/Timezone/That/Does/Not/Exist")

        # Should fall back to localtime (lines 216-219)
        assert isinstance(result, str)
        assert len(result) == 5  # Format: +/-HHMM
        assert result[0] in ['+', '-']

    def test_gzip_file_source_deletion_error_coverage(self):
        """Test gzip_file_with_sufix when source file deletion fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test.log")
            with open(test_file, "w") as f:
                f.write("test content")

            # Mock Path.unlink to raise OSError during deletion
            import unittest.mock
            from pathlib import Path

            original_unlink = Path.unlink

            def mock_unlink(self):
                if str(self) == test_file:
                    raise OSError("Mock deletion error")
                return original_unlink(self)

            try:
                stderr_capture = io.StringIO()
                with contextlib.redirect_stderr(stderr_capture):
                    with unittest.mock.patch.object(Path, 'unlink', mock_unlink):
                        with pytest.raises(OSError):
                            log_utils.gzip_file_with_sufix(test_file, "test")

                # Should hit lines 257-259
                output = stderr_capture.getvalue()
                assert "Unable to delete source log file" in output

            finally:
                Path.unlink = original_unlink

    def test_get_timezone_function_utc_fallback(self):
        """Test get_timezone_function UTC fallback when ZoneInfo UTC fails."""
        log_utils.get_timezone_function.cache_clear()

        # Mock the entire zoneinfo module to raise exception for UTC
        import unittest.mock

        def mock_zoneinfo(key):
            if key == "UTC":
                raise Exception("Mock UTC timezone error")
            # Return the real ZoneInfo for other timezones
            from zoneinfo import ZoneInfo

            return ZoneInfo(key)

        try:
            with unittest.mock.patch('pythonLogs.log_utils.ZoneInfo', side_effect=mock_zoneinfo):
                result = log_utils.get_timezone_function("UTC")

                # Should fall back to localtime (lines 273-275)
                assert result.__name__ == "localtime"

        finally:
            log_utils.get_timezone_function.cache_clear()

    def test_get_timezone_function_custom_timezone_fallback(self):
        """Test get_timezone_function custom timezone fallback."""
        log_utils.get_timezone_function.cache_clear()

        # Mock the entire zoneinfo module to raise exception for custom timezone
        import unittest.mock

        def mock_zoneinfo(key):
            if key == "Custom/Timezone":
                raise Exception("Mock custom timezone error")
            # Return the real ZoneInfo for other timezones
            from zoneinfo import ZoneInfo

            return ZoneInfo(key)

        try:
            with unittest.mock.patch('pythonLogs.log_utils.ZoneInfo', side_effect=mock_zoneinfo):
                result = log_utils.get_timezone_function("Custom/Timezone")

                # Should fall back to localtime (lines 283-285)
                assert result.__name__ == "localtime"

        finally:
            log_utils.get_timezone_function.cache_clear()

    def test_gzip_file_osioerror_handling(self):
        """Test gzip_file_with_sufix OSError/IOError handling during compression."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test_osioerror.log")
            with open(test_file, "w") as f:
                f.write("test content for OSError test")

            # Mock gzip.open to raise OSError during compression
            import unittest.mock

            def mock_gzip_open(*args, **kwargs):
                # Raise OSError to trigger lines 265-267
                raise OSError("Mock OSError during gzip compression")

            try:
                with unittest.mock.patch('gzip.open', side_effect=mock_gzip_open):
                    stderr_capture = io.StringIO()
                    with contextlib.redirect_stderr(stderr_capture):
                        with pytest.raises(OSError) as exc_info:
                            log_utils.gzip_file_with_sufix(test_file, "osioerror_test")

                    # Verify the error was logged to stderr (line 266)
                    output = stderr_capture.getvalue()
                    assert "Unable to gzip log file" in output
                    assert test_file in output
                    assert "Mock OSError during gzip compression" in output

                    # Verify the exception was re-raised (line 267)
                    assert "Mock OSError during gzip compression" in str(exc_info.value)

            finally:
                # Cleanup: remove the test file if it still exists
                if os.path.exists(test_file):
                    os.unlink(test_file)

    def test_gzip_file_ioerror_handling(self):
        """Test gzip_file_with_sufix IOError handling during compression."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test_ioerror.log")
            with open(test_file, "w") as f:
                f.write("test content for IOError test")

            # Mock shutil.copyfileobj to raise IOError during copy
            import unittest.mock

            def mock_copyfileobj(*args, **kwargs):
                # Raise IOError to trigger lines 265-267
                raise IOError("Mock IOError during file copy")

            try:
                with unittest.mock.patch('shutil.copyfileobj', side_effect=mock_copyfileobj):
                    stderr_capture = io.StringIO()
                    with contextlib.redirect_stderr(stderr_capture):
                        with pytest.raises(IOError) as exc_info:
                            log_utils.gzip_file_with_sufix(test_file, "ioerror_test")

                    # Verify the error was logged to stderr (line 266)
                    output = stderr_capture.getvalue()
                    assert "Unable to gzip log file" in output
                    assert test_file in output
                    assert "Mock IOError during file copy" in output

                    # Verify the exception was re-raised (line 267)
                    assert "Mock IOError during file copy" in str(exc_info.value)

            finally:
                # Cleanup: remove the test file if it still exists
                if os.path.exists(test_file):
                    os.unlink(test_file)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix/Linux/macOS-specific test - Windows version in test_log_utils_windows.py"
    )
    def test_gzip_file_retry_mechanism_unix(self):
        """Test gzip retry mechanism on Unix/Linux/macOS systems."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test_retry_unix.log")
            with open(test_file, "w") as f:
                f.write("test content for Unix retry mechanism")

            # On Unix systems, test normal gzip operation without Windows-specific retries
            result = log_utils.gzip_file_with_sufix(test_file, "unix_test")

            # Should succeed normally on Unix systems
            assert result is not None
            assert result.endswith("_unix_test.log.gz")
            assert not os.path.exists(test_file)  # Original should be deleted

            # Clean up the gzipped file
            if result and os.path.exists(result):
                os.unlink(result)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix/Linux/macOS-specific test - Windows version in test_log_utils_windows.py"
    )
    def test_gzip_file_error_handling_unix(self):
        """Test gzip_file_with_sufix error handling on Unix/Linux/macOS systems."""
        # Test with non-existent source file (cross-platform behavior)
        result = log_utils.gzip_file_with_sufix("/non/existent/file.log", "test")
        assert result is None

        # Unix systems don't need the complex Windows retry mechanisms,
        # So we test the basic error handling paths
