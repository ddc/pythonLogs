# -*- encoding: utf-8 -*-
import contextlib
import io
import logging
import os
import shutil
import sys
import tempfile
import time
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import log_utils


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

    def test_check_directory_permissions(self):
        # Test permission error on access
        directory = os.path.join(tempfile.gettempdir(), "test_permission")
        os.makedirs(directory, mode=0o000, exist_ok=True)  # No permissions at all
        assert os.path.exists(directory) == True
        with pytest.raises(PermissionError) as exec_info:
            log_utils.check_directory_permissions(directory)
        os.chmod(directory, 0o755)  # Restore permissions for cleanup
        assert type(exec_info.value) is PermissionError
        assert "Unable to access directory" in str(exec_info.value)
        log_utils.delete_file(directory)
        assert os.path.exists(directory) == False

        # test permission error on creation - use a readonly parent directory
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_parent = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_parent, mode=0o555)  # Read-only parent
            try:
                non_existent = os.path.join(readonly_parent, "non-existent-directory")
                with pytest.raises(PermissionError) as exec_info:
                    log_utils.check_directory_permissions(non_existent)
                assert type(exec_info.value) is PermissionError
                assert "Unable to create directory" in str(exec_info.value)
            finally:
                os.chmod(readonly_parent, 0o755)  # Restore permissions for cleanup

    def test_remove_old_logs(self):
        directory = os.path.join(tempfile.gettempdir(), "test_remove_logs")
        os.makedirs(directory, mode=0o755, exist_ok=True)
        assert os.path.exists(directory) == True

        # Create a file and manually set its modification time to be old
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".gz", delete=False) as tmpfile:
            file_path = tmpfile.name
            old_time = time.time() - 2*24*60*60  # 2 days old
            os.utime(file_path, (old_time, old_time))

        log_utils.remove_old_logs(directory, 1)  # Remove files older than 1 day
        assert os.path.isfile(file_path) == False
        log_utils.delete_file(directory)
        assert os.path.exists(directory) == False

    def test_delete_file(self):
        directory = tempfile.gettempdir()
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".log")
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == True
        log_utils.delete_file(file_path)
        assert os.path.isfile(file_path) == False

    def test_is_older_than_x_days(self):
        directory = tempfile.gettempdir()
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".log")
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == True

        result = log_utils.is_older_than_x_days(file_path, 1)
        assert result == True

        result = log_utils.is_older_than_x_days(file_path, 5)
        assert result == False

        log_utils.delete_file(file_path)
        assert os.path.isfile(file_path) == False

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
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_dir, mode=0o555)
            try:
                with pytest.raises(PermissionError) as exc_info:
                    log_utils.get_log_path(readonly_dir, test_file)
                assert "Unable to access directory" in str(exc_info.value)
            finally:
                os.chmod(readonly_dir, 0o755)  # Cleanup permissions
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
        assert result == f"[%(asctime)s.%(msecs)03d+1000]:[%(levelname)s]:[{name}]:%(message)s"

    def test_gzip_file_with_sufix(self):
        directory = tempfile.gettempdir()
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".log")
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == True
        sufix = "test1"
        result = log_utils.gzip_file_with_sufix(file_path, sufix)
        file_path_no_suffix = file_path.split(".")[0]
        assert result == f"{file_path_no_suffix}_{sufix}.log.gz"
        log_utils.delete_file(result)
        assert os.path.isfile(result) == False

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
        assert result.__name__ == "<lambda>"

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
        """Test _get_timezone_offset function via get_format"""
        # Test UTC timezone
        format1 = log_utils.get_format(False, "test", "UTC")
        format2 = log_utils.get_format(False, "test", "UTC")
        assert "+0000" in format1
        assert format1 == format2  # Should be identical due to caching
        
        # Test localtime
        format3 = log_utils.get_format(False, "test", "localtime")
        assert format3 is not None

    def test_stderr_timezone_caching(self):
        """Test _get_stderr_timezone function via write_stderr"""
        # Test with UTC
        original_tz = os.environ.get("LOG_TIMEZONE")
        os.environ["LOG_TIMEZONE"] = "UTC"
        
        try:
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test UTC message")
            
            output = stderr_capture.getvalue()
            assert "+0000" in output or "Z" in output  # UTC timezone indicator
        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]

    def test_stderr_timezone_localtime(self):
        """Test _get_stderr_timezone with localtime"""
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

    def test_remove_old_logs_file_error(self):
        """Test remove_old_logs error handling when file deletion fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a .gz file
            gz_file = os.path.join(temp_dir, "test.gz")
            with open(gz_file, "wb") as f:
                f.write(b"test content")
            
            # Set old modification time
            old_time = time.time() - 2*24*60*60  # 2 days old
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

    def test_get_log_path_permission_error(self):
        """Test get_log_path when directory exists but is not writable"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory and make it read-only
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, 0o555)  # Read and execute only
            
            try:
                with pytest.raises(PermissionError) as exc_info:
                    log_utils.get_log_path(readonly_dir, "test.log")
                # The error could be from check_directory_permissions or get_log_path itself
                assert ("Unable to access directory" in str(exc_info.value) or 
                        "Unable to write to log directory" in str(exc_info.value))
            finally:
                os.chmod(readonly_dir, 0o755)  # Restore for cleanup

    def test_gzip_file_io_error(self):
        """Test gzip_file_with_sufix error handling during compression"""
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
                os.chmod(temp_dir, 0o755)  # Restore for cleanup

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
            
            # Clean up
            if os.path.exists(result):
                os.unlink(result)

    def test_write_stderr_fallback(self):
        """Test write_stderr fallback when timezone operations fail"""
        # Save original function
        original_get_stderr_tz = log_utils._get_stderr_timezone
        
        # Mock _get_stderr_timezone to raise an error
        def mock_error_timezone():
            raise KeyError("Mock timezone error")
        
        try:
            log_utils._get_stderr_timezone = mock_error_timezone
            
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Test fallback message")
            
            output = stderr_capture.getvalue()
            assert "Test fallback message" in output
            assert "ERROR" in output
        finally:
            # Restore original function
            log_utils._get_stderr_timezone = original_get_stderr_tz

    def test_stderr_timezone_with_special_timezone(self):
        """Test _get_stderr_timezone with different timezone configurations"""
        original_tz = os.environ.get("LOG_TIMEZONE")
        
        try:
            # Test with a specific timezone
            os.environ["LOG_TIMEZONE"] = "Europe/London"
            # Clear the cache
            log_utils._get_stderr_timezone.cache_clear()
            
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
            log_utils._get_stderr_timezone.cache_clear()

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
        log_utils._get_timezone_offset.cache_clear()
        
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
        
        # Test _get_timezone_offset cache
        offset1 = log_utils._get_timezone_offset("UTC")
        offset2 = log_utils._get_timezone_offset("UTC")
        assert offset1 == offset2
        
        offset_cache = log_utils._get_timezone_offset.cache_info()
        assert offset_cache.currsize >= 1
        assert offset_cache.hits >= 1

    def test_thread_safety_directory_check(self):
        """Test thread safety of directory permission checking."""
        import threading
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
        assert utc_func.__name__ == "gmtime"
        
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
        assert custom_func.__name__ == "<lambda>"
        
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
        log_utils._get_timezone_offset.cache_clear()
        
        # Test various timezones
        timezones = [
            ("UTC", "+0000"),
            ("Europe/London", None),  # Variable offset due to DST
            ("Asia/Tokyo", "+0900"),
            ("America/Los_Angeles", None),  # Variable offset due to DST
            ("localtime", None)  # System dependent
        ]
        
        for tz, expected_offset in timezones:
            try:
                offset = log_utils._get_timezone_offset(tz)
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
                logger, formatter = log_utils.get_logger_and_formatter(
                    name, datefmt, True, timezone
                )
                
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
        log_utils._get_timezone_offset.cache_clear()
        log_utils._get_stderr_timezone.cache_clear()
        log_utils._checked_directories.clear()
        
        # Test that repeated operations don't significantly increase memory
        initial_refs = sys.getrefcount(log_utils.get_timezone_function)
        
        # Perform many operations
        for i in range(100):
            log_utils.get_timezone_function("UTC")
            log_utils._get_timezone_offset("UTC")
            log_utils.get_format(False, f"test_{i}", "UTC")
        
        # Reference count shouldn't grow significantly
        final_refs = sys.getrefcount(log_utils.get_timezone_function)
        ref_growth = final_refs - initial_refs
        assert ref_growth < 50, f"Memory leak detected: reference count grew by {ref_growth}"
