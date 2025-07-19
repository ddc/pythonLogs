# Test Suite Documentation

This directory contains comprehensive tests for the pythonLogs library, covering all features including Factory Pattern, Context Managers, Memory Management, and Performance Optimizations.

## Test Files Overview

### Core Functionality Tests
- **`test_basic_log.py`** - Comprehensive BasicLog functionality testing
  - Tests BasicLog initialization, context managers, thread safety
  - Validates cleanup methods and multiple instance handling
  - **10 test cases** covering all BasicLog features

- **`test_some_log_utils.py`** - Tests for utility functions
  - Tests helper functions in `log_utils.py`
  - Includes file operations, timezone handling, and validation
  - Multiple test cases for various utilities

### Context Manager & Resource Management Tests
- **`test_context_managers.py`** - Context manager functionality for all logger types
  - Tests automatic resource cleanup for BasicLog, SizeRotatingLog, TimedRotatingLog
  - Validates exception safety and proper handler cleanup
  - Tests nested context managers and multiple file handlers
  - **10 test cases** including the new `shutdown_logger` test

- **`test_resource_management.py`** - Resource lifecycle management
  - Test factory registry cleanup and memory management
  - Validates handler cleanup and resource disposal
  - Tests concurrent access safety and performance
  - **9 test cases** for robust resource management

### Logger Type Tests
- **`test_size_rotating.py`** - Size-based rotating logger tests
  - Tests file rotation, compression, and cleanup
  - Context manager functionality and resource management
  - Multiple file handling and stream output
  - Comprehensive size rotation scenarios

- **`test_timed_rotating.py`** - Time-based rotating logger tests
  - Tests time-based rotation (hourly, daily, midnight, weekdays)
  - Context manager functionality and resource management
  - Timezone handling and rotation scheduling
  - Comprehensive time rotation scenarios

### Factory Pattern Tests
- **`test_factory.py`** - Core factory pattern functionality
  - Tests `LoggerFactory` class and all factory methods
  - Validates logger creation, registry caching, and performance
  - Tests error handling and type validation
  - **Multiple test cases** covering all factory features

- **`test_enums.py`** - Enum usage with factory pattern
  - Tests `LogLevel`, `RotateWhen`, and `LoggerType` enums
  - Validates enum-to-string conversion and type safety
  - Tests backward compatibility with string values
  - **10 test cases** covering all enum scenarios

- **`test_factory_examples.py`** - Integration and practical examples
  - Real-world usage scenarios and production-like setups
  - Multi-logger configurations and file-based logging
  - Registry usage patterns and error scenarios
  - **Multiple test cases** demonstrating practical usage

- **`test_string_levels.py`** - String-based level configuration
  - Tests case-insensitive string level handling
  - Validates string to enum conversion
  - Tests all logger types with string levels
  - Comprehensive string level compatibility

### Performance & Memory Tests
- **`test_performance.py`** - Performance and optimization tests
  - Validates caching improvements and performance gains
  - Tests settings caching, registry performance, and memory usage
  - Stress testing and large-scale logger creation
  - Performance benchmarking for optimization features

- **`test_memory_optimization.py`** - Memory management and optimization
  - Test memory usage patterns and cleanup efficiency
  - Validates formatter caching and directory caching
  - Tests garbage collection and memory leak prevention
  - Memory optimization feature validation

- **`test_performance_zoneinfo.py`** - Performance tests for timezone operations
  - Benchmarks timezone function caching and optimization
  - Tests performance under concurrent access and bulk operations
  - Validates memory efficiency of timezone caching
  - Timezone performance optimization validation

### Thread Safety & Concurrency Tests
- **`test_thread_safety.py`** - Concurrency and thread safety
  - Tests concurrent logger creation and registry access
  - Validates thread-safe operations across all components
  - Tests concurrent context manager cleanup
  - Stress testing for multithreaded environments

### Timezone & Migration Tests
- **`test_timezone_migration.py`** - Timezone functionality with zoneinfo
  - Tests migration from pytz to Python's built-in zoneinfo module
  - Validates UTC, localtime, and named timezone support
  - Tests timezone integration with all logger types and factory pattern
  - **Multiple test cases** covering comprehensive timezone scenarios

- **`test_zoneinfo_fallbacks.py`** - Timezone fallback mechanisms and edge cases
  - Tests fallback behavior for systems without complete timezone data
  - Validates error handling and edge cases for timezone operations
  - Tests concurrent access and memory efficiency
  - **Multiple test cases** for robust timezone handling



## Running Tests

### Run All Tests and Create a Coverage Report
```bash
poetry run poe test
```

### Run Specific Test Categories
```bash
# Context managers and resource management
poetry run pytest tests/test_context_managers.py tests/test_resource_management.py -v

# Core logger functionality
poetry run pytest tests/test_basic_log.py tests/test_size_rotating.py tests/test_timed_rotating.py -v

# Factory pattern tests
poetry run pytest tests/test_factory*.py tests/test_enums.py -v

# Performance and memory tests
poetry run pytest tests/test_performance*.py tests/test_memory*.py -v

# Thread safety and concurrency
poetry run pytest tests/test_thread_safety.py -v

# Timezone functionality
poetry run pytest tests/test_timezone*.py tests/test_zoneinfo*.py -v
```
