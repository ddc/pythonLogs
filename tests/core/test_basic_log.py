import logging
import os
import sys
import pytest


# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import BasicLog, LogLevel, clear_logger_registry


class TestBasicLog:
    """Test BasicLog functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear any existing loggers
        clear_logger_registry()

    def teardown_method(self):
        """Clean up after each test method."""
        # Clear registry after each test
        clear_logger_registry()

    def test_basic_log_initialization(self):
        """Test BasicLog initialization with default parameters."""
        basic_log = BasicLog()
        assert hasattr(basic_log, 'level')
        assert hasattr(basic_log, 'appname')
        assert hasattr(basic_log, 'encoding')
        assert hasattr(basic_log, 'datefmt')
        assert hasattr(basic_log, 'timezone')
        assert hasattr(basic_log, 'showlocation')
        assert basic_log.logger is None

    def test_basic_log_initialization_with_params(self):
        """Test BasicLog initialization with custom parameters."""
        basic_log = BasicLog(
            level=LogLevel.DEBUG.value,
            name="test_app",
            encoding="utf-8",
            datefmt="%Y-%m-%d %H:%M:%S",
            timezone="UTC",
            showlocation=True,
        )
        assert basic_log.level == logging.DEBUG
        assert basic_log.appname == "test_app"
        assert basic_log.encoding == "utf-8"
        assert basic_log.datefmt == "%Y-%m-%d %H:%M:%S"
        assert basic_log.timezone == "UTC"
        assert basic_log.showlocation is True

    def test_basic_log_init_method(self):
        """Test BasicLog init method creates logger."""
        basic_log = BasicLog(name="test_init", level=LogLevel.INFO.value)
        logger = basic_log.init()

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_init"
        assert logger.level == logging.INFO
        assert hasattr(basic_log, 'logger')
        assert basic_log.logger is logger

    def test_basic_log_logger_functionality(self):
        """Test that BasicLog logger can log messages."""
        basic_log = BasicLog(name="test_logging", level=LogLevel.INFO.value)
        logger = basic_log.init()

        # Test logging at different levels
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # Should not raise any exceptions

    def test_basic_log_level_filtering(self):
        """Test that BasicLog respects log level filtering."""
        basic_log = BasicLog(name="test_level", level=LogLevel.WARNING.value)
        logger = basic_log.init()

        assert logger.level == logging.WARNING
        assert logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)
        assert not logger.isEnabledFor(logging.INFO)
        assert not logger.isEnabledFor(logging.DEBUG)

    def test_basic_log_cleanup_static_method(self):
        """Test BasicLog static cleanup method."""
        basic_log = BasicLog(name="test_cleanup", level=LogLevel.INFO.value)
        logger = basic_log.init()

        # Add a handler
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        assert len(logger.handlers) > 0

        # Clean up using static method
        BasicLog.cleanup_logger(logger)
        assert len(logger.handlers) == 0

    def test_basic_log_instance_cleanup_method(self):
        """Test BasicLog instance cleanup method."""
        basic_log = BasicLog(name="test_instance_cleanup", level=LogLevel.INFO.value)
        logger = basic_log.init()

        # Add a handler
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        assert len(logger.handlers) > 0

        # Clean up using instance method
        basic_log._cleanup_logger(logger)
        assert len(logger.handlers) == 0

    def test_basic_log_thread_safety(self):
        """Test BasicLog thread safety with concurrent operations."""
        import threading
        import time

        basic_log = BasicLog(name="test_thread_safety", level=LogLevel.INFO.value)
        logger = basic_log.init()
        results = []

        def log_messages(thread_id):
            try:
                for i in range(10):
                    logger.info(f"Thread {thread_id} message {i}")
                    time.sleep(0.001)  # Small delay
                results.append(f"thread_{thread_id}_success")
            except Exception as e:
                results.append(f"thread_{thread_id}_error_{e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_messages, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All threads should complete successfully
        assert len(results) == 5
        assert all("success" in result for result in results)

    def test_basic_log_different_log_levels(self):
        """Test BasicLog with different log levels."""
        log_levels = [
            (LogLevel.DEBUG.value, logging.DEBUG),
            (LogLevel.INFO.value, logging.INFO),
            (LogLevel.WARNING.value, logging.WARNING),
            (LogLevel.ERROR.value, logging.ERROR),
            (LogLevel.CRITICAL.value, logging.CRITICAL),
        ]

        for level_str, level_int in log_levels:
            basic_log = BasicLog(name=f"test_{level_str}", level=level_str)
            logger = basic_log.init()
            assert logger.level == level_int

            # Clean up
            BasicLog.cleanup_logger(logger)

    def test_basic_log_multiple_instances(self):
        """Test creating multiple BasicLog instances."""
        loggers = []

        for i in range(5):
            basic_log = BasicLog(name=f"test_multi_{i}", level=LogLevel.INFO.value)
            logger = basic_log.init()
            loggers.append((basic_log, logger))

            assert logger.name == f"test_multi_{i}"
            assert logger.level == logging.INFO

        # Clean up all loggers
        for basic_log, logger in loggers:
            BasicLog.cleanup_logger(logger)
            assert len(logger.handlers) == 0


if __name__ == "__main__":
    pytest.main([__file__])
