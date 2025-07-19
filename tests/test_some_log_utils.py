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

        # test permission error on creation
        directory = "/non-existent-directory"
        with pytest.raises(PermissionError) as exec_info:
            log_utils.check_directory_permissions(directory)
        assert type(exec_info.value) is PermissionError
        assert "Unable to create directory" in str(exec_info.value)

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
        temp_dir = tempfile.mkdtemp()
        test_file = "test.log"
        try:
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
        finally:
            shutil.rmtree(temp_dir)

    def test_get_format(self):
        show_location = True
        name = "test1"
        timezone = "UTC"
        result = log_utils.get_format(show_location, name, timezone)
        assert result == (
            f"[%(asctime)s.%(msecs)03d+0000]:[%(levelname)s]:[{name}]:"
            "[%(filename)s:%(funcName)s:%(lineno)d]:%(message)s"
        )

        show_location = False
        name = "test2"
        timezone = "America/Los_Angeles"
        result = log_utils.get_format(show_location, name, timezone)
        assert result.startswith(f"[%(asctime)s.%(msecs)03d-0")
        assert result.endswith(f"]:[%(levelname)s]:[{name}]:%(message)s")

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

        # test a non-existent file
        file_path = "/non-existent-directory/test2.log"
        sufix = "test2"
        result = log_utils.gzip_file_with_sufix(file_path, sufix)
        assert result is None

    def test_get_timezone_function(self):
        timezone = "UTC"
        result = log_utils.get_timezone_function(timezone)
        assert result.__name__ == "gmtime"

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
            
            # Second call should use cache (no exception should be raised)
            log_utils.check_directory_permissions(temp_dir)
            
            # Verify it's in the cache by checking the global variable
            assert temp_dir in log_utils._checked_directories
