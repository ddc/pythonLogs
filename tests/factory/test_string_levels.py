# -*- coding: utf-8 -*-
import logging
import os
import sys
import tempfile


# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pythonLogs import (
    basic_logger,
    size_rotating_logger,
    timed_rotating_logger,
    LoggerFactory, LogLevel,
    RotateWhen,
    clear_logger_registry
)


class TestStringLevels:
    """Test string level support across all logger types and methods."""
    
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Set up test fixtures before each test method."""
        # Clear any existing loggers
        clear_logger_registry()
        
        # Create temporary directory for log files using context manager
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            self.log_file = "string_test.log"
            yield
        
        # Clear registry after each test
        clear_logger_registry()
    
    def test_basic_logger_string_levels(self):
        """Test BasicLog with string levels."""
        test_cases = [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
            # Test case-insensitive
            ("DEBUG", logging.DEBUG),
            ("Info", logging.INFO),
            ("WARNING", logging.WARNING),
            ("Error", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]
        
        for level_str, expected_level in test_cases:
            logger = basic_logger(
                name=f"test_basic_{level_str}",
                level=level_str
            )
            assert logger.level == expected_level
            assert isinstance(logger, logging.Logger)
    
    def test_size_rotating_logger_string_levels(self):
        """Test SizeRotatingLog with string levels."""
        test_cases = [
            ("debug", logging.DEBUG),
            ("info", logging.INFO), 
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ]
        
        for level_str, expected_level in test_cases:
            logger = size_rotating_logger(
                name=f"test_size_{level_str}",
                level=level_str,
                directory=self.temp_dir,
                filenames=[f"{level_str}.log"],
                maxmbytes=1
            )
            assert logger.level == expected_level
            assert isinstance(logger, logging.Logger)
    
    def test_timed_rotating_logger_string_levels(self):
        """Test TimedRotatingLog with string levels."""
        test_cases = [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING), 
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ]
        
        for level_str, expected_level in test_cases:
            logger = timed_rotating_logger(
                name=f"test_timed_{level_str}",
                level=level_str,
                directory=self.temp_dir,
                filenames=[f"{level_str}.log"],
                when=RotateWhen.HOURLY
            )
            assert logger.level == expected_level
            assert isinstance(logger, logging.Logger)
    
    def test_factory_create_logger_string_levels(self):
        """Test LoggerFactory.create_logger with string levels."""
        test_cases = [
            ("basic", "debug", logging.DEBUG),
            ("size_rotating", "info", logging.INFO),
            ("timed_rotating", "warning", logging.WARNING),
        ]
        
        for logger_type_str, level_str, expected_level in test_cases:
            logger = LoggerFactory.create_logger(
                logger_type_str,
                name=f"test_factory_{logger_type_str}_{level_str}",
                level=level_str,
                directory=self.temp_dir if logger_type_str != "basic" else None,
                filenames=[f"{level_str}.log"] if logger_type_str != "basic" else None,
                maxmbytes=1 if logger_type_str == "size_rotating" else None,
                when=RotateWhen.HOURLY if logger_type_str == "timed_rotating" else None
            )
            assert logger.level == expected_level
            assert isinstance(logger, logging.Logger)
    
    def test_mixed_enum_and_string_usage(self):
        """Test mixing enum and string usage in the same application."""
        # Create logger with enum
        logger_enum = basic_logger(
            name="enum_logger",
            level=LogLevel.DEBUG
        )
        
        # Create logger with string
        logger_string = basic_logger(
            name="string_logger", 
            level="debug"
        )
        
        # Both should have the same level
        assert logger_enum.level == logger_string.level == logging.DEBUG
        
        # Both should be proper logger instances
        assert isinstance(logger_enum, logging.Logger)
        assert isinstance(logger_string, logging.Logger)
    
    def test_string_level_aliases(self):
        """Test string level aliases (warn, crit)."""
        # Test WARN alias for WARNING
        logger_warn = basic_logger(name="warn_test", level="warn")
        logger_warning = basic_logger(name="warning_test", level="warning")
        assert logger_warn.level == logger_warning.level == logging.WARNING
        
        # Test CRIT alias for CRITICAL  
        logger_crit = basic_logger(name="crit_test", level="crit")
        logger_critical = basic_logger(name="critical_test", level="critical")
        assert logger_crit.level == logger_critical.level == logging.CRITICAL
    
    def test_invalid_string_level_fallback(self):
        """Test that invalid string levels fall back to INFO."""
        invalid_levels = ["invalid", "trace", "verbose", "123", ""]
        
        for invalid_level in invalid_levels:
            logger = basic_logger(
                name=f"invalid_{invalid_level or 'empty'}",
                level=invalid_level
            )
            # Should fall back to INFO level
            assert logger.level == logging.INFO
    
    def test_string_levels_with_context_managers(self):
        """Test string levels work with context managers."""
        from pythonLogs import BasicLog, SizeRotatingLog
        
        # Test BasicLog context manager with string level
        with BasicLog(name="context_basic", level="warning") as logger:
            assert logger.level == logging.WARNING
            logger.warning("Test warning message")
        
        # Test SizeRotatingLog context manager with string level
        with SizeRotatingLog(
            name="context_size",
            level="error",
            directory=self.temp_dir,
            filenames=["context.log"],
            maxmbytes=1
        ) as logger:
            assert logger.level == logging.ERROR
            logger.error("Test error message")
    
    def test_factory_registry_with_string_levels(self):
        """Test factory registry works with string levels."""
        from pythonLogs import get_or_create_logger
        
        # Create logger with string level
        logger1 = get_or_create_logger("basic", name="registry_test", level="info")
        assert logger1.level == logging.INFO
        
        # Get the same logger again (should be cached)
        logger2 = get_or_create_logger("basic", name="registry_test", level="debug")
        
        # Should be the same instance (registry hit)
        assert logger1 is logger2
        # Level should remain as first created (INFO)
        assert logger2.level == logging.INFO
    
    def test_comprehensive_string_level_functionality(self):
        """Test comprehensive functionality with string levels."""
        # Create loggers of each type with string levels
        basic = basic_logger(name="comp_basic", level="debug")
        
        size_rotating = size_rotating_logger(
            name="comp_size",
            level="info",
            directory=self.temp_dir,
            filenames=["comp_size.log"],
            maxmbytes=1,
            streamhandler=True
        )
        
        timed_rotating = timed_rotating_logger(
            name="comp_timed",
            level="warning",
            directory=self.temp_dir,
            filenames=["comp_timed.log"],
            when="midnight",
            streamhandler=True
        )
        
        # Test logging functionality
        basic.debug("Debug message")
        basic.info("Info message")
        
        size_rotating.info("Size rotating info")
        size_rotating.warning("Size rotating warning")
        
        timed_rotating.warning("Timed rotating warning") 
        timed_rotating.error("Timed rotating error")
        
        # Verify levels are set correctly
        assert basic.level == logging.DEBUG
        assert size_rotating.level == logging.INFO
        assert timed_rotating.level == logging.WARNING
        
        # Verify all are proper logger instances
        assert all(isinstance(logger, logging.Logger) 
                  for logger in [basic, size_rotating, timed_rotating])


if __name__ == "__main__":
    pytest.main([__file__])
