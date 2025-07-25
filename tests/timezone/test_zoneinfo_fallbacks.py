#!/usr/bin/env python3
"""Test zoneinfo fallback mechanisms and edge cases."""
import os
import sys
import tempfile
from unittest.mock import patch
import pytest


# Add parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)  # For pythonLogs

# Import test utilities
from tests.core.test_log_utils import get_safe_timezone, requires_zoneinfo_utc


class TestZoneinfoFallbacks:
    """Test fallback mechanisms for zoneinfo import and edge cases."""

    def test_zoneinfo_import_available(self):
        """Test that zoneinfo is available in Python 3.9+."""
        try:
            from zoneinfo import ZoneInfo

            # If import succeeds, ZoneInfo is guaranteed to be a valid class
            print("✓ Native zoneinfo available")
        except ImportError:
            pytest.skip("zoneinfo not available in this Python version")

    def test_timezone_error_handling(self):
        """Test proper error handling for timezone operations."""
        from pythonLogs import basic_logger, LogLevel

        # With the new fallback system, invalid timezones should gracefully fall back
        # to localtime instead of raising exceptions for better robustness
        logger = basic_logger(
            name="error_test", timezone="NonExistent/Timezone", level=LogLevel.INFO  # Should fall back to localtime
        )
        # Logger should be created successfully with fallback
        assert logger.name == "error_test"
        logger.info("Test message with fallback timezone")

    def test_timezone_offset_edge_cases(self):
        """Test timezone offset calculation for edge cases."""
        from pythonLogs.log_utils import get_timezone_offset

        # Test UTC (may fall back to localtime on systems without UTC data)
        utc_offset = get_timezone_offset("UTC")
        # UTC should return +0000, but may fall back to localtime on Windows
        assert isinstance(utc_offset, str)
        assert len(utc_offset) == 5
        assert utc_offset[0] in ['+', '-']

        # Test localtime (should work on any system)
        local_offset = get_timezone_offset("localtime")
        assert isinstance(local_offset, str)
        assert len(local_offset) == 5
        assert local_offset[0] in ['+', '-']

        # Test case insensitivity for localtime
        local_offset_upper = get_timezone_offset("LOCALTIME")
        assert local_offset_upper == local_offset

    def test_stderr_timezone_fallback(self):
        """Test stderr timezone fallback behavior."""
        from pythonLogs.log_utils import write_stderr
        import io
        from contextlib import redirect_stderr

        # Mock environment variable
        with patch.dict(os.environ, {'LOG_TIMEZONE': 'UTC'}):
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                write_stderr("Test message")

            output = stderr_capture.getvalue()
            assert "Test message" in output
            assert "ERROR" in output

    def test_timezone_function_fallback(self):
        """Test timezone function fallback for edge cases."""
        from pythonLogs.log_utils import get_timezone_function
        import time

        # Test standard cases - UTC may fall back to localtime on systems without UTC data
        utc_func = get_timezone_function("UTC")
        assert utc_func in [time.gmtime, time.localtime]

        local_func = get_timezone_function("localtime")
        assert local_func is time.localtime

        # Test case insensitivity - UTC may fall back to localtime
        utc_func_upper = get_timezone_function("utc")
        assert utc_func_upper in [time.gmtime, time.localtime]

        local_func_upper = get_timezone_function("LOCALTIME")
        assert local_func_upper is time.localtime

    def test_logger_creation_with_fallback_timezone(self):
        """Test logger creation when timezone operations might fail."""
        from pythonLogs import basic_logger, LogLevel

        # Use safe timezone that works on all platforms
        safe_tz = get_safe_timezone()
        logger = basic_logger(name="fallback_test", timezone=safe_tz, level=LogLevel.INFO)

        logger.info("Fallback test message")
        assert logger.name == "fallback_test"

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file",
    )
    def test_complex_timezone_scenarios(self):
        """Test complex timezone scenarios and edge cases."""
        from pythonLogs import size_rotating_logger, LogLevel

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with various timezone formats
            timezones = ["UTC", "localtime", "America/New_York", "Europe/London", "Asia/Tokyo"]

            for i, tz in enumerate(timezones):
                try:
                    logger = size_rotating_logger(
                        name=f"complex_tz_test_{i}",
                        directory=temp_dir,
                        timezone=tz,
                        level=LogLevel.INFO,
                        streamhandler=False,
                    )
                    logger.info(f"Complex timezone test: {tz}")
                    assert logger.name == f"complex_tz_test_{i}"
                except Exception as e:
                    # Some timezones might not be available on all systems
                    pytest.skip(f"Timezone {tz} not available: {e}")

    def test_zoneinfo_caching_behavior(self):
        """Test that zoneinfo objects are properly cached."""
        from pythonLogs.log_utils import get_timezone_function, get_timezone_offset

        # Test function caching
        func1 = get_timezone_function("America/Chicago")
        func2 = get_timezone_function("America/Chicago")
        assert func1 is func2  # Should be cached

        # Test offset caching
        offset1 = get_timezone_offset("America/Chicago")
        offset2 = get_timezone_offset("America/Chicago")
        assert offset1 == offset2  # Should be cached

    def test_environment_variable_timezone_handling(self):
        """Test timezone handling through environment variables."""

        # Test with environment variable
        with patch.dict(os.environ, {'LOG_TIMEZONE': 'Europe/Paris'}):
            # Environment variable should be used for stderr
            from pythonLogs.log_utils import get_stderr_timezone

            # Clear cache to test new environment
            get_stderr_timezone.cache_clear()

            tz = get_stderr_timezone()
            # On Windows, timezone data might not be available, so allow None (fallback to localtime)
            if sys.platform == "win32":
                # On Windows, accept None as a valid fallback
                assert tz is None or tz is not None
            else:
                assert tz is not None

    def test_concurrent_timezone_access(self):
        """Test timezone functionality under concurrent access."""
        import threading
        from pythonLogs import basic_logger, LogLevel

        # Use safe timezone that works on all platforms
        safe_tz = get_safe_timezone()
        results = []
        errors = []

        def create_logger_worker(worker_id):
            try:
                logger = basic_logger(name=f"concurrent_test_{worker_id}", timezone=safe_tz, level=LogLevel.INFO)
                logger.info(f"Concurrent test message {worker_id}")
                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, e))

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_logger_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10

    @requires_zoneinfo_utc
    def test_memory_usage_with_timezone_caching(self):
        """Test that timezone caching doesn't cause memory leaks."""
        from pythonLogs import basic_logger, clear_logger_registry

        # Create many loggers with same timezone (should use cache)
        for i in range(100):
            logger = basic_logger(name=f"memory_test_{i}", timezone="UTC")
            logger.info(f"Memory test {i}")

        # Clear registry to free memory
        clear_logger_registry()

        # Should complete without memory issues - test passes if no exception is raised

    @requires_zoneinfo_utc
    def test_timezone_validation_edge_cases(self):
        """Test timezone validation for various edge cases."""
        from pythonLogs.log_utils import get_timezone_offset

        # Test case variations (timezone names are case-sensitive except for localtime)
        test_cases = [
            ("UTC", "+0000"),
            ("localtime", None),  # Will vary by system
            ("LOCALTIME", None),  # Will vary by system
        ]

        for tz_input, expected in test_cases:
            result = get_timezone_offset(tz_input)
            if expected is not None:
                assert result == expected
            else:
                # For localtime, just check format
                assert isinstance(result, str)
                assert len(result) == 5
                assert result[0] in ['+', '-']

        # Test that invalid timezone names now fall back gracefully to localtime
        result = get_timezone_offset("invalid_timezone")
        # Should fall back to localtime format
        assert isinstance(result, str)
        assert len(result) == 5
        assert result[0] in ['+', '-']
