#!/usr/bin/env python3
"""Test enum usage with the factory pattern."""
import os
import sys
import tempfile
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import (
    LoggerFactory,
    LoggerType,
    LogLevel,
    RotateWhen,
    create_logger,
    basic_logger,
    timed_rotating_logger,
    clear_logger_registry,
)


class TestEnumUsage:
    """Test cases for enum usage with factory pattern."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()
    
    def test_log_level_enum_usage(self):
        """Test LogLevel enum usage."""
        logger = LoggerFactory.create_logger(
            LoggerType.BASIC,
            name="enum_test",
            level=LogLevel.DEBUG  # Using enum instead of string
        )
        assert logger.name == "enum_test"
        assert logger.level == 10  # DEBUG level
    
    def test_rotate_when_enum_usage(self):
        """Test RotateWhen enum usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = timed_rotating_logger(
                name="rotate_test",
                directory=temp_dir,
                level=LogLevel.INFO,      # LogLevel enum
                when=RotateWhen.MIDNIGHT  # RotateWhen enum
            )
            assert logger.name == "rotate_test"
    
    def test_mixed_enum_and_string_usage(self):
        """Test mixed enum and string usage."""
        logger = create_logger(
            "basic",               # String logger type
            name="mixed_test",
            level=LogLevel.WARNING # Enum level
        )
        assert logger.name == "mixed_test"
        assert logger.level == 30  # WARNING level
    
    def test_all_log_level_enum_values(self):
        """Test all LogLevel enum values are accessible and work."""
        levels = [
            (LogLevel.DEBUG, 10),
            (LogLevel.INFO, 20),
            (LogLevel.WARNING, 30),
            (LogLevel.ERROR, 40),
            (LogLevel.CRITICAL, 50)
        ]
        
        for enum_level, expected_int in levels:
            logger = basic_logger(
                name=f"test_{enum_level.value.lower()}",
                level=enum_level
            )
            assert logger.level == expected_int
    
    def test_all_rotate_when_enum_values(self):
        """Test all RotateWhen enum values are accessible."""
        when_options = [
            RotateWhen.MIDNIGHT,
            RotateWhen.HOURLY,
            RotateWhen.DAILY,
            RotateWhen.MONDAY,
            RotateWhen.TUESDAY,
            RotateWhen.WEDNESDAY,
            RotateWhen.THURSDAY,
            RotateWhen.FRIDAY,
            RotateWhen.SATURDAY,
            RotateWhen.SUNDAY
        ]
        
        # Just verify they're accessible and have expected values
        expected_values = ['midnight', 'H', 'D', 'W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6']
        actual_values = [when.value for when in when_options]
        assert actual_values == expected_values
    
    def test_enum_string_conversion(self):
        """Test that enums are properly converted to strings internally."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create logger with enums
            logger = LoggerFactory.create_logger(
                LoggerType.TIMED_ROTATING,
                name="conversion_test",
                directory=temp_dir,
                level=LogLevel.ERROR,
                when=RotateWhen.DAILY
            )
            
            # Verify logger was created successfully
            assert logger.name == "conversion_test"
            assert logger.level == 40  # ERROR level
    
    def test_backward_compatibility_with_strings(self):
        """Test that string values still work alongside enums."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mix of enums and strings
            logger = timed_rotating_logger(
                name="compat_test",
                directory=temp_dir,
                level="INFO",                # String level
                when=RotateWhen.MIDNIGHT     # Enum when
            )
            
            assert logger.name == "compat_test"
            assert logger.level == 20  # INFO level
    
    def test_logger_type_enum_values(self):
        """Test LoggerType enum values."""
        types = [LoggerType.BASIC, LoggerType.SIZE_ROTATING, LoggerType.TIMED_ROTATING]
        expected = ["basic", "size_rotating", "timed_rotating"]
        actual = [t.value for t in types]
        assert actual == expected
    
    def test_case_insensitive_string_logger_types(self):
        """Test that string logger types are case insensitive."""
        test_cases = ["BASIC", "Basic", "basic", "BASIC"]
        
        for case in test_cases:
            logger = create_logger(case, name=f"case_test_{case}")
            assert logger.name == f"case_test_{case}"
    
    def test_invalid_enum_conversion(self):
        """Test error handling for invalid enum-like strings."""
        with pytest.raises(ValueError, match="Invalid logger type"):
            create_logger("invalid_enum_type", name="error_test")
