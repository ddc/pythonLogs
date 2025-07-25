# -*- coding: utf-8 -*-
import logging
import os
import sys
import tempfile


# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pythonLogs import (
    BasicLog,
    SizeRotatingLog,
    TimedRotatingLog,
    LogLevel,
    RotateWhen,
    clear_logger_registry,
    LoggerFactory,
)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
class TestContextManagers:
    """Test context manager functionality for resource management."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Set up test fixtures before each test method."""
        # Clear any existing loggers
        clear_logger_registry()

        # Create temporary directory for log files using context manager
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            self.log_file = "test.log"
            yield
        
        # Clear registry after each test
        clear_logger_registry()

    def test_basic_log_context_manager(self):
        """Test BasicLog as context manager."""
        logger_name = "test_basic_context"

        with BasicLog(name=logger_name, level=LogLevel.INFO.value) as logger:
            assert isinstance(logger, logging.Logger)
            assert logger.name == logger_name
            assert logger.level == logging.INFO

            # Test logging
            logger.info("Test message in context")

        # After context exit, handlers should be cleaned up
        assert len(logger.handlers) == 0

    def test_size_rotating_context_manager(self):
        """Test SizeRotatingLog as context manager."""
        logger_name = "test_size_context"

        with SizeRotatingLog(
            name=logger_name,
            level=LogLevel.DEBUG.value,
            directory=self.temp_dir,
            filenames=[self.log_file],
            maxmbytes=1,
            daystokeep=2
        ) as logger:
            assert isinstance(logger, logging.Logger)
            assert logger.name == logger_name
            assert logger.level == logging.DEBUG

            # Should have file handlers
            file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
            assert len(file_handlers) > 0

            # Test logging
            logger.debug("Test debug message")
            logger.info("Test info message")

        # After context exit, handlers should be cleaned up
        assert len(logger.handlers) == 0

    def test_timed_rotating_context_manager(self):
        """Test TimedRotatingLog as context manager."""
        logger_name = "test_timed_context"

        with TimedRotatingLog(
            name=logger_name,
            level=LogLevel.WARNING.value,
            directory=self.temp_dir,
            filenames=[self.log_file],
            when=RotateWhen.HOURLY.value,
            daystokeep=3
        ) as logger:
            assert isinstance(logger, logging.Logger)
            assert logger.name == logger_name
            assert logger.level == logging.WARNING

            # Should have file handlers
            file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
            assert len(file_handlers) > 0

            # Test logging
            logger.warning("Test warning message")
            logger.error("Test error message")

        # After context exit, handlers should be cleaned up
        assert len(logger.handlers) == 0

    def test_context_manager_exception_handling(self):
        """Test context manager cleanup on exceptions."""
        logger_name = "test_exception_context"
        logger_ref = None

        try:
            with BasicLog(name=logger_name, level=LogLevel.ERROR.value) as logger:
                logger_ref = logger
                logger.error("Test before exception")
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected exception

        # Even with exception, handlers should be cleaned up
        assert logger_ref is not None
        assert len(logger_ref.handlers) == 0

    def test_context_manager_without_init(self):
        """Test context manager calls init() if not already called."""
        logger_instance = BasicLog(name="test_no_init", level=LogLevel.INFO.value)

        # Don't call init() manually - logger should be None initially
        assert logger_instance.logger is None

        with logger_instance as logger:
            # Context manager should have called init()
            assert hasattr(logger_instance, 'logger')
            assert logger_instance.logger is not None
            assert isinstance(logger, logging.Logger)
            logger.info("Test message")

        # Cleanup should still work
        assert len(logger.handlers) == 0

    def test_context_manager_with_existing_init(self):
        """Test context manager with logger already initialized."""
        logger_instance = BasicLog(name="test_existing_init", level=LogLevel.INFO.value)

        # Call init() manually first
        manual_logger = logger_instance.init()
        assert hasattr(logger_instance, 'logger')

        with logger_instance as context_logger:
            # Should return the same logger
            assert context_logger is manual_logger
            context_logger.info("Test message")

        # Cleanup should still work
        assert len(manual_logger.handlers) == 0

    def test_multiple_file_handlers_cleanup(self):
        """Test cleanup of multiple file handlers."""
        logger_name = "test_multi_files"
        multiple_files = ["test1.log", "test2.log", "test3.log"]

        with SizeRotatingLog(
            name=logger_name, directory=self.temp_dir, filenames=multiple_files, maxmbytes=1
        ) as logger:
            # Should have multiple file handlers
            file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
            assert len(file_handlers) == len(multiple_files)

            logger.info("Test message to multiple files")

        # All handlers should be cleaned up
        assert len(logger.handlers) == 0

    def test_stream_handler_cleanup(self):
        """Test cleanup of stream handlers."""
        logger_name = "test_stream_cleanup"

        with SizeRotatingLog(
            name=logger_name, directory=self.temp_dir, filenames=[self.log_file], streamhandler=True
            # Enable stream handler
        ) as logger:
            # Should have both file and stream handlers
            stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]

            assert len(stream_handlers) > 0
            assert len(file_handlers) > 0

            logger.info("Test message to file and console")

        # All handlers should be cleaned up
        assert len(logger.handlers) == 0

    def test_nested_context_managers(self):
        """Test nested context managers don't interfere."""
        with BasicLog(name="outer_logger", level=LogLevel.INFO.value) as outer_logger:
            outer_logger.info("Outer logger message")

            with BasicLog(name="inner_logger", level=LogLevel.DEBUG.value) as inner_logger:
                inner_logger.debug("Inner logger message")
                assert outer_logger.name != inner_logger.name

            # Inner logger should be cleaned up
            assert len(inner_logger.handlers) == 0

            # Outer logger should still work
            outer_logger.info("Outer logger still working")

        # Both loggers should be cleaned up
        assert len(outer_logger.handlers) == 0
        assert len(inner_logger.handlers) == 0

    def test_shutdown_logger(self):
        """Test shutdown_logger functionality."""
        logger_name = "test_shutdown_logger"
        
        # Create a logger using factory (with registry caching)
        logger = LoggerFactory.get_or_create_logger("basic", name=logger_name, level=LogLevel.INFO.value)
        
        # Verify logger is in registry
        assert logger_name in LoggerFactory._logger_registry
        
        # Add some handlers
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        
        # Verify handler is attached
        assert len(logger.handlers) > 0
        
        # Shutdown the specific logger
        LoggerFactory.shutdown_logger(logger_name)
        
        # Verify logger handlers are cleaned up
        assert len(logger.handlers) == 0
        
        # Verify logger is removed from registry
        assert logger_name not in LoggerFactory._logger_registry


if __name__ == "__main__":
    pytest.main([__file__])
