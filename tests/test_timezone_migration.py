#!/usr/bin/env python3
"""Test timezone functionality after pytz to zoneinfo migration."""
import os
import sys
import tempfile
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import (
    basic_logger,
    size_rotating_logger,
    timed_rotating_logger,
    LogLevel,
    RotateWhen,
    LoggerFactory,
    LoggerType,
    clear_logger_registry,
)
from pythonLogs.log_utils import (
    get_timezone_function,
    _get_timezone_offset,
    write_stderr,
    _get_stderr_timezone,
)


class TestTimezoneZoneinfo:
    """Test cases for timezone functionality using zoneinfo instead of pytz."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()
    
    def test_zoneinfo_import_success(self):
        """Test that ZoneInfo is properly imported."""
        from pythonLogs.log_utils import ZoneInfo
        
        # Should be able to create timezone objects
        utc_tz = ZoneInfo("UTC")
        assert utc_tz is not None
    
    def test_utc_timezone_basic_logger(self):
        """Test UTC timezone with basic logger."""
        logger = basic_logger(
            name="utc_test",
            level=LogLevel.INFO,
            timezone="UTC"
        )
        
        # Should not raise exceptions
        logger.info("UTC timezone test message")
        assert logger.name == "utc_test"
    
    def test_localtime_timezone_basic_logger(self):
        """Test localtime timezone with basic logger."""
        logger = basic_logger(
            name="local_test",
            level=LogLevel.INFO,
            timezone="localtime"
        )
        
        logger.info("Local timezone test message")
        assert logger.name == "local_test"
    
    def test_named_timezone_basic_logger(self):
        """Test named timezone (America/New_York) with basic logger."""
        logger = basic_logger(
            name="ny_test",
            level=LogLevel.INFO,
            timezone="America/New_York"
        )
        
        logger.info("New York timezone test message")
        assert logger.name == "ny_test"
    
    def test_timezone_with_size_rotating_logger(self):
        """Test timezone functionality with size rotating logger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = size_rotating_logger(
                name="size_tz_test",
                directory=temp_dir,
                level=LogLevel.INFO,
                timezone="America/Chicago",
                streamhandler=False
            )
            
            logger.info("Size rotating with timezone test")
            assert logger.name == "size_tz_test"
    
    def test_timezone_with_timed_rotating_logger(self):
        """Test timezone functionality with timed rotating logger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = timed_rotating_logger(
                name="timed_tz_test",
                directory=temp_dir,
                level=LogLevel.INFO,
                timezone="Europe/London",
                when=RotateWhen.DAILY,
                streamhandler=False
            )
            
            logger.info("Timed rotating with timezone test")
            assert logger.name == "timed_tz_test"
    
    def test_timezone_factory_pattern(self):
        """Test timezone functionality through factory pattern."""
        logger = LoggerFactory.create_logger(
            LoggerType.BASIC,
            name="factory_tz_test",
            level=LogLevel.DEBUG,
            timezone="Asia/Tokyo"
        )
        
        logger.debug("Factory timezone test message")
        assert logger.name == "factory_tz_test"
    
    def test_invalid_timezone_handling(self):
        """Test handling of invalid timezone names."""
        # Should handle invalid timezone gracefully
        with pytest.raises(Exception):  # ZoneInfoNotFoundError or similar
            basic_logger(
                name="invalid_tz_test",
                timezone="Invalid/Timezone"
            )
    
    def test_timezone_offset_calculation(self):
        """Test timezone offset calculation function."""
        # Test UTC
        utc_offset = _get_timezone_offset("UTC")
        assert utc_offset == "+0000"
        
        # Test localtime
        local_offset = _get_timezone_offset("localtime")
        assert len(local_offset) == 5  # Format: ±HHMM
        assert local_offset[0] in ['+', '-']
    
    def test_timezone_function_caching(self):
        """Test that timezone functions are properly cached."""
        # First call
        func1 = get_timezone_function("UTC")
        
        # Second call should return cached result
        func2 = get_timezone_function("UTC")
        
        # Should be the same function object (cached)
        assert func1 is func2
    
    def test_timezone_function_types(self):
        """Test different timezone function types."""
        # UTC should return gmtime
        utc_func = get_timezone_function("UTC")
        import time
        assert utc_func is time.gmtime
        
        # Localtime should return localtime
        local_func = get_timezone_function("localtime")
        assert local_func is time.localtime
        
        # Named timezone should return custom function
        named_func = get_timezone_function("America/New_York")
        assert callable(named_func)
        assert named_func is not time.gmtime
        assert named_func is not time.localtime
    
    def test_stderr_timezone_functionality(self):
        """Test stderr timezone handling."""
        import io
        from contextlib import redirect_stderr
        
        # Capture stderr output
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            write_stderr("Test error message")
        
        output = stderr_capture.getvalue()
        
        # Should contain timestamp and error message
        assert "ERROR" in output
        assert "Test error message" in output
        assert "[" in output and "]" in output  # Timestamp brackets
    
    def test_stderr_timezone_caching(self):
        """Test that stderr timezone is cached."""
        # First call
        tz1 = _get_stderr_timezone()
        
        # Second call should return cached result
        tz2 = _get_stderr_timezone()
        
        # Should be the same object (cached)
        assert tz1 is tz2
    
    def test_multiple_timezone_loggers(self):
        """Test creating loggers with different timezones."""
        timezones = ["UTC", "America/New_York", "Europe/Paris", "Asia/Tokyo"]
        loggers = []
        
        for i, tz in enumerate(timezones):
            logger = basic_logger(
                name=f"tz_test_{i}",
                timezone=tz,
                level=LogLevel.INFO
            )
            loggers.append(logger)
            logger.info(f"Message from {tz}")
        
        # All loggers should be created successfully
        assert len(loggers) == len(timezones)
        
        # Each should have a unique name
        names = {logger.name for logger in loggers}
        assert len(names) == len(timezones)
    
    def test_timezone_with_factory_registry(self):
        """Test timezone functionality with factory registry."""
        from pythonLogs import get_or_create_logger
        
        # Create logger with timezone
        logger1 = get_or_create_logger(
            LoggerType.BASIC,
            name="registry_tz_test",
            timezone="Australia/Sydney"
        )
        
        # Get the same logger from registry
        logger2 = get_or_create_logger(
            LoggerType.BASIC,
            name="registry_tz_test",
            timezone="Australia/Sydney"
        )
        
        # Should be the same instance
        assert logger1 is logger2
        
        logger1.info("Registry timezone test")
    
    def test_case_insensitive_timezone_handling(self):
        """Test case insensitive timezone handling."""
        # Test localtime in different cases
        logger1 = basic_logger(name="test1", timezone="localtime")
        logger2 = basic_logger(name="test2", timezone="LOCALTIME")
        logger3 = basic_logger(name="test3", timezone="LocalTime")
        
        # All should work without errors
        logger1.info("Test message 1")
        logger2.info("Test message 2")
        logger3.info("Test message 3")
    
    def test_timezone_performance_optimization(self):
        """Test that timezone operations are optimized."""
        import time
        
        # Time creating multiple loggers with the same timezone (should use cache)
        start_time = time.time()
        
        loggers = []
        for i in range(20):
            logger = basic_logger(
                name=f"perf_test_{i}",
                timezone="America/Chicago"  # Same timezone - should use cache
            )
            loggers.append(logger)
        
        elapsed_time = time.time() - start_time
        
        # Should complete quickly due to caching
        assert elapsed_time < 0.5  # Should be very fast
        assert len(loggers) == 20
    
    def test_backward_compatibility_timezone_strings(self):
        """Test that string-based timezone parameters still work."""
        # All of these should work (backward compatibility)
        test_cases = [
            "UTC",
            "localtime", 
            "America/New_York",
            "Europe/London"
        ]
        
        for tz in test_cases:
            logger = basic_logger(
                name=f"compat_test_{tz.replace('/', '_')}",
                timezone=tz
            )
            logger.info(f"Compatibility test for {tz}")
            assert logger.name.startswith("compat_test_")
