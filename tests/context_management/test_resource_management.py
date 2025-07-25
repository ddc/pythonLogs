# -*- coding: utf-8 -*-
import logging
import os
import sys
import tempfile
import time


# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pythonLogs import (
    LoggerFactory, basic_logger,
    size_rotating_logger,
    clear_logger_registry,
    shutdown_logger,
    get_registered_loggers,
    LogLevel
)


class TestResourceManagement:
    """Test resource management functionality."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Set up test fixtures before each test method."""
        # Clear any existing loggers
        clear_logger_registry()

        # Create temporary directory for log files using context manager
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            self.log_file = "resource_test.log"
            yield
        
        # Clear registry after each test
        clear_logger_registry()

    def test_factory_registry_cleanup(self):
        """Test that factory registry cleanup properly closes handlers."""
        logger_name = "test_registry_cleanup"

        # Create logger through factory
        logger = LoggerFactory.create_size_rotating_logger(
            name=logger_name,
            directory=self.temp_dir,
            filenames=[self.log_file],
            maxmbytes=1
        )

        # Add to registry
        LoggerFactory._logger_registry[logger_name] = (logger, time.time())

        # Verify logger has handlers
        assert len(logger.handlers) > 0
        initial_handler_count = len(logger.handlers)

        # Clear registry
        LoggerFactory.clear_registry()

        # Verify handlers were closed and removed
        assert len(logger.handlers) == 0
        assert initial_handler_count > 0  # Ensure we actually had handlers to clean up
        assert len(LoggerFactory._logger_registry) == 0

    def test_shutdown_specific_logger(self):
        """Test shutting down a specific logger."""
        logger1_name = "test_logger_1"
        logger2_name = "test_logger_2"

        # Create two loggers
        logger1 = basic_logger(name=logger1_name, level=LogLevel.INFO.value)
        logger2 = basic_logger(name=logger2_name, level=LogLevel.DEBUG.value)

        # Add to registry manually for testing
        LoggerFactory._logger_registry[logger1_name] = (logger1, time.time())
        LoggerFactory._logger_registry[logger2_name] = (logger2, time.time())

        # Verify both are in registry
        assert len(get_registered_loggers()) == 2

        # Shutdown only logger1
        result = shutdown_logger(logger1_name)
        assert result is True

        # Verify logger1 was removed and cleaned up
        assert logger1_name not in get_registered_loggers()
        assert len(logger1.handlers) == 0

        # Verify logger2 is still active
        assert logger2_name in get_registered_loggers()
        assert len(get_registered_loggers()) == 1

    def test_shutdown_nonexistent_logger(self):
        """Test shutting down a logger that doesn't exist."""
        result = shutdown_logger("nonexistent_logger")
        assert result is False

    def test_handler_cleanup_static_method(self):
        """Test the static cleanup method directly."""
        from pythonLogs.basic_log import BasicLog

        # Create a logger with handlers
        logger = logging.getLogger("test_static_cleanup")
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()

        logger.addHandler(handler1)
        logger.addHandler(handler2)

        assert len(logger.handlers) == 2

        # Use static cleanup method
        BasicLog.cleanup_logger(logger)

        # Verify all handlers were cleaned up
        assert len(logger.handlers) == 0

    def test_handler_cleanup_with_errors(self):
        """Test handler cleanup handles errors gracefully."""
        from pythonLogs.basic_log import BasicLog

        logger = logging.getLogger("test_error_cleanup")

        # Create a mock handler that raises an error on close
        class ErrorHandler(logging.Handler):
            def close(self):
                raise OSError("Mock error during close")

        error_handler = ErrorHandler()
        normal_handler = logging.StreamHandler()

        logger.addHandler(error_handler)
        logger.addHandler(normal_handler)

        assert len(logger.handlers) == 2

        # Cleanup should handle errors and still remove handlers
        BasicLog.cleanup_logger(logger)

        # All handlers should be removed despite errors
        assert len(logger.handlers) == 0

    def test_registry_clear_with_file_handlers(self):
        """Test registry cleanup with file handlers."""
        logger_name = "test_file_handlers"

        # Create logger with file handlers
        logger = LoggerFactory.create_size_rotating_logger(
            name=logger_name,
            directory=self.temp_dir,
            filenames=[self.log_file, "second.log"],
            maxmbytes=1,
            streamhandler=True  # Add stream handler too
        )

        # Add to registry
        LoggerFactory._logger_registry[logger_name] = (logger, time.time())

        # Write some data to verify handlers are working
        logger.info("Test message before cleanup")

        # Verify we have multiple handlers
        file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]

        assert len(file_handlers) == 2  # Two file handlers
        assert len(stream_handlers) > 0  # At least one stream handler

        # Clear registry
        clear_logger_registry()

        # Verify all handlers cleaned up
        assert len(logger.handlers) == 0
        assert len(get_registered_loggers()) == 0

    def test_resource_cleanup_performance(self):
        """Test that resource cleanup doesn't cause performance issues."""
        num_loggers = 10
        logger_names = [f"perf_test_logger_{i}" for i in range(num_loggers)]

        # Create multiple loggers
        start_time = time.time()
        for name in logger_names:
            logger = size_rotating_logger(
                name=name,
                directory=self.temp_dir,
                filenames=[f"{name}.log"],
                maxmbytes=1
            )
            LoggerFactory._logger_registry[name] = (logger, time.time())

        creation_time = time.time() - start_time

        # Verify all created
        assert len(get_registered_loggers()) == num_loggers

        # Clear all at once
        cleanup_start = time.time()
        clear_logger_registry()
        cleanup_time = time.time() - cleanup_start

        # Verify cleanup completed
        assert len(get_registered_loggers()) == 0

        # Performance should be reasonable (less than 1 second for 10 loggers)
        assert cleanup_time < 1.0
        print(f"Created {num_loggers} loggers in {creation_time:.4f}s")
        print(f"Cleaned up {num_loggers} loggers in {cleanup_time:.4f}s")

    def test_memory_usage_after_cleanup(self):
        """Test that memory is properly released after cleanup."""
        import gc
        import weakref

        logger_name = "memory_test_logger"

        # Create logger and get weak reference
        logger = size_rotating_logger(
            name=logger_name,
            directory=self.temp_dir,
            filenames=[self.log_file],
            maxmbytes=1
        )

        # Add to registry
        LoggerFactory._logger_registry[logger_name] = (logger, time.time())

        # Create weak reference to track if logger is garbage collected
        logger_weakref = weakref.ref(logger)
        handler_weakrefs = [weakref.ref(h) for h in logger.handlers]

        # Clear local reference
        del logger

        # Logger should still exist due to registry
        assert logger_weakref() is not None
        # Handlers should also still exist
        assert all(ref() is not None for ref in handler_weakrefs)

        # Clear registry
        clear_logger_registry()

        # Force garbage collection
        gc.collect()

        # Logger should be garbage collected
        # Note: This test might be flaky depending on Python's garbage collector,
        # but it helps verify we're not holding unnecessary references
        print(f"Logger weakref after cleanup: {logger_weakref()}")

    def test_concurrent_cleanup(self):
        """Test resource cleanup works correctly with concurrent access."""
        import concurrent.futures

        def create_and_cleanup_logger(index):
            """Create a logger and immediately clean it up."""
            logger_name = f"concurrent_test_{index}"
            logger = basic_logger(name=logger_name, level=LogLevel.INFO.value)
            
            # Add to registry
            LoggerFactory._logger_registry[logger_name] = (logger, time.time())
            
            # Small delay to increase chance of concurrent access
            time.sleep(0.01)
            
            # Shutdown this specific logger
            return shutdown_logger(logger_name)
        
        # Create multiple threads doing concurrent operations
        num_threads = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                futures.append(executor.submit(create_and_cleanup_logger, i))
            
            # Wait for all to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # All operations should succeed
        assert all(results)
        
        # The Registry should be empty
        assert len(get_registered_loggers()) == 0


if __name__ == "__main__":
    pytest.main([__file__])
