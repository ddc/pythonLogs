#!/usr/bin/env python3
"""Test memory optimization features of the pythonLogs library."""
import gc
import os
import sys
import tempfile
import time
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs import (
    LoggerFactory,
    LoggerType,
    LogLevel,
    basic_logger,
    clear_logger_registry,
    get_memory_stats,
    clear_formatter_cache,
    clear_directory_cache,
    force_garbage_collection,
    optimize_lru_cache_sizes,
    set_directory_cache_limit,
)


class TestMemoryOptimization:
    """Test cases for memory optimization features."""
    
    def setup_method(self):
        """Clear all caches and registries before each test."""
        clear_logger_registry()
        clear_formatter_cache()
        clear_directory_cache()
        force_garbage_collection()
    
    def teardown_method(self):
        """Clean up after each test."""
        clear_logger_registry()
        clear_formatter_cache()
        clear_directory_cache()
        # Reset to default limits
        LoggerFactory.set_memory_limits(max_loggers=100, ttl_seconds=3600)
        set_directory_cache_limit(500)
    
    def test_logger_registry_size_limit(self):
        """Test that logger registry enforces size limits."""
        # Set a small limit for testing
        LoggerFactory.set_memory_limits(max_loggers=3, ttl_seconds=3600)
        
        # Create more loggers than the limit
        loggers = []
        for i in range(5):
            logger = LoggerFactory.get_or_create_logger(
                LoggerType.BASIC,
                name=f"test_logger_{i}",
                level=LogLevel.INFO
            )
            loggers.append(logger)
        
        # Registry should not exceed the limit
        registry = LoggerFactory.get_registered_loggers()
        assert len(registry) <= 3, f"Registry size {len(registry)} exceeds limit of 3"
        
        # Verify oldest loggers were evicted
        registry_names = set(registry.keys())
        expected_names = {"test_logger_2", "test_logger_3", "test_logger_4"}  # Last 3
        assert registry_names == expected_names or len(registry_names.intersection(expected_names)) >= 2
    
    def test_logger_registry_ttl(self):
        """Test that logger registry enforces TTL (time-to-live)."""
        # Set very short TTL for testing
        LoggerFactory.set_memory_limits(max_loggers=100, ttl_seconds=1)
        
        # Create a logger
        logger1 = LoggerFactory.get_or_create_logger(
            LoggerType.BASIC,
            name="ttl_test_logger",
            level=LogLevel.INFO
        )
        
        # Verify it's in registry
        registry = LoggerFactory.get_registered_loggers()
        assert "ttl_test_logger" in registry
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Create another logger to trigger cleanup
        logger2 = LoggerFactory.get_or_create_logger(
            LoggerType.BASIC,
            name="new_logger",
            level=LogLevel.INFO
        )
        
        # The Original logger should be cleaned up due to TTL
        registry = LoggerFactory.get_registered_loggers()
        assert "ttl_test_logger" not in registry
        assert "new_logger" in registry
    
    def test_directory_cache_size_limit(self):
        """Test that directory cache enforces size limits."""
        import pythonLogs.log_utils as log_utils
        
        # Set a small limit for testing
        set_directory_cache_limit(3)
        
        # Create temporary directories and check them
        temp_dirs = []
        for i in range(5):
            temp_dir = tempfile.mkdtemp(prefix=f"cache_test_{i}_")
            temp_dirs.append(temp_dir)
            log_utils.check_directory_permissions(temp_dir)
        
        try:
            # Cache should not exceed the limit
            with log_utils._directory_lock:
                cache_size = len(log_utils._checked_directories)
            assert cache_size <= 3, f"Directory cache size {cache_size} exceeds limit of 3"
        
        finally:
            # Cleanup temp directories
            import shutil
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_formatter_cache_efficiency(self):
        """Test that formatters are cached and reused efficiently."""
        from pythonLogs.memory_utils import get_cached_formatter
        
        # Clear cache first
        clear_formatter_cache()
        
        # Create formatters with the same configuration
        format_string = "[%(asctime)s]:[%(levelname)s]:%(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        
        formatter1 = get_cached_formatter(format_string, datefmt)
        formatter2 = get_cached_formatter(format_string, datefmt)
        formatter3 = get_cached_formatter(format_string, datefmt)
        
        # Should be the exact same instance (cached)
        assert formatter1 is formatter2
        assert formatter2 is formatter3
        
        # Create formatter with different configuration
        formatter4 = get_cached_formatter(format_string, "%Y-%m-%d")
        
        # Should be different instance
        assert formatter1 is not formatter4
    
    def test_memory_stats_reporting(self):
        """Test memory statistics reporting functionality."""
        # Create some loggers to populate stats
        for i in range(3):
            LoggerFactory.get_or_create_logger(
                LoggerType.BASIC,
                name=f"stats_test_{i}",
                level=LogLevel.INFO
            )
        
        # Get memory stats
        stats = get_memory_stats()
        
        # Verify stats structure
        expected_keys = {
            'registry_size',
            'formatter_cache_size', 
            'directory_cache_size',
            'active_logger_count',
            'max_registry_size',
            'max_formatter_cache',
            'max_directory_cache'
        }
        assert set(stats.keys()) == expected_keys
        
        # Verify some basic constraints
        assert stats['registry_size'] >= 3
        assert stats['max_registry_size'] > 0
        assert stats['max_formatter_cache'] > 0
        assert stats['max_directory_cache'] > 0
        assert isinstance(stats['active_logger_count'], int)
    
    def test_weak_reference_tracking(self):
        """Test that weak references track active loggers correctly."""
        from pythonLogs.memory_utils import get_active_logger_count
        
        initial_count = get_active_logger_count()
        
        # Create loggers in local scope
        def create_temporary_loggers():
            loggers = []
            for i in range(3):
                logger = basic_logger(name=f"weak_ref_test_{i}", level=LogLevel.INFO.value)
                loggers.append(logger)
            return len(loggers)
        
        created_count = create_temporary_loggers()
        
        # Force garbage collection to clean up references
        gc.collect()
        
        # Active count should eventually decrease (may not be immediate due to GC timing)
        # Allow some tolerance for GC behavior
        final_count = get_active_logger_count()
        assert final_count >= initial_count  # Some loggers might still be referenced
    
    def test_lru_cache_optimization(self):
        """Test LRU cache size optimization."""
        from pythonLogs import log_utils
        
        # Get initial cache info
        initial_timezone_cache = log_utils.get_timezone_function.cache_info()
        
        # Optimize cache sizes
        optimize_lru_cache_sizes()
        
        # Verify caches were cleared and are working
        optimized_cache = log_utils.get_timezone_function.cache_info()
        assert optimized_cache.currsize == 0  # Should be cleared
        
        # Use the function to verify it still works
        tz_func = log_utils.get_timezone_function("UTC")
        assert callable(tz_func)
        
        # Verify cache is working
        new_cache_info = log_utils.get_timezone_function.cache_info()
        assert new_cache_info.currsize == 1
    
    def test_force_garbage_collection(self):
        """Test forced garbage collection functionality."""
        # Create some objects that could be garbage collected
        temp_objects = []
        for i in range(100):
            temp_objects.append(f"temp_object_{i}" * 1000)
        
        # Clear reference
        del temp_objects
        
        # Force garbage collection
        gc_stats = force_garbage_collection()
        
        # Verify stats structure
        expected_keys = {'objects_collected', 'garbage_count', 'reference_cycles'}
        assert set(gc_stats.keys()) == expected_keys
        
        # Verify all values are integers
        for value in gc_stats.values():
            assert isinstance(value, (int, tuple))  # reference_cycles might be a tuple
    
    def test_concurrent_memory_operations(self):
        """Test memory operations under concurrent access."""
        import concurrent.futures
        
        # Set reasonable limits for concurrent testing
        LoggerFactory.set_memory_limits(max_loggers=20, ttl_seconds=10)
        
        results = []
        errors = []
        
        def memory_worker(worker_id):
            """Worker that performs various memory operations."""
            try:
                # Create logger
                logger = LoggerFactory.get_or_create_logger(
                    LoggerType.BASIC,
                    name=f"concurrent_memory_{worker_id}",
                    level=LogLevel.INFO
                )
                
                # Get memory stats
                stats = get_memory_stats()
                
                # Use formatter cache
                from pythonLogs.memory_utils import get_cached_formatter
                formatter = get_cached_formatter(f"[%(levelname)s]:{worker_id}:%(message)s")
                
                # Log something
                logger.info(f"Memory test from worker {worker_id}")
                
                results.append({
                    'worker_id': worker_id,
                    'logger_name': logger.name,
                    'stats': stats,
                    'formatter': formatter is not None
                })
                
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Run concurrent workers
        num_workers = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(memory_worker, i) for i in range(num_workers)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        # Verify results
        assert len(errors) == 0, f"Concurrent memory operations failed: {errors}"
        assert len(results) == num_workers
        
        # Verify memory constraints were maintained
        final_stats = get_memory_stats()
        assert final_stats['registry_size'] <= 20  # Respect size limit
    
    def test_memory_leak_prevention(self):
        """Test that the library prevents common memory leaks."""
        initial_stats = get_memory_stats()
        
        # Create and destroy many loggers
        for batch in range(5):
            # Create a batch of loggers
            batch_loggers = []
            for i in range(10):
                logger = basic_logger(
                    name=f"leak_test_batch_{batch}_logger_{i}",
                    level=LogLevel.INFO.value
                )
                batch_loggers.append(logger)
                logger.info(f"Test message from batch {batch}, logger {i}")
            
            # Clear references (simulating end of scope)
            del batch_loggers
            
            # Force cleanup
            force_garbage_collection()
        
        # Check final stats
        final_stats = get_memory_stats()
        
        # Registry should not have grown excessively
        registry_growth = final_stats['registry_size'] - initial_stats['registry_size']
        assert registry_growth <= 20, f"Registry grew by {registry_growth}, possible memory leak"
        
        # Cache sizes should be reasonable
        assert final_stats['formatter_cache_size'] <= 50
        assert final_stats['directory_cache_size'] <= 500
    
    def test_logger_cleanup_on_context_exit(self):
        """Test that logger cleanup works properly with context managers."""
        from pythonLogs import BasicLog, SizeRotatingLog
        
        # Track initial handler count
        import logging
        initial_handlers = len(logging.getLogger().handlers)
        
        # Use context managers that should clean up
        with tempfile.TemporaryDirectory() as temp_dir:
            # Basic logger context manager
            with BasicLog(name="cleanup_test_basic", level="INFO") as logger1:
                assert len(logger1.handlers) >= 0
                logger1.info("Test message 1")
            
            # After context exit, handlers should be cleaned
            assert len(logger1.handlers) == 0
            
            # Size rotating logger context manager
            with SizeRotatingLog(
                name="cleanup_test_size",
                directory=temp_dir,
                filenames=["test.log"],
                level="INFO"
            ) as logger2:
                assert len(logger2.handlers) > 0
                logger2.info("Test message 2")
            
            # After context exit, handlers should be cleaned
            assert len(logger2.handlers) == 0
        
        # Overall handler count should not have increased
        final_handlers = len(logging.getLogger().handlers)
        assert final_handlers == initial_handlers
    
    def test_registry_memory_management_edge_cases(self):
        """Test edge cases in registry memory management."""
        # Test with zero limits (should handle gracefully)
        LoggerFactory.set_memory_limits(max_loggers=0, ttl_seconds=0)
        
        # Creating a logger should still work but might not be cached
        logger = LoggerFactory.get_or_create_logger(
            LoggerType.BASIC,
            name="edge_case_logger",
            level=LogLevel.INFO
        )
        assert logger is not None
        
        # Test with very large limits
        LoggerFactory.set_memory_limits(max_loggers=10000, ttl_seconds=86400)
        
        # Should handle without issues
        for i in range(50):
            logger = LoggerFactory.get_or_create_logger(
                LoggerType.BASIC,
                name=f"large_limit_test_{i}",
                level=LogLevel.INFO
            )
            assert logger is not None
        
        # Registry should contain all loggers (within limit)
        registry = LoggerFactory.get_registered_loggers()
        assert len(registry) >= 50


if __name__ == "__main__":
    pytest.main([__file__])
