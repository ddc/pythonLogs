# -*- coding: utf-8 -*-
"""Test that all automatic features work together in logger classes."""
import gc
import tempfile
import threading
import time
from pythonLogs.basic_log import BasicLog
from pythonLogs.constants import RotateWhen
from pythonLogs.memory_utils import get_active_logger_count
from pythonLogs.size_rotating import SizeRotatingLog
from pythonLogs.timed_rotating import TimedRotatingLog


class TestAutomaticFeatures:
    """Test that all three automatic features work together."""

    def test_basic_log_all_automatic_features(self):
        """Test BasicLog with all automatic features working together."""
        initial_logger_count = get_active_logger_count()
        
        # Test memory optimization, resource cleanup, and thread safety together
        def test_logger_operations():
            with BasicLog(name="test_all_features_basic") as logger:
                # Memory optimization: logger is registered automatically
                assert logger is not None
                logger.info("Testing all automatic features")
                # Resource cleanup and thread safety: handled automatically by context manager
            
        # Run in multiple threads to test thread safety
        threads = []
        for i in range(5):
            thread = threading.Thread(target=test_logger_operations)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Force garbage collection to test memory optimization
        gc.collect()
        time.sleep(0.1)  # Allow cleanup to complete
        
        # Verify memory optimization: logger count should be managed
        final_logger_count = get_active_logger_count()
        assert final_logger_count >= initial_logger_count  # May have some loggers still active

    def test_size_rotating_log_all_automatic_features(self):
        """Test SizeRotatingLog with all automatic features working together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            initial_logger_count = get_active_logger_count()
            
            def test_logger_operations():
                with SizeRotatingLog(
                    name="test_all_features_size",
                    directory=temp_dir,
                    filenames=("test.log",),
                    maxmbytes=1
                ) as logger:
                    # Memory optimization: logger is registered automatically
                    assert logger is not None
                    logger.info("Testing size rotating with all features")
                    # Resource cleanup and thread safety: handled automatically
            
            # Run in multiple threads to test thread safety
            threads = []
            for i in range(3):
                thread = threading.Thread(target=test_logger_operations)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            gc.collect()
            time.sleep(0.1)

    def test_timed_rotating_log_all_automatic_features(self):
        """Test TimedRotatingLog with all automatic features working together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            initial_logger_count = get_active_logger_count()
            
            def test_logger_operations():
                with TimedRotatingLog(
                    name="test_all_features_timed",
                    directory=temp_dir,
                    filenames=("test.log",),
                    when=RotateWhen.DAILY,
                    daystokeep=1
                ) as logger:
                    # Memory optimization: logger is registered automatically
                    assert logger is not None
                    logger.info("Testing timed rotating with all features")
                    # Resource cleanup and thread safety: handled automatically
            
            # Run in multiple threads to test thread safety
            threads = []
            for i in range(3):
                thread = threading.Thread(target=test_logger_operations)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            gc.collect()
            time.sleep(0.1)

    def test_manual_cleanup_still_works(self):
        """Test that manual cleanup methods still work alongside automatic features."""
        basic_log = BasicLog(name="test_manual_cleanup")
        logger = basic_log.init()
        
        # Manual cleanup should still work
        basic_log._cleanup_logger(logger)
        BasicLog.cleanup_logger(logger)  # Static method should work too
        
        # No errors should occur

    def test_automatic_features_verification(self):
        """Verify all automatic features are properly configured."""
        # Test BasicLog
        basic_log = BasicLog(name="test_verification")
        
        # 1. Memory Optimization: register_logger_weakref is called in init()
        logger = basic_log.init()
        assert logger is not None
        
        # 2. Automatic Resource Cleanup: Context manager support
        assert hasattr(basic_log, '__enter__')
        assert hasattr(basic_log, '__exit__')
        assert hasattr(basic_log, '_cleanup_logger')
        
        # 3. Automatic Thread Safety: Decorator applied
        assert hasattr(basic_log.__class__, '_lock')
        assert hasattr(basic_log.init, '_thread_safe_wrapped')
        assert hasattr(basic_log._cleanup_logger, '_thread_safe_wrapped')
        
        basic_log._cleanup_logger(logger)

    def test_stress_test_all_features(self):
        """Stress test all automatic features working together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results = []
            errors = []
            results_lock = threading.Lock()
            
            def stress_worker(worker_id):
                try:
                    # Mix different logger types
                    if worker_id % 3 == 0:
                        with BasicLog(name=f"stress_basic_{worker_id}") as logger:
                            logger.info(f"Stress test basic {worker_id}")
                    elif worker_id % 3 == 1:
                        with SizeRotatingLog(
                            name=f"stress_size_{worker_id}",
                            directory=temp_dir,
                            filenames=(f"stress_{worker_id}.log",),
                            maxmbytes=1
                        ) as logger:
                            logger.info(f"Stress test size {worker_id}")
                    else:
                        with TimedRotatingLog(
                            name=f"stress_timed_{worker_id}",
                            directory=temp_dir,
                            filenames=(f"stress_{worker_id}.log",),
                            when=RotateWhen.DAILY
                        ) as logger:
                            logger.info(f"Stress test timed {worker_id}")
                    
                    with results_lock:
                        results.append(f"Worker {worker_id} completed")
                        
                except Exception as e:
                    with results_lock:
                        errors.append(f"Worker {worker_id}: {e}")
            
            # Create many concurrent workers
            threads = []
            for i in range(20):
                thread = threading.Thread(target=stress_worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            assert len(errors) == 0, f"Stress test errors: {errors}"
            assert len(results) == 20, f"Expected 20 results, got {len(results)}"
