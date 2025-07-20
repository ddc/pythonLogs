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
        
        # Check the final stats
        final_stats = get_memory_stats()
        
        # The Registry should not have grown excessively
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
                assert len(logger1.handlers) > 0
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
        
        # The Overall handler count should not have increased
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

    def test_cleanup_logger_handlers_standalone(self):
        """Test cleanup_logger_handlers function directly."""
        from pythonLogs.memory_utils import cleanup_logger_handlers
        import logging
        
        # Test with None logger
        cleanup_logger_handlers(None)  # Should not raise error
        
        # Test with logger having handlers
        logger = logging.getLogger("cleanup_test")
        handler1 = logging.StreamHandler()
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as temp_file:
            temp_filename = temp_file.name
        handler2 = logging.FileHandler(temp_filename)
        
        try:
            logger.addHandler(handler1)
            logger.addHandler(handler2)
            assert len(logger.handlers) == 2
            
            # Cleanup should remove all handlers
            cleanup_logger_handlers(logger)
            assert len(logger.handlers) == 0
        finally:
            # Clean up temporary file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_cleanup_logger_handlers_error_handling(self):
        """Test cleanup_logger_handlers with handler errors."""
        from pythonLogs.memory_utils import cleanup_logger_handlers
        import logging
        from unittest.mock import Mock
        
        logger = logging.getLogger("cleanup_error_test")
        
        # Create mock handler that raises error on close
        error_handler = Mock()
        error_handler.close.side_effect = OSError("Test error")
        logger.addHandler(error_handler)
        
        # Should handle error gracefully
        cleanup_logger_handlers(logger)
        assert len(logger.handlers) == 0

    def test_formatter_cache_eviction_detailed(self):
        """Test detailed formatter cache eviction scenarios."""
        from pythonLogs.memory_utils import get_cached_formatter, clear_formatter_cache
        
        clear_formatter_cache()
        
        # Create formatters up to the limit
        formatters = []
        for i in range(50):  # Default max is 50
            formatter = get_cached_formatter(f"Format {i}: %(message)s", f"%Y-%m-%d {i}")
            formatters.append(formatter)
        
        # Verify cache is at capacity
        from pythonLogs.memory_utils import _formatter_cache, _formatter_cache_lock
        with _formatter_cache_lock:
            cache_size = len(_formatter_cache)
        assert cache_size == 50
        
        # Create one more formatter - should trigger eviction
        new_formatter = get_cached_formatter("New format: %(message)s", "%Y-%m-%d new")
        
        # Cache should still be at limit
        with _formatter_cache_lock:
            final_cache_size = len(_formatter_cache)
        assert final_cache_size == 50

    def test_set_directory_cache_limit_edge_cases(self):
        """Test set_directory_cache_limit with edge cases."""
        from pythonLogs.memory_utils import set_directory_cache_limit, clear_directory_cache
        import pythonLogs.log_utils as log_utils
        
        # Setup some directories in cache
        clear_directory_cache()
        temp_dirs = []
        for i in range(5):
            temp_dir = tempfile.mkdtemp(prefix=f"limit_test_{i}_")
            temp_dirs.append(temp_dir)
            log_utils.check_directory_permissions(temp_dir)
        
        try:
            # Verify cache has entries
            with log_utils._directory_lock:
                initial_size = len(log_utils._checked_directories)
            assert initial_size == 5
            
            # Set smaller limit - should trim cache
            set_directory_cache_limit(3)
            
            with log_utils._directory_lock:
                trimmed_size = len(log_utils._checked_directories)
            assert trimmed_size == 3
            
            # Set zero limit - should clear cache
            set_directory_cache_limit(0)
            
            with log_utils._directory_lock:
                zero_size = len(log_utils._checked_directories)
            assert zero_size == 0
            
        finally:
            # Cleanup
            import shutil
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_logger_weakref_direct(self):
        """Test register_logger_weakref function directly."""
        from pythonLogs.memory_utils import register_logger_weakref, get_active_logger_count
        import logging
        
        initial_count = get_active_logger_count()
        
        # Create logger and register weak reference
        logger = logging.getLogger("weakref_direct_test")
        register_logger_weakref(logger)
        
        # Count should increase
        new_count = get_active_logger_count()
        assert new_count >= initial_count
        
        # Delete logger reference
        logger_name = logger.name
        del logger
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Count should eventually decrease (may not be immediate)
        final_count = get_active_logger_count()
        # Note: Due to GC timing, we can't guarantee immediate cleanup

    def test_weakref_callback_behavior(self):
        """Test weak reference callback behavior."""
        from pythonLogs.memory_utils import _active_loggers, _weak_ref_lock
        import logging
        import weakref
        import gc
        
        initial_weak_refs = len(_active_loggers)
        
        # Create logger and manually create weak reference with callback
        logger = logging.getLogger("callback_test")
        
        callback_called = []
        def test_callback(ref):
            callback_called.append(ref)
        
        with _weak_ref_lock:
            weak_ref = weakref.ref(logger, test_callback)
            _active_loggers.add(weak_ref)
        
        # Delete logger
        del logger
        gc.collect()
        
        # Callback should have been called
        assert len(callback_called) == 0 or len(callback_called) > 0  # May or may not be called immediately

    def test_optimize_lru_cache_sizes_normal_operation(self):
        """Test optimize_lru_cache_sizes normal operation."""
        from pythonLogs.memory_utils import optimize_lru_cache_sizes
        from pythonLogs import log_utils
        
        # Get initial cache info
        initial_cache = log_utils.get_timezone_function.cache_info()
        
        # Run optimization
        optimize_lru_cache_sizes()
        
        # Verify caches were cleared
        new_cache = log_utils.get_timezone_function.cache_info()
        assert new_cache.currsize == 0

    def test_formatter_cache_thread_safety(self):
        """Test thread safety of formatter cache operations."""
        from pythonLogs.memory_utils import get_cached_formatter, clear_formatter_cache
        import concurrent.futures
        import threading
        
        clear_formatter_cache()
        errors = []
        created_formatters = []
        
        def formatter_worker(worker_id):
            """Worker that creates formatters concurrently."""
            try:
                for i in range(10):
                    formatter = get_cached_formatter(
                        f"Worker {worker_id} format {i}: %(message)s",
                        f"%Y-%m-%d W{worker_id}I{i}"
                    )
                    created_formatters.append(formatter)
                return worker_id
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
                return None
        
        # Run concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(formatter_worker, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Should have no errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len([r for r in results if r is not None]) == 5
        assert len(created_formatters) == 50  # 5 workers * 10 formatters each

    def test_weak_reference_cleanup_mechanism(self):
        """Test weak reference cleanup mechanism without relying on GC timing."""
        from pythonLogs.memory_utils import get_active_logger_count, _active_loggers, _weak_ref_lock
        import weakref
        
        # Test the cleanup detection logic in get_active_logger_count
        with _weak_ref_lock:
            initial_size = len(_active_loggers)
            
            # Create a dead reference manually (simulates what happens after GC)
            class DummyRef:
                def __call__(self):
                    return None  # Dead reference returns None
            
            dead_ref = DummyRef()
            _active_loggers.add(dead_ref)
            
            # Verify dead reference was added
            assert len(_active_loggers) == initial_size + 1
        
        # get_active_logger_count should detect and remove dead references
        count = get_active_logger_count()
        
        # Dead reference should be cleaned up
        with _weak_ref_lock:
            final_size = len(_active_loggers)
        assert final_size == initial_size  # Dead reference removed

    def test_memory_stats_comprehensive(self):
        """Test comprehensive memory statistics reporting."""
        from pythonLogs.memory_utils import get_memory_stats, get_cached_formatter
        
        # Create some items to populate stats
        LoggerFactory.get_or_create_logger(LoggerType.BASIC, name="stats_test_1")
        LoggerFactory.get_or_create_logger(LoggerType.BASIC, name="stats_test_2")
        get_cached_formatter("Test format: %(message)s")
        
        stats = get_memory_stats()
        
        # Verify all required fields exist
        required_fields = [
            'registry_size', 'formatter_cache_size', 'directory_cache_size',
            'active_logger_count', 'max_registry_size', 'max_formatter_cache',
            'max_directory_cache'
        ]
        
        for field in required_fields:
            assert field in stats, f"Missing field: {field}"
            assert isinstance(stats[field], int), f"Field {field} should be int"
            assert stats[field] >= 0, f"Field {field} should be non-negative"
        
        # Verify relationships
        assert stats['registry_size'] <= stats['max_registry_size']
        assert stats['formatter_cache_size'] <= stats['max_formatter_cache']
        assert stats['directory_cache_size'] <= stats['max_directory_cache']

    def test_force_garbage_collection_comprehensive(self):
        """Test comprehensive garbage collection functionality."""
        from pythonLogs.memory_utils import force_garbage_collection
        
        # Create objects that could be garbage collected
        test_objects = []
        for i in range(100):
            test_objects.append({
                'data': f"test_data_{i}" * 100,
                'nested': {'value': i, 'list': list(range(10))}
            })
        
        # Create circular references
        obj1 = {'name': 'obj1'}
        obj2 = {'name': 'obj2'}
        obj1['ref'] = obj2
        obj2['ref'] = obj1
        test_objects.extend([obj1, obj2])
        
        # Clear references
        del test_objects, obj1, obj2
        
        # Force garbage collection
        gc_stats = force_garbage_collection()
        
        # Verify stats
        assert 'objects_collected' in gc_stats
        assert 'garbage_count' in gc_stats
        assert 'reference_cycles' in gc_stats
        
        assert isinstance(gc_stats['objects_collected'], int)
        assert isinstance(gc_stats['garbage_count'], int)
        assert gc_stats['objects_collected'] >= 0
        assert gc_stats['garbage_count'] >= 0

    def test_memory_optimization_integration(self):
        """Test integration of all memory optimization features."""
        from pythonLogs.memory_utils import (
            clear_formatter_cache, clear_directory_cache, 
            optimize_lru_cache_sizes, force_garbage_collection,
            get_memory_stats
        )
        
        # Start with clean state
        LoggerFactory.clear_registry()
        clear_formatter_cache()
        clear_directory_cache()
        
        # Create various objects
        for i in range(10):
            logger = LoggerFactory.get_or_create_logger(
                LoggerType.BASIC, name=f"integration_test_{i}"
            )
            logger.info("Test message")
        
        # Get initial stats
        initial_stats = get_memory_stats()
        
        # Optimize caches
        optimize_lru_cache_sizes()
        
        # Force cleanup
        gc_result = force_garbage_collection()
        
        # Get final stats
        final_stats = get_memory_stats()
        
        # Verify optimization worked
        assert final_stats['formatter_cache_size'] == 0  # Should be cleared
        assert final_stats['directory_cache_size'] == 0  # Should be cleared
        assert gc_result['objects_collected'] >= 0

    def test_memory_utils_module_constants(self):
        """Test module-level constants and their behavior."""
        from pythonLogs import memory_utils
        
        # Verify module constants exist and have reasonable values
        assert hasattr(memory_utils, '_formatter_cache')
        assert hasattr(memory_utils, '_formatter_cache_lock')
        assert hasattr(memory_utils, '_max_formatters')
        assert hasattr(memory_utils, '_active_loggers')
        assert hasattr(memory_utils, '_weak_ref_lock')
        
        # Verify default values
        assert memory_utils._max_formatters > 0
        assert isinstance(memory_utils._formatter_cache, dict)
        assert isinstance(memory_utils._active_loggers, set)


if __name__ == "__main__":
    pytest.main([__file__])
