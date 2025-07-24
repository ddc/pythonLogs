#!/usr/bin/env python3
"""Practical examples and integration tests for the Logger Factory Pattern."""
import os
import sys
import tempfile
from pathlib import Path
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import (
    LoggerFactory,
    LoggerType,
    LogLevel,
    RotateWhen,
    create_logger,
    get_or_create_logger,
    basic_logger,
    size_rotating_logger,
    timed_rotating_logger,
    clear_logger_registry,
)


class TestFactoryExamples:
    """Integration tests demonstrating factory pattern usage."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()
    
    def test_basic_console_logging(self):
        """Test basic console logging example."""
        logger = LoggerFactory.create_logger(
            LoggerType.BASIC,
            name="console_app",
            level=LogLevel.INFO
        )
        
        # Test logging (won't fail, just exercises the code)
        logger.info("Application started")
        logger.warning("This is a warning")
        logger.debug("This debug message should be filtered out")
        
        assert logger.name == "console_app"
        assert logger.level == 20  # INFO level
    
    def test_file_based_size_rotating_logger(self):
        """Test file-based size rotating logger example."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = size_rotating_logger(
                name="app_logger",
                directory=temp_dir,
                filenames=["app.log", "debug.log"],
                maxmbytes=1,  # Small size for testing
                daystokeep=7,
                level=LogLevel.DEBUG,
                streamhandler=False  # No console output for test
            )
            
            # Generate some log messages
            for i in range(10):
                logger.info(f"Log message {i}")
                logger.error(f"Error message {i}")
            
            # Verify log files were created
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) >= 1  # At least one log file should exist
    
    def test_time_based_rotating_logger(self):
        """Test time-based rotating logger example."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = timed_rotating_logger(
                name="scheduled_app",
                directory=temp_dir,
                filenames=["scheduled.log"],
                when=RotateWhen.DAILY,
                level=LogLevel.WARNING,
                streamhandler=False
            )
            
            logger.warning("Scheduled task started")
            logger.error("Task encountered an error")
            logger.critical("Critical system failure")
            
            # Verify log file was created
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) >= 1
    
    def test_production_like_multi_logger_setup(self):
        """Test production-like setup with multiple loggers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Application logger
            app_logger = LoggerFactory.create_logger(
                LoggerType.SIZE_ROTATING,
                name="production_app",
                directory=temp_dir,
                filenames=["app.log"],
                maxmbytes=50,
                daystokeep=30,
                level=LogLevel.INFO,
                streamhandler=False,
                showlocation=True,
                timezone="UTC"
            )
            
            # Error logger
            error_logger = LoggerFactory.create_logger(
                LoggerType.SIZE_ROTATING,
                name="production_errors",
                directory=temp_dir,
                filenames=["errors.log"],
                maxmbytes=10,
                daystokeep=90,
                level=LogLevel.ERROR,
                streamhandler=False
            )
            
            # Audit logger
            audit_logger = LoggerFactory.create_logger(
                LoggerType.TIMED_ROTATING,
                name="audit_log",
                directory=temp_dir,
                filenames=["audit.log"],
                when=RotateWhen.MIDNIGHT,
                level=LogLevel.INFO,
                streamhandler=False
            )
            
            # Test logging to different loggers
            app_logger.info("Application started successfully")
            error_logger.error("Database connection failed")
            audit_logger.info("User login: admin")
            
            # Verify all loggers are different instances
            assert app_logger.name != error_logger.name != audit_logger.name
            
            # Verify log files were created
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) >= 3
    
    def test_logger_registry_in_production_scenario(self):
        """Test logger registry usage in production scenario."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # First module gets logger
            module1_logger = get_or_create_logger(
                LoggerType.SIZE_ROTATING,
                name="shared_app_logger",
                directory=temp_dir,
                level=LogLevel.INFO
            )
            
            # The Second module gets the same logger (cached)
            module2_logger = get_or_create_logger(
                LoggerType.SIZE_ROTATING,
                name="shared_app_logger",
                directory=temp_dir  # Must provide same params
            )
            
            # Should be the same instance
            assert module1_logger is module2_logger
            
            # Both modules can log
            module1_logger.info("Message from module 1")
            module2_logger.info("Message from module 2")
    
    def test_mixed_enum_string_usage_example(self):
        """Test realistic mixed usage of enums and strings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configuration from environment (strings)
            config_level = "INFO"
            config_when = "midnight"
            
            # Create logger with mix of config and enums
            logger = timed_rotating_logger(
                name="config_driven_app",
                directory=temp_dir,
                level=config_level,          # String from config
                when=RotateWhen.MIDNIGHT,    # Enum for type safety
                streamhandler=True
            )
            
            logger.info("Configuration loaded successfully")
            assert logger.name == "config_driven_app"
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        # Invalid logger type
        with pytest.raises(ValueError, match="Invalid logger type"):
            create_logger("nonexistent_type", name="error_test")
        
        # Invalid directory (should raise PermissionError when trying to create)
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_parent = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_parent, mode=0o555)  # Read-only parent
            try:
                invalid_dir = os.path.join(readonly_parent, "invalid")
                with pytest.raises(PermissionError):
                    size_rotating_logger(
                        name="permission_test",
                        directory=invalid_dir
                    )
            finally:
                os.chmod(readonly_parent, 0o755)  # Restore permissions for cleanup
    
    def test_logger_customization_example(self):
        """Test logger with extensive customization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = LoggerFactory.create_logger(
                LoggerType.TIMED_ROTATING,
                name="custom_app",
                directory=temp_dir,
                filenames=["custom.log", "custom_debug.log"],
                level=LogLevel.DEBUG,
                when=RotateWhen.HOURLY,
                daystokeep=14,
                encoding="utf-8",
                datefmt="%Y-%m-%d %H:%M:%S",
                timezone="UTC",
                streamhandler=True,
                showlocation=True,
                rotateatutc=True
            )
            
            # Test all log levels
            logger.debug("Debug information")
            logger.info("Informational message")
            logger.warning("Warning message")
            logger.error("Error occurred")
            logger.critical("Critical failure")
            
            assert logger.name == "custom_app"
            assert logger.level == 10  # DEBUG level
    
    def test_convenience_functions_examples(self):
        """Test all convenience functions with realistic scenarios."""
        # Basic logger for console output
        console_logger = basic_logger(
            name="console",
            level=LogLevel.WARNING
        )
        console_logger.warning("Console warning message")
        
        # Size rotating for application logs
        with tempfile.TemporaryDirectory() as temp_dir:
            app_logger = size_rotating_logger(
                name="application",
                directory=temp_dir,
                maxmbytes=5,
                level=LogLevel.INFO
            )
            app_logger.info("Application log message")
            
            # Timed rotating for audit logs
            audit_logger = timed_rotating_logger(
                name="audit",
                directory=temp_dir,
                when=RotateWhen.DAILY,
                level=LogLevel.INFO
            )
            audit_logger.info("Audit log message")
        
        # Verify all loggers have different names
        names = {console_logger.name, app_logger.name, audit_logger.name}
        assert len(names) == 3  # All unique names
