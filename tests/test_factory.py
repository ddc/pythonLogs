#!/usr/bin/env python3
"""Test the factory pattern implementation."""
import os
import sys
import tempfile
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from pythonLogs import (
    LoggerFactory,
    LoggerType,
    LogLevel,
    RotateWhen,
    create_logger,
    get_or_create_logger,
    basic_logger,
    size_rotating_logger,
    timed_rotating_logger,
    clear_logger_registry,
    get_registered_loggers,
)


class TestLoggerFactory:
    """Test cases for the LoggerFactory pattern."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_logger_registry()
    
    def test_basic_logger_creation_via_factory(self):
        """Test basic logger creation using factory."""
        _basic_logger = LoggerFactory.create_logger(LoggerType.BASIC, name="test_basic")
        assert _basic_logger.name == "test_basic"
    
    def test_size_rotating_logger_creation(self):
        """Test size rotating logger creation using convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_logger = size_rotating_logger(
                name="test_size",
                directory=temp_dir,
                maxmbytes=5
            )
            assert size_logger.name == "test_size"
    
    def test_timed_rotating_logger_creation(self):
        """Test timed rotating logger creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_logger = timed_rotating_logger(
                name="test_timed",
                directory=temp_dir,
                when="midnight"
            )
            assert timed_logger.name == "test_timed"
    
    def test_logger_registry_caching(self):
        """Test logger registry functionality."""
        # Clear registry and verify it's empty
        clear_logger_registry()
        assert len(get_registered_loggers()) == 0
        
        # Create logger with caching
        logger1 = get_or_create_logger(LoggerType.BASIC, name="cached_logger")
        logger2 = get_or_create_logger(LoggerType.BASIC, name="cached_logger")
        
        # Should be the same instance
        assert logger1 is logger2
        assert len(get_registered_loggers()) == 1
    
    def test_string_based_logger_type_creation(self):
        """Test string-based logger type creation."""
        string_logger = create_logger("basic", name="string_test")
        assert string_logger.name == "string_test"
    
    def test_invalid_logger_type_handling(self):
        """Test error handling for invalid logger types."""
        with pytest.raises(ValueError, match="Invalid logger type"):
            create_logger("invalid_type", name="error_test")
    
    def test_performance_improvement_with_caching(self):
        """Test performance improvements with registry caching."""
        import time
        
        # Test without registry (creates new each time)
        clear_logger_registry()
        start_time = time.time()
        for i in range(20):  # Reduced for faster tests
            create_logger(LoggerType.BASIC, name=f"perf_test_{i}")
        no_cache_time = time.time() - start_time
        
        # Test with registry (reuses loggers)
        clear_logger_registry()
        start_time = time.time()
        for i in range(20):
            get_or_create_logger(LoggerType.BASIC, name="cached_perf_test")
        cached_time = time.time() - start_time
        
        # Cached should be faster (allow some tolerance for test environment)
        assert cached_time <= no_cache_time
    
    def test_convenience_functions(self):
        """Test all convenience functions work correctly."""
        basic_conv = basic_logger(name="conv_basic")
        assert basic_conv.name == "conv_basic"
    
    def test_registry_management(self):
        """Test registry management functions."""
        # Create some loggers
        logger1 = get_or_create_logger(LoggerType.BASIC, name="logger1")
        logger2 = get_or_create_logger(LoggerType.BASIC, name="logger2")
        
        # Check registry contents
        registered = get_registered_loggers()
        assert len(registered) == 2
        assert "logger1" in registered
        assert "logger2" in registered
        
        # Clear registry
        clear_logger_registry()
        assert len(get_registered_loggers()) == 0
    
    def test_logger_with_file_output(self):
        """Test logger creation with actual file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = size_rotating_logger(
                name="file_test",
                directory=temp_dir,
                filenames=["test.log"],
                level="INFO"
            )
            
            # Test logging
            logger.info("Test message")
            logger.warning("Test warning")
            
            # Verify logger is working
            assert logger.name == "file_test"
            assert logger.level == 20  # INFO level

    def test_factory_create_logger_with_enums(self):
        """Test factory create_logger with enum parameters."""
        logger = LoggerFactory.create_logger(
            LoggerType.BASIC,
            level=LogLevel.DEBUG,
            name="enum_test"
        )
        assert logger.name == "enum_test"
        assert logger.level == 10  # DEBUG level

    def test_factory_create_logger_with_strings(self):
        """Test factory create_logger with string parameters."""
        logger = LoggerFactory.create_logger(
            "basic",
            level="WARNING",
            name="string_test"
        )
        assert logger.name == "string_test"
        assert logger.level == 30  # WARNING level

    def test_factory_create_logger_invalid_type(self):
        """Test factory create_logger with invalid logger type."""
        with pytest.raises(ValueError, match="Invalid logger type"):
            LoggerFactory.create_logger("invalid_type")

    def test_factory_create_size_rotating_logger(self):
        """Test factory create_size_rotating_logger method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = LoggerFactory.create_size_rotating_logger(
                name="size_factory_test",
                directory=temp_dir,
                maxmbytes=10,
                level=LogLevel.INFO
            )
            assert logger.name == "size_factory_test"

    def test_factory_create_timed_rotating_logger(self):
        """Test factory create_timed_rotating_logger method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = LoggerFactory.create_timed_rotating_logger(
                name="timed_factory_test",
                directory=temp_dir,
                when=RotateWhen.DAILY,
                level="ERROR"
            )
            assert logger.name == "timed_factory_test"

    def test_factory_create_basic_logger(self):
        """Test factory create_basic_logger method."""
        logger = LoggerFactory.create_basic_logger(
            name="basic_factory_test",
            level=LogLevel.CRITICAL
        )
        assert logger.name == "basic_factory_test"
        assert logger.level == 50  # CRITICAL level

    def test_factory_shutdown_logger(self):
        """Test factory shutdown_logger functionality."""
        # Create and register a logger
        logger = get_or_create_logger(LoggerType.BASIC, name="shutdown_test")
        assert "shutdown_test" in get_registered_loggers()
        
        # Shutdown the logger
        result = LoggerFactory.shutdown_logger("shutdown_test")
        assert result is True
        assert "shutdown_test" not in get_registered_loggers()
        
        # Try to shutdown non-existent logger
        result = LoggerFactory.shutdown_logger("non_existent")
        assert result is False

    def test_factory_get_or_create_with_default_name(self):
        """Test get_or_create_logger with default name."""
        logger = LoggerFactory.get_or_create_logger(LoggerType.BASIC)
        # Should use default appname from settings
        assert logger.name is not None

    def test_factory_enum_conversion_edge_cases(self):
        """Test enum conversion edge cases in factory."""
        # Test with lowercase string
        logger = LoggerFactory.create_logger("basic", name="lowercase_test")
        assert logger.name == "lowercase_test"
        
        # Test with uppercase string
        logger = LoggerFactory.create_logger("BASIC", name="uppercase_test")
        assert logger.name == "uppercase_test"

    def test_convenience_functions_comprehensive(self):
        """Test all convenience functions with various parameters."""
        # Test basic_logger
        basic_log = basic_logger(name="conv_basic", level="DEBUG")
        assert basic_log.name == "conv_basic"
        
        # Test size_rotating_logger
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = size_rotating_logger(
                name="conv_size",
                directory=temp_dir,
                filenames=["test1.log", "test2.log"],
                maxmbytes=5,
                daystokeep=30
            )
            assert size_log.name == "conv_size"
            
            # Test timed_rotating_logger
            timed_log = timed_rotating_logger(
                name="conv_timed",
                directory=temp_dir,
                when="midnight",
                sufix="%Y%m%d",
                daystokeep=7
            )
            assert timed_log.name == "conv_timed"

    def test_factory_pattern_match_case_coverage(self):
        """Test all pattern match cases in factory create_logger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test BASIC case
            basic = LoggerFactory.create_logger(
                LoggerType.BASIC,
                name="match_basic"
            )
            assert basic.name == "match_basic"
            
            # Test SIZE_ROTATING case
            size = LoggerFactory.create_logger(
                LoggerType.SIZE_ROTATING,
                name="match_size",
                directory=temp_dir
            )
            assert size.name == "match_size"
            
            # Test TIMED_ROTATING case
            timed = LoggerFactory.create_logger(
                LoggerType.TIMED_ROTATING,
                name="match_timed",
                directory=temp_dir
            )
            assert timed.name == "match_timed"

    def test_factory_registry_copy_safety(self):
        """Test that get_registered_loggers returns a copy."""
        # Create some loggers
        logger1 = get_or_create_logger(LoggerType.BASIC, name="copy_test1")
        logger2 = get_or_create_logger(LoggerType.BASIC, name="copy_test2")
        
        # Get registry copy
        registry_copy = get_registered_loggers()
        assert len(registry_copy) == 2
        
        # Modify the copy (should not affect original)
        registry_copy["new_logger"] = logger1
        
        # Original registry should be unchanged
        original_registry = get_registered_loggers()
        assert len(original_registry) == 2
        assert "new_logger" not in original_registry

    def test_factory_error_handling_during_cleanup(self):
        """Test error handling during logger cleanup."""
        from unittest.mock import Mock

        # Create a logger
        logger = get_or_create_logger(LoggerType.BASIC, name="cleanup_error_test")
        
        # Create a mock handler that will raise an error on close
        mock_handler = Mock()
        mock_handler.close.side_effect = OSError("Test error")
        logger.addHandler(mock_handler)
        
        # Shutdown should handle the error gracefully
        result = LoggerFactory.shutdown_logger("cleanup_error_test")
        assert result is True
