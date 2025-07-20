# Test Suite Documentation

This directory contains comprehensive tests for the pythonLogs library, organized into logical categories for better maintainability and navigation.

## Test Directory Structure

```
tests/
├── core/                     # Core functionality tests
├── context_management/       # Context managers & resource management 
├── logger_types/            # Specific logger type tests
├── factory/                 # Factory pattern tests
├── performance/             # Performance & memory optimization tests
├── thread_safety/           # Thread safety & concurrency tests
└── timezone/                # Timezone functionality tests
```

## Test Files Overview

### Core Functionality Tests (`tests/core/`)
- **`test_basic_log.py`** - Comprehensive BasicLog functionality testing
  - Tests BasicLog initialization, context managers, thread safety
  - Validates cleanup methods and multiple instance handling
  - **10 test cases** covering all BasicLog features

- **`test_log_utils.py`** - Tests for utility functions
  - Tests helper functions in `log_utils.py`
  - Includes file operations, timezone handling, and validation
  - Multiple test cases for various utilities

### Context Manager & Resource Management Tests (`tests/context_management/`)
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

### Logger Type Tests (`tests/logger_types/`)
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

### Factory Pattern Tests (`tests/factory/`)
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

### Performance & Memory Tests (`tests/performance/`)
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

### Thread Safety & Concurrency Tests (`tests/thread_safety/`)
- **`test_thread_safety.py`** - Concurrency and thread safety
  - Tests concurrent logger creation and registry access
  - Validates thread-safe operations across all components
  - Tests concurrent context manager cleanup
  - Stress testing for multithreaded environments

- **`test_automatic_thread_safety.py`** - Automatic thread safety implementation
  - Tests automatic thread-safety decorators applied to logger classes
  - Validates @auto_thread_safe decorator functionality
  - Tests BasicLog, SizeRotatingLog, and TimedRotatingLog with automatic locking
  - **4 test cases** covering automatic thread safety features

- **`test_thread_safety_module.py`** - Comprehensive thread safety module tests
  - Test all thread safety decorators (@thread_safe, @auto_thread_safe)
  - Tests ThreadSafeMeta metaclass and AutoThreadSafe base class
  - Tests ThreadSafeContext context manager and edge cases
  - **19 test cases** covering all thread safety mechanisms

- **`test_thread_safety_patterns.py`** - Advanced thread safety patterns
  - Tests real-world concurrent patterns (producer-consumer, singleton, etc.)
  - Tests resource pool, event bus, and cache patterns with thread safety
  - Tests weak reference cleanup in multithreaded environments
  - **8 test cases** covering complex thread safety scenarios

- **`test_automatic_features.py`** - Integration of all automatic features
  - Test memory optimization, resource cleanup, and thread safety together
  - Validates all three automatic features work seamlessly
  - Tests stress scenarios with multiple logger types concurrently
  - **6 test cases** ensuring all automatic features integrate properly

### Timezone & Migration Tests (`tests/timezone/`)
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
# Core functionality tests
poetry run pytest tests/core/ -v

# Context managers and resource management
poetry run pytest tests/context_management/ -v

# Logger type tests (size rotating, timed rotating)
poetry run pytest tests/logger_types/ -v

# Factory pattern tests
poetry run pytest tests/factory/ -v

# Performance and memory optimization tests
poetry run pytest tests/performance/ -v

# Thread safety and concurrency tests
poetry run pytest tests/thread_safety/ -v

# Timezone functionality tests
poetry run pytest tests/timezone/ -v

# Run specific directories together
poetry run pytest tests/core/ tests/logger_types/ -v    # Core + Logger types
poetry run pytest tests/performance/ tests/thread_safety/ -v    # Performance + Concurrency
```
