#!/usr/bin/env python3
"""Performance tests for zoneinfo vs pytz migration."""
import os
import sys
import tempfile
import time
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import (
    basic_logger,
    size_rotating_logger,
    LogLevel,
    clear_logger_registry,
)


class TestZoneinfoPerformance:
    """Performance tests for zoneinfo timezone operations."""

    def setup_method(self):
        """Clear registry and caches before each test."""
        clear_logger_registry()

        # Clear timezone caches
        from pythonLogs.log_utils import get_timezone_function, get_timezone_offset, get_stderr_timezone

        get_timezone_function.cache_clear()
        get_timezone_offset.cache_clear()
        get_stderr_timezone.cache_clear()

    def test_timezone_function_caching_performance(self):
        """Test that timezone function caching improves performance."""
        from pythonLogs.log_utils import get_timezone_function

        # First call (not cached) - single call to prime the cache
        start_time = time.time()
        get_timezone_function("America/New_York")
        first_call_time = time.time() - start_time

        # Subsequent calls (should be from cache)
        start_time = time.time()
        for _ in range(50):
            get_timezone_function("America/New_York")  # Same timezone, should be cached
        cached_call_time = time.time() - start_time

        # Cached calls should be significantly faster per call
        # Compare average time per call
        cached_avg_time = cached_call_time / 50
        assert cached_avg_time <= first_call_time  # Cached should be faster or equal

    def test_timezone_offset_caching_performance(self):
        """Test timezone offset calculation caching performance."""
        from pythonLogs.log_utils import get_timezone_offset

        # Test with multiple calls to the same timezone
        start_time = time.time()
        for _ in range(100):
            get_timezone_offset("UTC")  # Should be cached after first call
        cached_time = time.time() - start_time

        # Should complete very quickly due to caching
        assert cached_time < 0.1  # Should be very fast

    def test_logger_creation_performance_with_timezones(self):
        """Test logger creation performance with various timezones."""
        timezones = ["UTC", "localtime", "America/Chicago", "Europe/London"]

        start_time = time.time()

        loggers = []
        for i in range(40):  # 10 loggers per timezone
            tz = timezones[i % len(timezones)]
            logger = basic_logger(name=f"perf_test_{i}", timezone=tz, level=LogLevel.INFO)
            loggers.append(logger)

        elapsed_time = time.time() - start_time

        # Should complete in reasonable time
        assert elapsed_time < 1.0  # 1 second for 40 loggers
        assert len(loggers) == 40

    def test_concurrent_timezone_performance(self):
        """Test timezone performance under concurrent access."""
        import threading

        results = []

        def timezone_worker(worker_id):
            start_time = time.time()

            # Create loggers with same timezone (should benefit from caching)
            for i in range(10):
                logger = basic_logger(name=f"concurrent_{worker_id}_{i}", timezone="UTC")
                logger.info(f"Concurrent test {worker_id}-{i}")

            elapsed = time.time() - start_time
            results.append(elapsed)

        # Run concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=timezone_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All workers should complete in reasonable time
        assert len(results) == 5
        for elapsed in results:
            assert elapsed < 0.5  # Each worker should complete quickly

    def test_timezone_memory_efficiency(self):
        """Test memory efficiency of timezone caching."""
        try:
            import psutil
            import os

            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss

            # Create many loggers with same timezone
            loggers = []
            for i in range(200):
                logger = basic_logger(name=f"memory_test_{i}", timezone="America/New_York")  # Same timezone for all
                loggers.append(logger)

            # Get memory usage after logger creation
            after_creation_memory = process.memory_info().rss

            # Clear loggers
            loggers.clear()
            clear_logger_registry()

            # Memory increase should be reasonable (not linear with the number of loggers)
            memory_increase = after_creation_memory - initial_memory

            # Allow up to 50MB increase for 200 loggers (should be much less with caching)
            assert memory_increase < 50 * 1024 * 1024  # 50MB

        except ImportError:
            # psutil not available, just test that we can create many loggers without crashing
            loggers = []
            for i in range(200):
                logger = basic_logger(name=f"memory_test_{i}", timezone="America/New_York")
                loggers.append(logger)

            # If we get here without errors, memory usage is acceptable
            assert len(loggers) == 200

            # Clear loggers
            loggers.clear()
            clear_logger_registry()

    def test_timezone_function_performance_comparison(self):
        """Compare performance of different timezone function types."""
        from pythonLogs.log_utils import get_timezone_function

        # Test UTC (should return time.gmtime - fastest)
        start_time = time.time()
        for _ in range(1000):
            func = get_timezone_function("UTC")
            func()  # Call the function
        utc_time = time.time() - start_time

        # Test localtime (should return time.localtime - fast)
        start_time = time.time()
        for _ in range(1000):
            func = get_timezone_function("localtime")
            func()  # Call the function
        local_time = time.time() - start_time

        # Test named timezone (custom function - should be reasonable)
        start_time = time.time()
        for _ in range(1000):
            func = get_timezone_function("America/Chicago")
            func()  # Call the function
        named_time = time.time() - start_time

        # UTC and localtime should be fastest (native functions)
        # Named timezone will be slower but should still be reasonable
        assert utc_time < 0.1
        assert local_time < 0.1
        assert named_time < 1.0  # Allow more time for named timezones

    def test_bulk_logger_creation_performance(self):
        """Test performance when creating many loggers with timezones."""
        start_time = time.time()

        # Create 100 loggers with various timezones
        timezones = ["UTC", "localtime", "America/New_York", "Europe/Paris", "Asia/Tokyo"]

        for i in range(100):
            tz = timezones[i % len(timezones)]
            logger = basic_logger(name=f"bulk_test_{i}", timezone=tz)
            # Actually use the logger to ensure it's fully initialized
            logger.info(f"Bulk test message {i}")

        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (less than 2 seconds for 100 loggers)
        assert elapsed_time < 2.0

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file",
    )
    def test_file_logger_timezone_performance(self):
        """Test performance of file-based loggers with timezones."""
        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()

            # Create file-based loggers with timezones
            for i in range(20):
                logger = size_rotating_logger(
                    name=f"file_tz_test_{i}",
                    directory=temp_dir,
                    timezone="America/Chicago",
                    level=LogLevel.INFO,
                    streamhandler=False,
                )

                # Write some log messages
                for j in range(5):
                    logger.info(f"File timezone test {i}-{j}")

            elapsed_time = time.time() - start_time

            # Should complete in reasonable time
            assert elapsed_time < 1.5  # 1.5 seconds for 20 file loggers with 100 messages

    @pytest.mark.slow
    def test_stress_test_timezone_operations(self):
        """Stress test timezone operations for performance and stability."""
        import threading
        import random

        timezones = [
            "UTC",
            "localtime",
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Australia/Sydney",
        ]

        errors = []

        def stress_worker(worker_id):
            try:
                for __i in range(50):
                    # Random timezone selection
                    tz = random.choice(timezones)

                    logger = basic_logger(name=f"stress_{worker_id}_{__i}", timezone=tz, level=LogLevel.INFO)
                    logger.info(f"Stress test message {worker_id}-{__i} with {tz}")

                    # Small delay to simulate real usage
                    time.sleep(0.001)

            except Exception as e:
                errors.append((worker_id, e))

        # Run stress test with multiple workers
        start_time = time.time()

        threads = []
        for _i in range(10):  # 10 workers
            thread = threading.Thread(target=stress_worker, args=(_i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        elapsed_time = time.time() - start_time

        # Should complete without errors
        assert len(errors) == 0, f"Errors during stress test: {errors}"

        # Should complete in reasonable time (10 workers * 50 operations each)
        assert elapsed_time < 30.0  # 30 seconds for 500 total operations
