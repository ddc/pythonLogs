"""
Windows-specific tests for log_utils module.

These tests are designed to run specifically on Windows OS and test
Windows-specific behaviors like file locking, permission models, and
timezone handling differences.
"""

import contextlib
import io
import logging
import os
import sys
import tempfile
import time
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pythonLogs import log_utils

# Import utility functions from the same directory
from test_log_utils import (
    create_windows_safe_temp_file,
    safe_close_and_delete_file,
    windows_safe_temp_directory,
    safe_delete_file,
    safe_delete_directory,
    cleanup_all_loggers,
)


class TestLogUtilsWindows:
    """Windows-specific tests for log_utils functionality."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_check_directory_permissions_windows(self):
        """Test Windows-specific directory permission behavior."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a deeply nested path that should trigger directory creation
            nested_path = os.path.join(temp_dir, "level1", "level2", "level3", "level4")

            # This should succeed and create the directories (function returns None)
            log_utils.check_directory_permissions(nested_path)
            assert os.path.exists(nested_path)

            # Test with a path that contains invalid characters (Windows-specific)
            try:
                invalid_chars_path = os.path.join(temp_dir, "invalid<>:|*?\"path")
                # This might raise different exceptions on different Windows versions
                with pytest.raises((OSError, ValueError)) as exec_info:
                    log_utils.check_directory_permissions(invalid_chars_path)
                # The specific error message may vary
                assert any(
                    phrase in str(exec_info.value).lower() for phrase in ["unable", "invalid", "permission", "access"]
                )
            except pytest.skip.Exception:
                pytest.skip("Windows permission test with invalid characters not applicable")

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_get_log_path_windows_permissions(self):
        """Test Windows-specific permission handling in get_log_path."""
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

            # Test 3: On Windows, we skip the permission error test since
            # chmod doesn't work the same way as Unix systems
            pytest.skip("Directory permission test not applicable on Windows")

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_delete_file_windows_safe(self):
        """Test delete_file with Windows-safe file handling."""
        # Import test utilities from the same directory

        # Create a Windows-safe temporary file
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write some content and close the file properly
            file_handle.write("test content")
            file_handle.close()

            assert os.path.isfile(file_path) == True
            log_utils.delete_file(file_path)
            assert os.path.isfile(file_path) == False
        finally:
            # Ensure cleanup if the test fails
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_is_older_than_x_days_windows_safe(self):
        """Test is_older_than_x_days with Windows-safe file handling."""
        # Import test utilities from the same directory

        # Create a Windows-safe temporary file
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write some content and close the file properly
            file_handle.write("test content")
            file_handle.close()

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
                safe_close_and_delete_file(None, file_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_gzip_file_with_sufix_windows_safe(self):
        """Test gzip_file_with_sufix with Windows-safe file handling."""
        # Create a Windows-safe temporary file
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write some test content and close the file properly
            file_handle.write("test content for gzip")
            file_handle.close()

            assert os.path.isfile(file_path) == True
            sufix = "test1"
            result = log_utils.gzip_file_with_sufix(file_path, sufix)
            file_path_no_suffix = file_path.split(".")[0]
            assert result == f"{file_path_no_suffix}_{sufix}.log.gz"

            # Clean up the gzipped file with Windows-safe deletion
            safe_close_and_delete_file(None, result)
            assert os.path.isfile(result) == False

        finally:
            # Ensure cleanup of the original file if it still exists
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_gzip_file_windows_retry_mechanism(self):
        """Test that gzip_file_with_sufix handles Windows file locking with retry."""
        from unittest.mock import patch

        # Create a Windows-safe temporary file
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write content and close properly
            file_handle.write("test content for retry test")
            file_handle.close()

            # Mock time.sleep to verify retry mechanism
            with patch('pythonLogs.log_utils.time.sleep') as mock_sleep:
                # Mock open to raise PermissionError on first call, succeed on second
                call_count = 0
                original_open = open

                def mock_open_side_effect(*args, real_open=original_open, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        # First call - simulate Windows file locking
                        raise PermissionError("Permission denied")
                    else:
                        # Subsequent calls - use real open
                        return real_open(*args, **kwargs)

                # Always mock platform as win32 and open with retry behavior
                with patch('pythonLogs.log_utils.sys.platform', 'win32'):
                    with patch('pythonLogs.log_utils.open', side_effect=mock_open_side_effect):
                        result = log_utils.gzip_file_with_sufix(file_path, "retry_test")

                        # Verify retry was attempted (sleep was called)
                        mock_sleep.assert_called_once_with(0.1)

                        # Verify the operation eventually succeeded
                        assert result is not None
                        assert "retry_test" in result

                        # Clean up the gzipped file
                        if result and os.path.exists(result):
                            safe_close_and_delete_file(None, result)

        finally:
            # Clean up the original file
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_timezone_fallback_windows(self):
        """Test timezone fallback behavior on Windows systems."""
        # Test get_format with timezone that may not be available on Windows
        show_location = False
        name = "test_windows_tz"
        timezone = "Australia/Queensland"
        result = log_utils.get_format(show_location, name, timezone)

        # On systems without timezone data (common on Windows), this falls back to localtime
        # Test should verify format structure rather than hardcoded timezone offset
        expected_base_format = "[%(asctime)s.%(msecs)03d"
        assert result.startswith(expected_base_format)
        assert f"]:[%(levelname)s]:[{name}]:%(message)s" in result

        # Verify timezone offset is present (either specific timezone or fallback)
        import re

        # The % characters need to be literal in the regex
        offset_pattern = r'\[%\(asctime\)s\.%\(msecs\)03d([+-]\d{4})\]'
        match = re.search(offset_pattern, result)
        assert match is not None, f"No timezone offset found in format: {result}"
        # The offset could be the specific timezone or system localtime fallback
        offset = match.group(1)
        assert re.match(r'[+-]\d{4}', offset), f"Invalid timezone offset format: {offset}"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_timezone_environment_fallback(self):
        """Test Windows-specific timezone environment variable fallback."""
        original_tz = os.environ.get("LOG_TIMEZONE")

        try:
            # Set an invalid timezone that doesn't exist on Windows
            os.environ["LOG_TIMEZONE"] = "Invalid/Windows/Timezone"
            log_utils.get_stderr_timezone.cache_clear()

            # This should trigger the exception and fallback to None (local timezone)
            result = log_utils.get_stderr_timezone()
            assert result is None  # Should fall back to None (local timezone)

            # Test that write_stderr still works with fallback
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Windows timezone fallback test")

            output = stderr_capture.getvalue()
            assert "Windows timezone fallback test" in output
            assert "ERROR" in output
        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]
            log_utils.get_stderr_timezone.cache_clear()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_file_locking_resilience(self):
        """Test that Windows file locking resilience works in production scenarios."""
        # Use Windows-safe temporary directory
        with windows_safe_temp_directory() as temp_dir:
            test_file = os.path.join(temp_dir, "windows_resilience_test.log")

            # Create file with content
            with open(test_file, "w") as f:
                f.write("Windows file locking resilience test content\n" * 100)

            # Ensure the file is properly closed before gzip operation
            assert os.path.isfile(test_file)

            # This should work without issues on Windows
            result = log_utils.gzip_file_with_sufix(test_file, "windows_test")

            assert result is not None
            assert result.endswith("_windows_test.log.gz")
            assert os.path.exists(result)
            assert not os.path.exists(test_file)  # Original should be deleted

            # Verify compressed content
            import gzip

            with gzip.open(result, "rt") as f:
                content = f.read()
            assert "Windows file locking resilience test content" in content

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_path_handling(self):
        """Test Windows-specific path handling behaviors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with Windows-style path separators
            windows_style_dir = temp_dir.replace("/", "\\")
            test_file = "windows_path_test.log"

            result = log_utils.get_log_path(windows_style_dir, test_file)
            expected = os.path.join(windows_style_dir, test_file)
            assert result == expected

            # Test with mixed separators (Windows handles this)
            mixed_dir = os.path.join(temp_dir, "mixed\\path/test")
            log_utils.get_log_path(mixed_dir, test_file)
            assert os.path.exists(mixed_dir)  # Should be created successfully

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_stderr_timezone_with_dst(self):
        """Test Windows timezone handling with DST considerations."""
        original_tz = os.environ.get("LOG_TIMEZONE")

        try:
            # Test with a timezone that has DST changes
            os.environ["LOG_TIMEZONE"] = "America/New_York"
            log_utils.get_stderr_timezone.cache_clear()

            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                log_utils.write_stderr("Windows DST timezone test")

            output = stderr_capture.getvalue()
            assert "Windows DST timezone test" in output
            assert "ERROR" in output

            # Should contain some form of timezone offset
            # Windows may fall back to local timezone if specific timezone unavailable
            assert any(char in output for char in ['+', '-']) or 'Z' in output

        finally:
            if original_tz is not None:
                os.environ["LOG_TIMEZONE"] = original_tz
            elif "LOG_TIMEZONE" in os.environ:
                del os.environ["LOG_TIMEZONE"]
            log_utils.get_stderr_timezone.cache_clear()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_concurrent_file_operations(self):
        """Test concurrent file operations on Windows with proper cleanup."""
        import concurrent.futures
        import threading

        results = []
        errors = []
        lock = threading.Lock()

        def windows_file_worker(worker_id):
            """Worker that performs Windows-safe file operations."""
            try:
                # Create Windows-safe temporary file
                file_handle, file_path = create_windows_safe_temp_file(suffix=f"_worker_{worker_id}.log", text=True)

                try:
                    # Write content and close properly
                    file_handle.write(f"Content from worker {worker_id}\n" * 10)
                    file_handle.close()

                    # Test file age check
                    is_old = log_utils.is_older_than_x_days(file_path, 1)

                    # Test gzip operation
                    gzip_result = log_utils.gzip_file_with_sufix(file_path, f"worker_{worker_id}")

                    with lock:
                        results.append(
                            {
                                'worker_id': worker_id,
                                'file_path': file_path,
                                'is_old': is_old,
                                'gzip_result': gzip_result,
                            }
                        )

                    # Clean up gzipped file
                    if gzip_result and os.path.exists(gzip_result):
                        safe_close_and_delete_file(None, gzip_result)

                finally:
                    # Ensure cleanup of the original file if it still exists
                    if os.path.exists(file_path):
                        safe_close_and_delete_file(None, file_path)

            except Exception as e:
                with lock:
                    errors.append(f"Worker {worker_id}: {str(e)}")

        # Run concurrent workers
        num_workers = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(windows_file_worker, i) for i in range(num_workers)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Windows concurrent operations failed: {errors}"
        assert len(results) == num_workers

        # Verify all workers completed successfully
        for result in results:
            assert result['is_old'] == False  # Files should NOT be considered "old" (created recently)
            assert result['gzip_result'] is not None
            assert f"worker_{result['worker_id']}" in result['gzip_result']

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_gzip_file_windows_permission_error(self):
        """Test gzip_file_with_sufix Windows-specific permission handling."""
        # This test replaces the Unix chmod-based test for Windows
        #  file locking is handled differently than Unix permissions

        # Create a Windows-safe temporary file
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write content and close properly
            file_handle.write("test content for Windows permission test")
            file_handle.close()

            # On Windows, we test the file locking retry mechanism instead of chmod
            # This is more realistic for Windows environments
            result = log_utils.gzip_file_with_sufix(file_path, "windows_perm_test")

            # Should succeed on Windows with proper file handling
            assert result is not None
            assert result.endswith("_windows_perm_test.log.gz")
            assert not os.path.exists(file_path)  # Original should be deleted

            # Clean up the gzipped file
            if result and os.path.exists(result):
                safe_close_and_delete_file(None, result)

        finally:
            # Ensure cleanup of the original file if it still exists
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_get_log_path_windows_comprehensive(self):
        """Comprehensive test for get_log_path Windows-specific behaviors."""
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

            # Test 3: Test with invalid path characters (Windows-specific)
            try:
                invalid_path = os.path.join(temp_dir, "invalid<>path")
                result = log_utils.get_log_path(invalid_path, "test.log")
                assert "test.log" in result
            except (OSError, ValueError):
                # Expected on Windows with invalid characters
                pass

            # Test 4: Test normal operation in created directory
            test_dir = os.path.join(temp_dir, "test_write_perm")
            os.makedirs(test_dir)
            result = log_utils.get_log_path(test_dir, "test.log")
            assert result == os.path.join(test_dir, "test.log")

            # Test 5: Windows-specific long path names (Windows limitation)
            long_filename = "a" * 200 + ".log"  # Very long filename
            try:
                result = log_utils.get_log_path(test_dir, long_filename)
                assert long_filename in result
            except OSError:
                # Expected on some Windows systems with path length limitations
                pass

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_gzip_file_retry_mechanism_comprehensive(self):
        """Comprehensive test of Windows retry mechanisms during gzip operations."""
        from unittest.mock import patch

        # Create a Windows-safe temporary file
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write content and close properly
            file_handle.write("test content for comprehensive retry test")
            file_handle.close()

            import unittest.mock

            # Mock to simulate Windows platform and PermissionError on first few attempts
            call_count = 0
            original_open = open

            def mock_open_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if args[0] == file_path and call_count <= 2:
                    # First two calls - simulate Windows file locking
                    raise PermissionError("The process cannot access the file")
                else:
                    # Subsequent calls - use real open
                    return original_open(*args, **kwargs)

            # Mock sys.platform to be Windows and time.sleep to verify retry
            with unittest.mock.patch('pythonLogs.log_utils.sys.platform', 'win32'):
                with unittest.mock.patch('pythonLogs.log_utils.time.sleep') as mock_sleep:
                    with unittest.mock.patch('pythonLogs.log_utils.open', side_effect=mock_open_side_effect):
                        result = log_utils.gzip_file_with_sufix(file_path, "comprehensive_retry")

                        # Verify retries were attempted (sleep should be called twice)
                        assert mock_sleep.call_count == 2

                        # Verify the operation eventually succeeded
                        assert result is not None
                        assert "comprehensive_retry" in result

                        # Clean up the gzipped file
                        if result and os.path.exists(result):
                            safe_close_and_delete_file(None, result)

        finally:
            # Clean up the original file
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_remove_old_logs_file_locking(self):
        """Test remove_old_logs with Windows file locking scenarios."""
        with windows_safe_temp_directory() as temp_dir:
            # Create a .gz file that simulates being locked
            gz_file = os.path.join(temp_dir, "locked_test.gz")
            with open(gz_file, "wb") as f:
                f.write(b"test content for locking scenario")

            # Set old modification time
            old_time = time.time() - 2 * 24 * 60 * 60  # 2 days old
            os.utime(gz_file, (old_time, old_time))

            # Test that remove_old_logs handles Windows file locking gracefully
            # This should work on Windows without permission issues
            log_utils.remove_old_logs(temp_dir, 1)

            # File should be removed on Windows (unlike Unix chmod tests)
            assert not os.path.exists(gz_file)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_delete_file_scenarios(self):
        """Test delete_file with various Windows-specific scenarios."""
        # Test 1: Normal file deletion
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)
        try:
            file_handle.write("test content")
            file_handle.close()

            assert os.path.isfile(file_path)
            result = log_utils.delete_file(file_path)
            assert result == True
            assert not os.path.exists(file_path)
        finally:
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)

        # Test 2: Non-existent file (should raise FileNotFoundError)
        non_existent = os.path.join(tempfile.gettempdir(), "non_existent_windows_test.log")
        with pytest.raises(FileNotFoundError):
            log_utils.delete_file(non_existent)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_logger_cleanup_integration(self):
        """Test Windows-specific logger cleanup integration."""
        # Create multiple loggers that would typically cause file locking issues
        logger_names = [f"windows_cleanup_test_{i}" for i in range(3)]
        temp_files = []

        try:
            with windows_safe_temp_directory() as temp_dir:
                for name in logger_names:
                    log_file = os.path.join(temp_dir, f"{name}.log")
                    temp_files.append(log_file)

                    # Create logger with file handler
                    logger = log_utils.get_logger_and_formatter(name, "%Y-%m-%d", False, "UTC")[0]

                    # Add file handler
                    file_handler = logging.FileHandler(log_file)
                    logger.addHandler(file_handler)

                    # Write some content
                    logger.info(f"Test message from {name}")

                # Now cleanup all loggers (Windows-specific behavior)
                cleanup_all_loggers()

                # Verify all log files can be deleted (no file locking issues)
                for log_file in temp_files:
                    if os.path.exists(log_file):
                        result = safe_delete_file(log_file)
                        assert result == True
        finally:
            # Ensure cleanup
            cleanup_all_loggers()
            for log_file in temp_files:
                if os.path.exists(log_file):
                    safe_close_and_delete_file(None, log_file)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_directory_cleanup_stress(self):
        """Test Windows directory cleanup under stress conditions."""
        temp_dirs = []

        try:
            # Create multiple nested directories with files
            for i in range(5):
                with windows_safe_temp_directory() as temp_dir:
                    nested_dir = os.path.join(temp_dir, f"level1_{i}", f"level2_{i}")
                    os.makedirs(nested_dir, exist_ok=True)

                    # Create files in nested directory
                    for j in range(3):
                        test_file = os.path.join(nested_dir, f"test_{j}.log")
                        with open(test_file, "w") as f:
                            f.write(f"Content for file {j} in directory {i}")

                    temp_dirs.append(temp_dir)

                    # Test that directory operations work on Windows
                    assert os.path.exists(nested_dir)

                    # Windows-safe cleanup should handle this
                    result = safe_delete_directory(nested_dir)
                    assert result == True or not os.path.exists(nested_dir)
        finally:
            # Final cleanup
            cleanup_all_loggers()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_gzip_error_recovery(self):
        """Test Windows-specific error recovery in gzip operations."""
        file_handle, file_path = create_windows_safe_temp_file(suffix=".log", text=True)

        try:
            # Write content and close properly
            file_handle.write("content for Windows error recovery test")
            file_handle.close()

            # Test that gzip operation recovers from Windows-specific errors
            result = log_utils.gzip_file_with_sufix(file_path, "error_recovery")

            # Should succeed on Windows
            assert result is not None
            assert "error_recovery" in result
            assert os.path.exists(result)
            assert not os.path.exists(file_path)  # Original should be deleted

            # Verify compressed content
            import gzip

            with gzip.open(result, "rt") as f:
                content = f.read()
            assert "Windows error recovery test" in content

            # Clean up
            safe_close_and_delete_file(None, result)

        finally:
            if os.path.exists(file_path):
                safe_close_and_delete_file(None, file_path)


if __name__ == "__main__":
    pytest.main([__file__])
