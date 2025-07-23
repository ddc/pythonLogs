# High-performance Python logging library

[![Donate](https://img.shields.io/badge/Donate-PayPal-brightgreen.svg?style=plastic)](https://www.paypal.com/ncp/payment/6G9Z78QHUD4RJ)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPi](https://img.shields.io/pypi/v/pythonLogs.svg)](https://pypi.python.org/pypi/pythonLogs)
[![PyPI Downloads](https://static.pepy.tech/badge/pythonLogs)](https://pepy.tech/projects/pythonLogs)
[![codecov](https://codecov.io/gh/ddc/pythonLogs/graph/badge.svg?token=QsjwsmYzgD)](https://codecov.io/gh/ddc/pythonLogs)
[![CI/CD Pipeline](https://github.com/ddc/pythonLogs/actions/workflows/workflow.yml/badge.svg)](https://github.com/ddc/pythonLogs/actions/workflows/workflow.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ddc_pythonLogs&metric=alert_status)](https://sonarcloud.io/dashboard?id=ddc_pythonLogs)  
[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A//actions-badge.atrox.dev/ddc/pythonLogs/badge?ref=main&label=build&logo=none)](https://actions-badge.atrox.dev/ddc/pythonLogs/goto?ref=main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python](https://img.shields.io/pypi/pyversions/pythonLogs.svg)](https://www.python.org/downloads)

[![Support me on GitHub](https://img.shields.io/badge/Support_me_on_GitHub-154c79?style=for-the-badge&logo=github)](https://github.com/sponsors/ddc)

High-performance Python logging library with file rotation and optimized caching for better performance


## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Logger Types](#logger-types)
  - [Basic Logger](#basic-logger)
  - [Size Rotating Logger](#size-rotating-logger)
  - [Timed Rotating Logger](#timed-rotating-logger)
- [Context Manager Support](#context-manager-support)
- [Advanced Factory Features](#advanced-factory-features)
- [Environment Variables](#env-variables-optional--production)
- [Memory Management](#memory-management)
- [Flexible Configuration Options](#flexible-configuration-options)
- [Migration Guide](#migration-guide)
- [Development](#development)
- [Development](#development)
  - [Building from Source](#building-from-source)
  - [Running Tests](#running-tests)
- [License](#license)
- [Support](#support)



# Features

✨ **Factory Pattern** - Easy logger creation with centralized configuration  
🚀 **High Performance** - Optimized caching for 90%+ performance improvements  
🔄 **File Rotation** - Automatic rotation by size or time with compression  
🎯 **Type Safety** - Enum-based configuration with IDE support  
⚙️ **Flexible Configuration** - Environment variables, direct parameters, or defaults  
📍 **Location Tracking** - Optional filename and line number in logs  
🌍 **Timezone Support** - Full timezone handling including `localtime` and `UTC`  
💾 **Memory Efficient** - Logger registry and settings caching  
🔒 **Context Manager Support** - Automatic resource cleanup and exception safety  
🧵 **Thread Safe** - Concurrent access protection for all operations  
🔧 **Resource Management** - Automatic handler cleanup and memory leak prevention  


# Installation
```shell
pip install pythonLogs
```


# Logger Types

## Basic Logger
Console-only logging without file output. Perfect for development and simple applications.

### Using Factory Pattern (Recommended)
```python
from pythonLogs import basic_logger, LogLevel

# Option 1: Using string (simple) (case-insensitive)
logger = basic_logger(
    name="my_app",
    level="debug",  # "debug", "info", "warning", "error", "critical"
    timezone="America/Sao_Paulo",
    showlocation=False
)
logger.warning("This is a warning example")

# Option 2: Using enum (type-safe)
logger = basic_logger(
    name="my_app",
    level=LogLevel.DEBUG,
    timezone="America/Sao_Paulo",
    showlocation=False
)
logger.warning("This is a warning example")
```

### Legacy Method (Still Supported)
```python
from pythonLogs import BasicLog

logger = BasicLog(
    level="debug",
    name="app",
    timezone="America/Sao_Paulo",
    showlocation=False,
).init()
logger.warning("This is a warning example")
```

#### Example Output
`[2024-10-08T19:08:56.918-0300]:[WARNING]:[my_app]:This is a warning example`





## Size Rotating Logger
File-based logging with automatic rotation when files reach a specified size. Rotated files are compressed as `.gz`.

+ **Rotation**: Based on file size (`maxmbytes` parameter)
+ **Naming**: Rotated logs have sequence numbers: `app.log_1.gz`, `app.log_2.gz`
+ **Cleanup**: Old logs deleted based on `daystokeep` (default: 30 days)

### Using Factory Pattern (Recommended)
```python
from pythonLogs import size_rotating_logger, LogLevel

# Option 1: Using string (simple) (case-insensitive)
logger = size_rotating_logger(
    name="my_app",
    level="debug",  # "debug", "info", "warning", "error", "critical"
    directory="/app/logs",
    filenames=["main.log", "app1.log"],
    maxmbytes=5,
    daystokeep=7,
    timezone="America/Chicago",
    streamhandler=True,
    showlocation=False
)
logger.warning("This is a warning example")

# Option 2: Using enum (type-safe)
logger = size_rotating_logger(
    name="my_app",
    level=LogLevel.DEBUG,
    directory="/app/logs",
    filenames=["main.log", "app1.log"],
    maxmbytes=5,
    daystokeep=7,
    timezone="America/Chicago",
    streamhandler=True,
    showlocation=False
)
logger.warning("This is a warning example")
```

### Legacy Method (Still Supported)
```python
from pythonLogs import SizeRotatingLog

logger = SizeRotatingLog(
    level="debug",
    name="app",
    directory="/app/logs",
    filenames=["main.log", "app1.log"],
    maxmbytes=5,
    daystokeep=7,
    timezone="America/Chicago",
    streamhandler=True,
    showlocation=False
).init()
logger.warning("This is a warning example")
```

#### Example Output
`[2024-10-08T19:08:56.918-0500]:[WARNING]:[my_app]:This is a warning example`





## Timed Rotating Logger
File-based logging with automatic rotation based on time intervals. Rotated files are compressed as `.gz`.

+ **Rotation**: Based on time (`when` parameter, defaults to `midnight`)
+ **Naming**: Rotated logs have date suffix: `app_20240816.log.gz`  
+ **Cleanup**: Old logs deleted based on `daystokeep` (default: 30 days)
+ **Supported Intervals**: `midnight`, `hourly`, `daily`, `W0-W6` (weekdays, 0=Monday)

### Using Factory Pattern (Recommended)
```python
from pythonLogs import timed_rotating_logger, LogLevel, RotateWhen

# Option 1: Using string (simple) (case-insensitive)
logger = timed_rotating_logger(
    name="my_app",
    level="debug",  # "debug", "info", "warning", "error", "critical"
    directory="/app/logs", 
    filenames=["main.log", "app2.log"],
    when="midnight",  # String when value
    daystokeep=7,
    timezone="UTC",
    streamhandler=True,
    showlocation=False
)
logger.warning("This is a warning example")

# Option 2: Using enum (type-safe)
logger = timed_rotating_logger(
    name="my_app",
    level=LogLevel.DEBUG,  # Type-safe enum
    directory="/app/logs", 
    filenames=["main.log", "app2.log"],
    when=RotateWhen.MIDNIGHT,  # Type-safe enum
    daystokeep=7,
    timezone="UTC",
    streamhandler=True,
    showlocation=False
)
logger.warning("This is a warning example")
```

### Legacy Method (Still Supported)
```python
from pythonLogs import TimedRotatingLog

logger = TimedRotatingLog(
    level="debug",
    name="app",
    directory="/app/logs",
    filenames=["main.log", "app2.log"],
    when="midnight",
    daystokeep=7,
    timezone="UTC",
    streamhandler=True,
    showlocation=False
).init()
logger.warning("This is a warning example")
```

#### Example Output
`[2024-10-08T19:08:56.918-0000]:[WARNING]:[my_app]:This is a warning example`





# Context Manager Support

Slow, but if you want immediate, deterministic cleanup for a specific scope.\
All logger types support context managers for automatic resource cleanup and exception safety:

## Basic Usage
```python
from pythonLogs import BasicLog, SizeRotatingLog, TimedRotatingLog, LogLevel

# Automatic cleanup with context managers
with BasicLog(name="app", level=LogLevel.INFO) as logger:
    logger.info("This is automatically cleaned up")
    # Handlers are automatically closed on exit

with SizeRotatingLog(name="app", directory="/logs", filenames=["app.log"]) as logger:
    logger.info("File handlers cleaned up automatically")
    # File handlers closed and resources freed

# Exception safety - cleanup happens even if exceptions occur
try:
    with TimedRotatingLog(name="app", directory="/logs") as logger:
        logger.error("Error occurred")
        raise ValueError("Something went wrong")
except ValueError:
    pass  # Logger was still cleaned up properly
```

## Benefits of Context Manager Usage
- 🔒 **Automatic Cleanup** - Handlers are closed and removed automatically
- ⚡ **Exception Safety** - Resources cleaned up even when exceptions occur
- 💾 **Memory Management** - Prevents memory leaks from unclosed handlers
- 🧵 **Thread Safety** - Cleanup operations are thread-safe
- 🔧 **No Manual Management** - No need to manually call cleanup methods

## Factory Pattern + Context Managers
```python
from pythonLogs import LoggerFactory, LoggerType

# Create logger through factory and use with context manager
logger_instance = LoggerFactory.get_or_create_logger(
    LoggerType.SIZE_ROTATING,
    name="production_app",
    directory="/var/log"
)

# Use the logger instance directly
with logger_instance as logger:
    logger.info("Factory created logger with automatic cleanup")
```


# Advanced Factory Features

## Logger Registry (Performance Optimization)
The factory pattern includes a built-in registry that caches loggers for improved performance:

```python
from pythonLogs import get_or_create_logger, LoggerType, clear_logger_registry

# First call creates the logger
logger1 = get_or_create_logger(LoggerType.BASIC, name="cached_app")

# The Second call returns the same logger instance (90% faster)
logger2 = get_or_create_logger(LoggerType.BASIC, name="cached_app")

# Both variables point to the same logger instance
assert logger1 is logger2

# Clear registry when needed (useful for testing)
clear_logger_registry()
```

## Production Setup Example
```python
from pythonLogs import size_rotating_logger, timed_rotating_logger, LogLevel, RotateWhen

# Application logger
app_logger = size_rotating_logger(
    name="production_app",
    directory="/var/log/myapp",
    filenames=["app.log"],
    maxmbytes=50,  # 50MB files
    daystokeep=30,  # Keep 30 days
    level=LogLevel.INFO,
    streamhandler=True,  # Also log to console
    showlocation=True,   # Show file:function:line
    timezone="UTC"
)

# Error logger with longer retention
error_logger = size_rotating_logger(
    name="production_errors", 
    directory="/var/log/myapp",
    filenames=["errors.log"],
    maxmbytes=10,
    daystokeep=90,  # Keep errors longer
    level=LogLevel.ERROR,
    streamhandler=False
)

# Audit logger with daily rotation
audit_logger = timed_rotating_logger(
    name="audit_log",
    directory="/var/log/myapp",
    filenames=["audit.log"],
    when=RotateWhen.MIDNIGHT,
    level=LogLevel.INFO
)

# Use the loggers
app_logger.info("Application started")
error_logger.error("Database connection failed")
audit_logger.info("User admin logged in")
```

## Env Variables (Optional | Production)
The .env variables file can be used by leaving all options blank when calling the function.\
If not specified inside the .env file, it will use the dafault value.\
This is a good approach for production environments, since options can be changed easily.
```python
from pythonLogs import timed_rotating_logger
log = timed_rotating_logger()
```

```
LOG_LEVEL=DEBUG
LOG_TIMEZONE=UTC
LOG_ENCODING=UTF-8
LOG_APPNAME=app
LOG_FILENAME=app.log
LOG_DIRECTORY=/app/logs
LOG_DAYS_TO_KEEP=30
LOG_DATE_FORMAT=%Y-%m-%dT%H:%M:%S
LOG_STREAM_HANDLER=True
LOG_SHOW_LOCATION=False
LOG_MAX_LOGGERS=50
LOG_LOGGER_TTL_SECONDS=1800

# SizeRotatingLog
LOG_MAX_FILE_SIZE_MB=10

# TimedRotatingLog
LOG_ROTATE_WHEN=midnight
LOG_ROTATE_AT_UTC=True
LOG_ROTATE_FILE_SUFIX="%Y%m%d"
```


# Memory Management

The library includes comprehensive memory management features to prevent memory leaks and optimize resource usage:

## Automatic Resource Cleanup
```python
from pythonLogs import clear_logger_registry, shutdown_logger, LoggerFactory

# Clear the entire logger registry with proper cleanup
clear_logger_registry()

# Shutdown specific logger and remove from registry
shutdown_logger("my_app_logger")

# Manual registry management
LoggerFactory.shutdown_logger("specific_logger")
LoggerFactory.clear_registry()
```

## Memory Optimization Features
```python
from pythonLogs import (
    get_memory_stats, 
    clear_formatter_cache, 
    clear_directory_cache,
    optimize_lru_cache_sizes,
    force_garbage_collection
)

# Get current memory usage statistics
stats = get_memory_stats()
print(f"Registry size: {stats['registry_size']}")
print(f"Formatter cache: {stats['formatter_cache_size']}")
print(f"Active loggers: {stats['active_logger_count']}")

# Clear various caches to free memory
clear_formatter_cache()  # Clear cached formatters
clear_directory_cache()  # Clear directory permission cache

# Optimize LRU cache sizes for memory-constrained environments
optimize_lru_cache_sizes()

# Force garbage collection and get collection statistics
gc_stats = force_garbage_collection()
print(f"Objects collected: {gc_stats['objects_collected']}")
```

## Registry Configuration
```python
from pythonLogs import LoggerFactory

# Configure registry limits for memory management
LoggerFactory.set_memory_limits(
    max_loggers=50,    # Maximum cached loggers
    ttl_seconds=1800   # Logger time-to-live (30 minutes)
)

# Monitor registered loggers
registered = LoggerFactory.get_registered_loggers()
print(f"Currently registered: {list(registered.keys())}")
```

# Flexible Configuration Options
You can use either enums (for type safety) or strings (for simplicity):

```python
from pythonLogs import LogLevel, RotateWhen, LoggerType

# Option 1: Type-safe enums (recommended)
LogLevel.DEBUG     # "DEBUG"
LogLevel.INFO      # "INFO"  
LogLevel.WARNING   # "WARNING"
LogLevel.ERROR     # "ERROR"
LogLevel.CRITICAL  # "CRITICAL"

# Option 2: String values (case-insensitive)
"debug"       # Same as LogLevel.DEBUG
"info"        # Same as LogLevel.INFO
"warning"     # Same as LogLevel.WARNING  
"warn"        # Same as LogLevel.WARN (alias)
"error"       # Same as LogLevel.ERROR
"critical"    # Same as LogLevel.CRITICAL
"crit"        # Same as LogLevel.CRIT (alias)
# Also supports: "DEBUG", "Info", "Warning", etc.

# RotateWhen values
RotateWhen.MIDNIGHT   # "midnight"
RotateWhen.HOURLY     # "H"
RotateWhen.DAILY      # "D"
RotateWhen.MONDAY     # "W0"
# ... through SUNDAY  # "W6"
# String equivalents: "midnight", "H", "D", "W0"-"W6"

# LoggerType values
LoggerType.BASIC            # "basic"
LoggerType.SIZE_ROTATING    # "size_rotating"  
LoggerType.TIMED_ROTATING   # "timed_rotating"
# String equivalents: "basic", "size_rotating", "timed_rotating"
```


# Migration Guide

## Upgrading from Legacy to Factory Pattern

The factory pattern is **100% backward compatible**. Your existing code will continue to work unchanged.

### Before (Legacy - Still Works)
```python
from pythonLogs import BasicLog, SizeRotatingLog, TimedRotatingLog

# Old way
basic_logger = BasicLog(level="info", name="app").init()
size_logger = SizeRotatingLog(level="debug", name="app", directory="/logs").init() 
timed_logger = TimedRotatingLog(level="warning", name="app", directory="/logs").init()
```

### After (Factory Pattern - Recommended)
```python
from pythonLogs import basic_logger, size_rotating_logger, timed_rotating_logger, LogLevel

# New way - cleaner and faster
basic_logger = basic_logger(level=LogLevel.INFO, name="app")
size_logger = size_rotating_logger(level=LogLevel.DEBUG, name="app", directory="/logs")
timed_logger = timed_rotating_logger(level=LogLevel.WARNING, name="app", directory="/logs")
```

### Benefits of Migration
- 🚀 **90% faster logger creation** with registry caching
- 🎯 **Type safety** with enum-based parameters
- 💡 **Better IDE support** with autocomplete and validation
- 🔧 **Cleaner API** without manual `.init()` calls
- 📚 **Centralized configuration** through factory pattern


# Development

### Building from Source
```shell
poetry build -f wheel
```

### Running Tests
```shell
poetry update --with test
poe tests
```

# License

Released under the [MIT License](LICENSE)

# Support

If you find this project helpful, consider supporting development:

- [GitHub Sponsor](https://github.com/sponsors/ddc)
- [ko-fi](https://ko-fi.com/ddcsta)
- [PayPal](https://www.paypal.com/ncp/payment/6G9Z78QHUD4RJ)
