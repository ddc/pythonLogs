# -*- coding: utf-8 -*-
"""Test automatic thread safety implementation."""
import threading
from pythonLogs.basic_log import BasicLog
from pythonLogs.constants import RotateWhen
from pythonLogs.size_rotating import SizeRotatingLog
from pythonLogs.timed_rotating import TimedRotatingLog


class TestAutomaticThreadSafety:
    """Test cases for automatic thread safety of logger classes."""

    def test_basic_log_automatic_thread_safety(self):
        """Test BasicLog with automatic thread safety decorators."""
        basic_log = BasicLog(name="test_auto_thread_safety")
        results = []
        errors = []

        def worker(worker_id):
            try:
                # These operations should be automatically thread-safe
                logger = basic_log.init()
                logger.info(f"Worker {worker_id} logging message")
                basic_log._cleanup_logger(logger)
                results.append(f"Worker {worker_id} completed")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Automatic thread safety errors: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"

    def test_size_rotating_log_automatic_thread_safety(self):
        """Test SizeRotatingLog with automatic thread safety decorators."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            log = SizeRotatingLog(
                name="test_auto_size_rotating",
                directory=temp_dir,
                filenames=("test.log",),
                maxmbytes=1
            )
            results = []
            errors = []

            def worker(worker_id):
                try:
                    logger = log.init()
                    logger.info(f"Size rotating worker {worker_id}")
                    log._cleanup_logger(logger)
                    results.append(f"Worker {worker_id} completed")
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")

            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            assert len(errors) == 0, f"Size rotating automatic thread safety errors: {errors}"
            assert len(results) == 5, f"Expected 5 results, got {len(results)}"

    def test_timed_rotating_log_automatic_thread_safety(self):
        """Test TimedRotatingLog with automatic thread safety decorators."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log = TimedRotatingLog(
                name="test_auto_timed_rotating",
                directory=temp_dir,
                filenames=("test.log",),
                when=RotateWhen.DAILY,
                daystokeep=1
            )
            results = []
            errors = []

            def worker(worker_id):
                try:
                    logger = log.init()
                    logger.info(f"Timed rotating worker {worker_id}")
                    log._cleanup_logger(logger)
                    results.append(f"Worker {worker_id} completed")
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")

            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            assert len(errors) == 0, f"Timed rotating automatic thread safety errors: {errors}"
            assert len(results) == 5, f"Expected 5 results, got {len(results)}"

    def test_automatic_locking_verification(self):
        """Verify that automatic locking is actually working by checking decorator presence."""
        basic_log = BasicLog(name="test_lock_verification")
        
        # Verify the class has the automatic thread safety decorator applied
        assert hasattr(basic_log.__class__, '_lock'), "Class should have automatic lock"
        assert hasattr(basic_log.init, '_thread_safe_wrapped'), "Method should be wrapped for thread safety"
        assert hasattr(basic_log._cleanup_logger, '_thread_safe_wrapped'), "Method should be wrapped for thread safety"
        
        # Test that methods can still be called normally
        logger = basic_log.init()
        assert logger is not None, "Logger should be initialized"
        basic_log._cleanup_logger(logger)
