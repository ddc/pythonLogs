#!/usr/bin/env python3
"""Windows-specific performance tests for the factory pattern and optimizations."""
import os
import sys
import time
import pytest

# Add parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)  # For pythonLogs

# Import test utilities
from tests.core.test_log_utils import get_safe_timezone, windows_safe_temp_directory

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


class TestPerformanceWindows:
    """Windows-specific performance tests for factory pattern and optimizations."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_directory_permission_caching_windows(self):
        """Test that directory permission checking is cached on Windows."""
        with windows_safe_temp_directory() as temp_dir:
            # First call should check and cache directory permissions
            start_time = time.time()
            logger1 = size_rotating_logger(
                name="dir_test_1_win",
                directory=temp_dir
            )
            first_call_time = time.time() - start_time
            
            # Subsequent calls to the same directory should be faster (cached)
            start_time = time.time()
            for i in range(10):
                logger = size_rotating_logger(
                    name=f"dir_test_{i+2}_win",
                    directory=temp_dir  # Same directory should use cache
                )
            subsequent_calls_time = time.time() - start_time
            
            # Average time per subsequent call should be less than or equal to the first call
            # Windows may have less precise timing, so we're more lenient
            avg_subsequent_time = subsequent_calls_time / 10
            assert avg_subsequent_time <= first_call_time * 2  # Allow 2x tolerance for Windows
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_mixed_logger_types_performance_windows(self):
        """Test performance when creating mixed logger types on Windows."""
        with windows_safe_temp_directory() as temp_dir:
            start_time = time.time()
            
            loggers = []
            for i in range(30):  # 10 of each type
                if i % 3 == 0:
                    logger = create_logger(LoggerType.BASIC, name=f"mixed_basic_{i}_win")
                elif i % 3 == 1:
                    logger = size_rotating_logger(
                        name=f"mixed_size_{i}_win",
                        directory=temp_dir
                    )
                else:
                    logger = create_logger(
                        LoggerType.TIMED_ROTATING,
                        name=f"mixed_timed_{i}_win",
                        directory=temp_dir
                    )
                loggers.append(logger)
            
            elapsed_time = time.time() - start_time
            
            # Should complete efficiently - Windows gets more time allowance
            assert elapsed_time < 3.0  # Increased from 1.5s to 3.0s for Windows
            assert len(loggers) == 30
    
    @pytest.mark.slow
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_stress_test_factory_pattern_windows(self):
        """Stress test the factory pattern with intensive usage on Windows."""
        with windows_safe_temp_directory() as temp_dir:
            start_time = time.time()
            
            # Intensive mixed usage
            for i in range(200):
                if i % 4 == 0:
                    logger = get_or_create_logger(LoggerType.BASIC, name="stress_cached_win")
                elif i % 4 == 1:
                    logger = create_logger("basic", name=f"stress_basic_{i}_win")
                elif i % 4 == 2:
                    logger = size_rotating_logger(
                        name=f"stress_size_{i}_win",
                        directory=temp_dir,
                        level=LogLevel.WARNING
                    )
                else:
                    logger = LoggerFactory.create_logger(
                        LoggerType.TIMED_ROTATING,
                        name=f"stress_timed_{i}_win",
                        directory=temp_dir,
                        when="midnight"
                    )
                
                # Actually use the logger
                logger.info(f"Stress test message {i}")
            
            elapsed_time = time.time() - start_time
            
            # Should complete in reasonable time even under stress - Windows gets more time
            assert elapsed_time < 10.0  # Increased from 5.0s to 10.0s for Windows
            
            # Verify registry has cached logger
            assert "stress_cached_win" in get_registered_loggers()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
    def test_windows_file_locking_resilience_performance(self):
        """Test performance with Windows file locking scenarios."""
        with windows_safe_temp_directory() as temp_dir:
            start_time = time.time()
            
            # Create multiple loggers that might compete for file access
            loggers = []
            for i in range(20):
                logger = size_rotating_logger(
                    name=f"file_lock_test_{i}_win",
                    directory=temp_dir,
                    filenames=[f"test_{i}.log"],
                    maxmbytes=1,  # Small files to trigger rotation
                    level=LogLevel.INFO
                )
                loggers.append(logger)
                
                # Generate some log messages to trigger file operations
                for j in range(5):
                    logger.info(f"Test message {j} from logger {i}")
            
            elapsed_time = time.time() - start_time
            
            # Should complete without hanging due to file locks
            assert elapsed_time < 5.0
            assert len(loggers) == 20


if __name__ == "__main__":
    pytest.main([__file__])