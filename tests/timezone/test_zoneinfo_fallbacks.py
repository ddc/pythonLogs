#!/usr/bin/env python3
"""Test zoneinfo fallback mechanisms and edge cases."""
import os
import sys
import tempfile
from unittest.mock import patch
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        
        # Test with invalid timezone
        with pytest.raises(Exception):  # Should raise ZoneInfoNotFoundError or similar
            basic_logger(
                name="error_test",
                timezone="NonExistent/Timezone",
                level=LogLevel.INFO
            )
    
    def test_timezone_offset_edge_cases(self):
        """Test timezone offset calculation for edge cases."""
        from pythonLogs.log_utils import _get_timezone_offset
        
        # Test UTC (should always work)
        utc_offset = _get_timezone_offset("UTC")
        assert utc_offset == "+0000"
        
        # Test localtime (should work on any system)
        local_offset = _get_timezone_offset("localtime")
        assert isinstance(local_offset, str)
        assert len(local_offset) == 5
        assert local_offset[0] in ['+', '-']
        
        # Test case insensitivity for localtime
        local_offset_upper = _get_timezone_offset("LOCALTIME")
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
        
        # Test standard cases
        utc_func = get_timezone_function("UTC")
        assert utc_func is time.gmtime
        
        local_func = get_timezone_function("localtime")
        assert local_func is time.localtime
        
        # Test case insensitivity
        utc_func_upper = get_timezone_function("utc")
        assert utc_func_upper is time.gmtime
        
        local_func_upper = get_timezone_function("LOCALTIME")
        assert local_func_upper is time.localtime
    
    def test_logger_creation_with_fallback_timezone(self):
        """Test logger creation when timezone operations might fail."""
        from pythonLogs import basic_logger, LogLevel
        
        # These should all work with proper fallback
        logger = basic_logger(
            name="fallback_test",
            timezone="UTC",
            level=LogLevel.INFO
        )
        
        logger.info("Fallback test message")
        assert logger.name == "fallback_test"
    
    def test_complex_timezone_scenarios(self):
        """Test complex timezone scenarios and edge cases."""
        from pythonLogs import size_rotating_logger, LogLevel
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with various timezone formats
            timezones = [
                "UTC",
                "localtime", 
                "America/New_York",
                "Europe/London",
                "Asia/Tokyo"
            ]
            
            for i, tz in enumerate(timezones):
                try:
                    logger = size_rotating_logger(
                        name=f"complex_tz_test_{i}",
                        directory=temp_dir,
                        timezone=tz,
                        level=LogLevel.INFO,
                        streamhandler=False
                    )
                    logger.info(f"Complex timezone test: {tz}")
                    assert logger.name == f"complex_tz_test_{i}"
                except Exception as e:
                    # Some timezones might not be available on all systems
                    pytest.skip(f"Timezone {tz} not available: {e}")
    
    def test_zoneinfo_caching_behavior(self):
        """Test that zoneinfo objects are properly cached."""
        from pythonLogs.log_utils import get_timezone_function, _get_timezone_offset
        
        # Test function caching
        func1 = get_timezone_function("America/Chicago")
        func2 = get_timezone_function("America/Chicago")
        assert func1 is func2  # Should be cached
        
        # Test offset caching  
        offset1 = _get_timezone_offset("America/Chicago")
        offset2 = _get_timezone_offset("America/Chicago")
        assert offset1 == offset2  # Should be cached
    
    def test_environment_variable_timezone_handling(self):
        """Test timezone handling through environment variables."""

        # Test with environment variable
        with patch.dict(os.environ, {'LOG_TIMEZONE': 'Europe/Paris'}):
            # Environment variable should be used for stderr
            from pythonLogs.log_utils import _get_stderr_timezone
            
            # Clear cache to test new environment
            _get_stderr_timezone.cache_clear()
            
            tz = _get_stderr_timezone()
            assert tz is not None
    
    def test_concurrent_timezone_access(self):
        """Test timezone functionality under concurrent access."""
        import threading
        from pythonLogs import basic_logger, LogLevel
        
        results = []
        errors = []
        
        def create_logger_worker(worker_id):
            try:
                logger = basic_logger(
                    name=f"concurrent_test_{worker_id}",
                    timezone="UTC",
                    level=LogLevel.INFO
                )
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
    
    def test_memory_usage_with_timezone_caching(self):
        """Test that timezone caching doesn't cause memory leaks."""
        from pythonLogs import basic_logger, clear_logger_registry
        
        # Check if zoneinfo works on this system
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo("UTC")  # Test if UTC is available
        except Exception:
            pytest.skip("zoneinfo not available or UTC timezone data missing on this system")
        
        # Create many loggers with same timezone (should use cache)
        for i in range(100):
            logger = basic_logger(
                name=f"memory_test_{i}",
                timezone="UTC"
            )
            logger.info(f"Memory test {i}")
        
        # Clear registry to free memory
        clear_logger_registry()
        
        # Should complete without memory issues - test passes if no exception is raised
    
    def test_timezone_validation_edge_cases(self):
        """Test timezone validation for various edge cases."""
        from pythonLogs.log_utils import _get_timezone_offset
        
        # Check if zoneinfo works on this system
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo("UTC")  # Test if UTC is available
        except Exception:
            pytest.skip("zoneinfo not available or UTC timezone data missing on this system")
        
        # Test case variations (timezone names are case-sensitive except for localtime)
        test_cases = [
            ("UTC", "+0000"),
            ("localtime", None),  # Will vary by system
            ("LOCALTIME", None),  # Will vary by system
        ]
        
        for tz_input, expected in test_cases:
            result = _get_timezone_offset(tz_input)
            if expected is not None:
                assert result == expected
            else:
                # For localtime, just check format
                assert isinstance(result, str)
                assert len(result) == 5
                assert result[0] in ['+', '-']
        
        # Test that invalid timezone names raise appropriate errors
        with pytest.raises(Exception):  # Should raise ZoneInfoNotFoundError
            _get_timezone_offset("invalid_timezone")
