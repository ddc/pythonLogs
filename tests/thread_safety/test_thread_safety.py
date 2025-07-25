#!/usr/bin/env python3
"""Test thread safety of the pythonLogs library."""
import concurrent.futures
import os
import sys
import tempfile
import threading
import time
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import (
    LoggerFactory,
    LoggerType,
    LogLevel,
    clear_logger_registry,
    BasicLog,
    SizeRotatingLog,
    TimedRotatingLog,
)


class TestThreadSafety:
    """Test cases for thread safety of logger creation and management."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()

    def teardown_method(self):
        """Clear the registry after each test."""
        clear_logger_registry()

    def test_concurrent_logger_factory_creation(self):
        """Test concurrent logger creation via factory doesn't create duplicates."""
        results = []
        num_threads = 10
        logger_name = "concurrent_test_logger"

        def create_logger_worker():
            """Worker function to create logger."""
            _logger = LoggerFactory.get_or_create_logger(LoggerType.BASIC, name=logger_name, level=LogLevel.INFO)
            results.append(_logger)
            return _logger

        # Create multiple threads that try to create the same logger
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_logger_worker) for _ in range(num_threads)]
            loggers = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All loggers should be the exact same instance (cached)
        first_logger = loggers[0]
        for logger in loggers[1:]:
            assert logger is first_logger, "All loggers should be the same cached instance"

        # Registry should only contain one logger
        registry = LoggerFactory.get_registered_loggers()
        assert len(registry) == 1
        assert logger_name in registry
        assert registry[logger_name] is first_logger

    def test_concurrent_registry_operations(self):
        """Test concurrent registry operations (create, shutdown, clear)."""
        num_threads = 20
        results = {'created': [], 'shutdown': [], 'errors': []}

        def mixed_operations_worker(worker_id):
            """Worker that performs mixed registry operations."""
            try:
                logger_name = f"test_logger_{worker_id}"

                # Create logger
                logger = LoggerFactory.get_or_create_logger(LoggerType.BASIC, name=logger_name, level=LogLevel.DEBUG)
                results['created'].append(logger_name)

                # Small delay to increase chance of race conditions
                time.sleep(0.01)

                # Try to shut down logger
                if LoggerFactory.shutdown_logger(logger_name):
                    results['shutdown'].append(logger_name)

            except Exception as e:
                results['errors'].append(str(e))

        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(mixed_operations_worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # No errors should occur
        assert len(results['errors']) == 0, f"Errors occurred: {results['errors']}"

        # All created loggers should be accounted for
        assert len(results['created']) == num_threads

        # Registry should be consistent
        registry = LoggerFactory.get_registered_loggers()
        # Some loggers might still be in the registry if shutdown happened after creation
        assert len(registry) <= num_threads

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file",
    )
    def test_concurrent_directory_cache_access(self):
        """Test concurrent access to directory permission cache."""
        import pythonLogs.log_utils as log_utils

        num_threads = 15
        temp_dirs = []
        errors = []

        def check_directory_worker(worker_id):
            """Worker that checks directory permissions."""
            try:
                # Create a unique temp directory for each worker using context manager
                with tempfile.TemporaryDirectory(prefix=f"test_thread_{worker_id}_") as _temp_dir:
                    temp_dirs.append(_temp_dir)

                    # Multiple calls to the same directory should be safe
                    for _ in range(3):
                        log_utils.check_directory_permissions(_temp_dir)
                        time.sleep(0.001)  # Small delay to increase race condition chance

            except Exception as e:
                errors.append(str(e))

        try:
            # Clear the directory cache first
            log_utils._checked_directories.clear()

            # Run concurrent directory checks
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(check_directory_worker, i) for i in range(num_threads)]
                for future in concurrent.futures.as_completed(futures):
                    future.result()

            # No errors should occur
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # All directories should be in cache
            assert len(log_utils._checked_directories) == num_threads

        finally:
            # Cleanup is handled automatically by TemporaryDirectory context managers
            pass

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file",
    )
    def test_concurrent_context_manager_cleanup(self):
        """Test concurrent context manager cleanup doesn't cause issues."""
        num_threads = 10
        errors = []

        def context_manager_worker(worker_id):
            """Worker that uses logger context managers."""
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Use different logger types to test all cleanup paths
                    if worker_id % 3 == 0:
                        with BasicLog(name=f"basic_{worker_id}", level="INFO") as logger:
                            logger.info(f"Basic logger message from thread {worker_id}")
                    elif worker_id % 3 == 1:
                        with SizeRotatingLog(name=f"size_{worker_id}", directory=temp_dir, level="DEBUG") as logger:
                            logger.debug(f"Size rotating message from thread {worker_id}")
                    else:
                        with TimedRotatingLog(
                            name=f"timed_{worker_id}",
                            directory=temp_dir,
                            level="WARNING",
                        ) as logger:
                            logger.warning(f"Timed rotating message from thread {worker_id}")

            except Exception as e:
                errors.append(f"Thread {worker_id}: {str(e)}")

        # Run concurrent context manager operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(context_manager_worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # No errors should occur during cleanup
        assert len(errors) == 0, f"Context manager errors: {errors}"

    def test_stress_test_factory_pattern(self):
        """Stress test the factory pattern with high concurrency."""
        num_threads = 50
        operations_per_thread = 10
        logger_names = [f"stress_logger_{i}" for i in range(5)]  # Shared logger names
        results = {'success': 0, 'errors': []}
        results_lock = threading.Lock()

        def stress_worker():
            """Worker that performs multiple factory operations."""
            try:
                for _ in range(operations_per_thread):
                    # Randomly pick a logger name to increase collision chance
                    import random

                    _logger_name = random.choice(logger_names)

                    # Create or get logger
                    logger = LoggerFactory.get_or_create_logger(
                        LoggerType.BASIC,
                        name=_logger_name,
                        level=LogLevel.INFO,
                    )

                    # Use the logger
                    logger.info(f"Stress test message from {threading.current_thread().name}")

                    # Small delay
                    time.sleep(0.001)

                with results_lock:
                    results['success'] += operations_per_thread

            except Exception as e:
                with results_lock:
                    results['errors'].append(str(e))

        # Run stress test
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(stress_worker) for _ in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify results
        expected_operations = num_threads * operations_per_thread
        assert results['success'] == expected_operations, f"Expected {expected_operations}, got {results['success']}"
        assert len(results['errors']) == 0, f"Stress test errors: {results['errors']}"

        # Registry should only have the expected number of unique loggers
        registry = LoggerFactory.get_registered_loggers()
        assert len(registry) == len(logger_names)
        for logger_name in logger_names:
            assert logger_name in registry

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file",
    )
    def test_concurrent_file_operations(self):
        """Test concurrent file operations don't conflict."""
        num_threads = 8
        errors = []

        def file_logger_worker(worker_id):
            """Worker that creates file loggers and logs messages."""
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Create size rotating logger
                    with SizeRotatingLog(
                        name=f"file_worker_{worker_id}",
                        directory=temp_dir,
                        filenames=[f"test_{worker_id}.log"],
                        maxmbytes=1,
                        level="INFO",
                    ) as logger:
                        # Log multiple messages
                        for i in range(50):
                            logger.info(f"Worker {worker_id} message {i}: {'A' * 100}")
                            time.sleep(0.001)

            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")

        # Run concurrent file operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(file_logger_worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # No file operation errors should occur
        assert len(errors) == 0, f"File operation errors: {errors}"

    def test_registry_clear_during_operations(self):
        """Test clearing registry while other operations are happening."""
        num_worker_threads = 10
        should_stop = threading.Event()
        errors = []

        def continuous_worker(worker_id):
            """Worker that continuously creates loggers."""
            try:
                while not should_stop.is_set():
                    logger_name = f"continuous_{worker_id}_{int(time.time() * 1000)}"
                    logger = LoggerFactory.get_or_create_logger(
                        LoggerType.BASIC, name=logger_name, level=LogLevel.INFO
                    )
                    logger.info(f"Continuous message from worker {worker_id}")
                    time.sleep(0.01)

            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")

        def registry_clearer():
            """Worker that periodically clears the registry."""
            try:
                for _ in range(5):
                    time.sleep(0.1)
                    clear_logger_registry()

            except Exception as e:
                errors.append(f"Registry clearer: {str(e)}")

        try:
            # Start worker threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_worker_threads + 1) as executor:
                # Start continuous workers
                worker_futures = [executor.submit(continuous_worker, i) for i in range(num_worker_threads)]

                # Start registry clearer
                clearer_future = executor.submit(registry_clearer)

                # Let it run for a bit
                time.sleep(0.5)

                # Signal workers to stop
                should_stop.set()

                # Wait for all to complete
                for future in worker_futures + [clearer_future]:
                    future.result(timeout=5)

        except concurrent.futures.TimeoutError:
            should_stop.set()
            pytest.fail("Thread operations timed out")

        # Should complete without errors
        assert len(errors) == 0, f"Registry clear test errors: {errors}"

    def _create_logger_and_messages(self, worker_id, temp_dir, results_lock, thread_results):
        """Helper to create logger and log messages for a worker thread."""
        logger_instance = SizeRotatingLog(
            name=f"independent_{worker_id}",
            directory=temp_dir,
            filenames=[f"independent_{worker_id}.log"],
            level="DEBUG",
        )

        with logger_instance as logger:
            # Log thread-specific messages
            messages = []
            for i in range(10):
                _message = f"Thread {worker_id} message {i}"
                logger.info(_message)
                messages.append(_message)

            # Verify log file and read content
            log_file = os.path.join(temp_dir, f"independent_{worker_id}.log")
            assert os.path.exists(log_file), f"Log file missing for thread {worker_id}"

            with open(log_file, 'r') as f:
                _log_content = f.read()

            # Verify all messages are in the file
            for _message in messages:
                assert _message in _log_content

            with results_lock:
                thread_results[worker_id] = {'messages': messages, 'log_content': _log_content}

    def _verify_thread_results(self, thread_results, num_threads):
        """Helper to verify all thread results are successful."""
        for worker_id in range(num_threads):
            assert worker_id in thread_results
            assert (
                'error' not in thread_results[worker_id]
            ), f"Thread {worker_id} failed: {thread_results[worker_id].get('error')}"
            assert 'messages' in thread_results[worker_id]
            assert len(thread_results[worker_id]['messages']) == 10

    def _check_worker_log_isolation(self, worker_id, log_content, thread_results, num_threads):
        """Check that a worker's log doesn't contain messages from other workers."""
        for other_id in range(num_threads):
            if other_id != worker_id:
                for message in thread_results[other_id]['messages']:
                    assert (
                        message not in log_content
                    ), f"Thread {worker_id} log contains message from thread {other_id}"

    def _verify_no_cross_contamination(self, thread_results, num_threads):
        """Helper to verify no cross-contamination between thread logs."""
        for worker_id in range(num_threads):
            log_content = thread_results[worker_id]['log_content']
            self._check_worker_log_isolation(worker_id, log_content, thread_results, num_threads)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file",
    )
    def test_thread_local_logger_independence(self):
        """Test that loggers in different threads don't interfere with each other."""
        num_threads = 5
        thread_results = {}
        results_lock = threading.Lock()

        def independent_worker(worker_id):
            """Worker that creates and uses independent loggers."""
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    self._create_logger_and_messages(worker_id, temp_dir, results_lock, thread_results)

            except Exception as e:
                with results_lock:
                    thread_results[worker_id] = {'error': str(e)}

        # Run independent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(independent_worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify all threads succeeded
        self._verify_thread_results(thread_results, num_threads)

        # Verify no cross-contamination between threads
        self._verify_no_cross_contamination(thread_results, num_threads)


if __name__ == "__main__":
    pytest.main([__file__])
