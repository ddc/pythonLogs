#!/usr/bin/env python3
"""Performance tests for the factory pattern and optimizations."""
import os
import sys
import tempfile
import time
import pytest


# Add parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tests_dir = os.path.join(project_root, 'tests')
sys.path.insert(0, project_root)  # For pythonLogs
sys.path.insert(0, tests_dir)  # For test_utils in tests/
from test_utils import get_safe_timezone

from pythonLogs import (
    LoggerFactory,
    LoggerType,
    LogLevel,
    create_logger,
    get_or_create_logger,
    basic_logger,
    size_rotating_logger,
    clear_logger_registry,
    get_registered_loggers,
)


class TestPerformance:
    """Performance tests for factory pattern and optimizations."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()
    
    def test_settings_caching_performance(self):
        """Test that settings caching improves performance."""
        # Create multiple loggers (should reuse cached settings)
        start_time = time.time()
        
        loggers = []
        for i in range(50):  # Reasonable number for CI/testing
            logger = LoggerFactory.create_logger(
                LoggerType.BASIC,
                name=f"settings_test_{i}"
            )
            loggers.append(logger)
        
        elapsed_time = time.time() - start_time
        
        # Should complete relatively quickly (less than 1 second)
        assert elapsed_time < 1.0
        assert len(loggers) == 50
        
        # Verify all loggers were created with unique names
        names = {logger.name for logger in loggers}
        assert len(names) == 50
    
    def test_registry_caching_performance(self):
        """Test that registry caching provides significant performance improvement."""
        # Baseline: Create new loggers each time
        start_time = time.time()
        for i in range(30):
            create_logger(LoggerType.BASIC, name=f"no_cache_{i}")
        no_cache_time = time.time() - start_time
        
        # With caching: Reuse same logger
        clear_logger_registry()
        start_time = time.time()
        for i in range(30):
            get_or_create_logger(LoggerType.BASIC, name="cached_logger")
        cache_time = time.time() - start_time
        
        # Cached should be significantly faster
        # Allow some tolerance for test environment variability
        performance_improvement = (no_cache_time - cache_time) / no_cache_time
        assert performance_improvement > 0.1  # At least 10% improvement
        
        # Verify only one logger was actually created
        assert len(get_registered_loggers()) == 1
    
    def test_directory_permission_caching(self):
        """Test that directory permission checking is cached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # First call should check and cache directory permissions
            start_time = time.time()
            logger1 = size_rotating_logger(
                name="dir_test_1",
                directory=temp_dir
            )
            first_call_time = time.time() - start_time
            
            # Subsequent calls to the same directory should be faster (cached)
            start_time = time.time()
            for i in range(10):
                logger = size_rotating_logger(
                    name=f"dir_test_{i+2}",
                    directory=temp_dir  # The Same directory should use cache
                )
            subsequent_calls_time = time.time() - start_time
            
            # The Average time per subsequent call should be less than the first call
            avg_subsequent_time = subsequent_calls_time / 10
            assert avg_subsequent_time <= first_call_time
    
    def test_timezone_function_caching(self):
        """Test that timezone functions are cached for performance."""
        # Create multiple loggers with same timezone
        start_time = time.time()
        
        safe_tz = get_safe_timezone()
        loggers = []
        for i in range(20):
            logger = basic_logger(
                name=f"tz_test_{i}",
                timezone=safe_tz  # Same timezone should use cached function
            )
            loggers.append(logger)
        
        elapsed_time = time.time() - start_time
        
        # Should complete quickly due to timezone caching
        assert elapsed_time < 0.5
        assert len(loggers) == 20
    
    def test_enum_vs_string_performance(self):
        """Test that enum usage doesn't significantly impact performance."""
        # Test with string values
        start_time = time.time()
        for i in range(25):
            create_logger("basic", name=f"string_test_{i}", level="INFO")
        string_time = time.time() - start_time
        
        # Test with enum values
        start_time = time.time()
        for i in range(25):
            create_logger(LoggerType.BASIC, name=f"enum_test_{i}", level=LogLevel.INFO)
        enum_time = time.time() - start_time
        
        # Enum performance should be comparable to strings
        # Allow 60% tolerance for enum conversion overhead
        assert enum_time <= string_time * 1.6
    
    def test_large_scale_logger_creation(self):
        """Test performance with larger number of loggers."""
        start_time = time.time()
        
        # Create 100 different loggers
        loggers = []
        for i in range(100):
            logger = LoggerFactory.create_logger(
                LoggerType.BASIC,
                name=f"scale_test_{i}",
                level=LogLevel.INFO
            )
            loggers.append(logger)
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 2 seconds)
        assert elapsed_time < 2.0
        assert len(loggers) == 100
        
        # Verify all loggers are unique
        names = {logger.name for logger in loggers}
        assert len(names) == 100
    
    def test_mixed_logger_types_performance(self):
        """Test performance when creating mixed logger types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()
            
            loggers = []
            for i in range(30):  # 10 of each type
                if i % 3 == 0:
                    logger = create_logger(LoggerType.BASIC, name=f"mixed_basic_{i}")
                elif i % 3 == 1:
                    logger = size_rotating_logger(
                        name=f"mixed_size_{i}",
                        directory=temp_dir
                    )
                else:
                    logger = create_logger(
                        LoggerType.TIMED_ROTATING,
                        name=f"mixed_timed_{i}",
                        directory=temp_dir
                    )
                loggers.append(logger)
            
            elapsed_time = time.time() - start_time
            
            # Should complete efficiently
            assert elapsed_time < 1.5
            assert len(loggers) == 30
    
    def test_memory_usage_with_registry(self):
        """Test that registry doesn't cause excessive memory usage."""
        # Create many loggers in registry
        for i in range(50):
            get_or_create_logger(LoggerType.BASIC, name=f"memory_test_{i}")
        
        # Verify registry contains expected number
        registered = get_registered_loggers()
        assert len(registered) == 50
        
        # Clear registry
        clear_logger_registry()
        
        # Verify registry is empty
        assert len(get_registered_loggers()) == 0
    
    @pytest.mark.slow
    def test_stress_test_factory_pattern(self):
        """Stress test the factory pattern with intensive usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()
            
            # Intensive mixed usage
            for i in range(200):
                if i % 4 == 0:
                    logger = get_or_create_logger(LoggerType.BASIC, name="stress_cached")
                elif i % 4 == 1:
                    logger = create_logger("basic", name=f"stress_basic_{i}")
                elif i % 4 == 2:
                    logger = size_rotating_logger(
                        name=f"stress_size_{i}",
                        directory=temp_dir,
                        level=LogLevel.WARNING
                    )
                else:
                    logger = LoggerFactory.create_logger(
                        LoggerType.TIMED_ROTATING,
                        name=f"stress_timed_{i}",
                        directory=temp_dir,
                        when="midnight"
                    )
                
                # Actually use the logger
                logger.info(f"Stress test message {i}")
            
            elapsed_time = time.time() - start_time
            
            # Should complete in reasonable time even under stress
            assert elapsed_time < 5.0  # 5 seconds max for 200 loggers
            
            # Verify registry has cached logger
            assert "stress_cached" in get_registered_loggers()
