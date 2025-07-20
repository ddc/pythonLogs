#!/usr/bin/env python3
"""Test the timed rotating logger implementation."""
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs.timed_rotating import TimedRotatingLog, GZipRotatorTimed
from pythonLogs import RotateWhen


class TestTimedRotatingLog:
    """Test cases for the TimedRotatingLog class."""
    
    def test_timed_rotating_log_initialization(self):
        """Test TimedRotatingLog initialization with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_timed",
                directory=temp_dir,
                level="INFO"
            )
            assert timed_log.appname == "test_timed"
            assert timed_log.directory == temp_dir
            assert timed_log.level == logging.INFO

    def test_timed_rotating_log_initialization_with_all_params(self):
        """Test TimedRotatingLog initialization with all parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                level="DEBUG",
                name="test_comprehensive",
                directory=temp_dir,
                filenames=["test1.log", "test2.log"],
                when="midnight",
                sufix="%Y%m%d",
                daystokeep=30,
                encoding="utf-8",
                datefmt="%Y-%m-%d %H:%M:%S",
                timezone="UTC",
                streamhandler=True,
                showlocation=True,
                rotateatutc=True
            )
            assert timed_log.appname == "test_comprehensive"
            assert timed_log.filenames == ["test1.log", "test2.log"]
            assert timed_log.when == "midnight"
            assert timed_log.sufix == "%Y%m%d"
            assert timed_log.daystokeep == 30
            assert timed_log.streamhandler is True
            assert timed_log.showlocation is True
            assert timed_log.rotateatutc is True

    def test_timed_rotating_log_init_method(self):
        """Test the init method of TimedRotatingLog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_init",
                directory=temp_dir,
                filenames=["test.log"]
            )
            logger = timed_log.init()
            
            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_init"
            assert len(logger.handlers) > 0

    def test_timed_rotating_log_context_manager(self):
        """Test TimedRotatingLog as context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with TimedRotatingLog(
                name="test_context",
                directory=temp_dir
            ) as logger:
                assert isinstance(logger, logging.Logger)
                assert logger.name == "test_context"
                logger.info("Test message in context")

    def test_timed_rotating_log_context_manager_cleanup(self):
        """Test context manager cleanup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_cleanup",
                directory=temp_dir
            )
            
            with timed_log as logger:
                initial_handler_count = len(logger.handlers)
                assert initial_handler_count > 0
            
            # After context exit, handlers should be cleaned up
            final_handler_count = len(logger.handlers)
            assert final_handler_count == 0

    def test_timed_rotating_log_multiple_files(self):
        """Test TimedRotatingLog with multiple log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_multiple",
                directory=temp_dir,
                filenames=["app.log", "error.log", "debug.log"]
            )
            logger = timed_log.init()
            
            # Should have handlers for each file
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
            assert len(file_handlers) == 3

    def test_timed_rotating_log_with_stream_handler(self):
        """Test TimedRotatingLog with stream handler enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_stream",
                directory=temp_dir,
                streamhandler=True
            )
            logger = timed_log.init()
            
            # Should have both file and stream handlers
            stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
            
            assert len(stream_handlers) >= 1
            assert len(file_handlers) >= 1

    def test_timed_rotating_log_when_values(self):
        """Test TimedRotatingLog with different 'when' values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_cases = [
                "midnight",
                "H",  # hourly 
                "D",  # daily
                RotateWhen.MIDNIGHT,
                RotateWhen.HOURLY,
                RotateWhen.DAILY
            ]
            
            for when_value in test_cases:
                timed_log = TimedRotatingLog(
                    name=f"test_when_{str(when_value).replace('/', '_')}",
                    directory=temp_dir,
                    when=when_value
                )
                logger = timed_log.init()
                assert logger is not None

    def test_timed_rotating_log_cleanup_logger_error_handling(self):
        """Test error handling in _cleanup_logger method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_error_cleanup",
                directory=temp_dir
            )
            logger = timed_log.init()
            
            # Add a mock handler that will raise an error on close
            mock_handler = Mock()
            mock_handler.close.side_effect = OSError("Test error")
            logger.addHandler(mock_handler)
            
            # Should handle the error gracefully
            TimedRotatingLog.cleanup_logger(logger)
            
            # Mock handler should still be removed despite the error
            assert mock_handler not in logger.handlers

    def test_timed_rotating_log_invalid_filenames(self):
        """Test TimedRotatingLog with invalid filenames parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_invalid",
                directory=temp_dir,
                filenames="invalid_string"  # Should be list or tuple
            )
            
            with pytest.raises(TypeError, match="Unable to parse filenames"):
                timed_log.init()

    def test_timed_rotating_log_actual_logging(self):
        """Test actual logging functionality with file creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = "test_actual.log"
            timed_log = TimedRotatingLog(
                name="test_actual",
                directory=temp_dir,
                filenames=[log_file],
                level="INFO"
            )
            logger = timed_log.init()
            
            # Log some messages
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            
            # Check that log file was created
            log_path = Path(temp_dir) / log_file
            assert log_path.exists()
            
            # Check log content
            log_content = log_path.read_text()
            assert "Test info message" in log_content
            assert "Test warning message" in log_content
            assert "Test error message" in log_content

    def test_timed_rotating_log_with_custom_suffix(self):
        """Test TimedRotatingLog with custom suffix."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_suffix",
                directory=temp_dir,
                sufix="%Y%m%d_%H%M%S"
            )
            logger = timed_log.init()
            
            # Check that handler has the custom suffix
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
            assert len(file_handlers) > 0
            assert file_handlers[0].suffix == "%Y%m%d_%H%M%S"

    def test_timed_rotating_log_utc_rotation(self):
        """Test TimedRotatingLog with UTC rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_utc",
                directory=temp_dir,
                rotateatutc=True
            )
            logger = timed_log.init()
            
            # Check that handler is configured for UTC
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
            assert len(file_handlers) > 0
            assert file_handlers[0].utc is True


class TestGZipRotatorTimed:
    """Test cases for the GZipRotatorTimed class."""
    
    def test_gzip_rotator_timed_initialization(self):
        """Test GZipRotatorTimed initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            assert rotator.dir == temp_dir
            assert rotator.days_to_keep == 7

    def test_gzip_rotator_timed_call_basic(self):
        """Test GZipRotatorTimed basic call functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            
            # Create source file with content
            source_file = Path(temp_dir) / "test.log"
            source_file.write_text("Test log content\nMore content\n")
            
            # Create destination filename (simulating what TimedRotatingFileHandler would do)
            dest_file = "test.log.20240101"
            
            # Process the file
            rotator(str(source_file), dest_file)
            
            # Source file should be processed (removed by gzip_file_with_sufix)
            assert not source_file.exists()
            
            # Should have created a gzipped file
            gz_files = list(Path(temp_dir).glob("*.gz"))
            assert len(gz_files) > 0

    def test_gzip_rotator_timed_suffix_extraction(self):
        """Test suffix extraction from destination filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            
            # Create source file with content
            source_file = Path(temp_dir) / "app.log"
            source_file.write_text("Test content")
            
            test_cases = [
                ("app.log.20240101", "20240101"),
                ("app.log.2024-01-01", "2024-01-01"),
                ("app.log.backup", "backup"),
                ("app.log.txt", "txt")
            ]
            
            for dest_filename, expected_suffix in test_cases:
                # Reset source file
                source_file.write_text("Test content")
                
                with patch('pythonLogs.timed_rotating.gzip_file_with_sufix') as mock_gzip:
                    rotator(str(source_file), dest_filename)
                    mock_gzip.assert_called_once_with(str(source_file), expected_suffix)

    def test_gzip_rotator_timed_with_nonexistent_source(self):
        """Test GZipRotatorTimed with non-existent source file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            
            # Call with non-existent source file
            rotator("/non/existent/file.log", "dest.log.20240101")
            
            # Should not crash and not create any files
            gz_files = list(Path(temp_dir).glob("*.gz"))
            assert len(gz_files) == 0

    @patch('pythonLogs.timed_rotating.remove_old_logs')
    def test_gzip_rotator_timed_calls_remove_old_logs(self, mock_remove_old_logs):
        """Test that GZipRotatorTimed calls remove_old_logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            
            # Create source file with content
            source_file = Path(temp_dir) / "test.log"
            source_file.write_text("Test content")
            
            rotator(str(source_file), "test.log.20240101")
            
            # Should have called remove_old_logs
            mock_remove_old_logs.assert_called_once_with(temp_dir, 7)

    @patch('pythonLogs.timed_rotating.gzip_file_with_sufix')
    def test_gzip_rotator_timed_calls_gzip_file_with_sufix(self, mock_gzip):
        """Test that GZipRotatorTimed calls gzip_file_with_sufix with correct parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            
            # Create source file with content
            source_file = Path(temp_dir) / "test.log"
            source_file.write_text("Test content")
            
            dest_file = "test.log.20240101"
            rotator(str(source_file), dest_file)
            
            # Should have called gzip_file_with_sufix with extracted suffix
            mock_gzip.assert_called_once_with(str(source_file), "20240101")

    def test_gzip_rotator_timed_integration(self):
        """Test GZipRotatorTimed integration with TimedRotatingLog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup TimedRotatingLog with GZipRotatorTimed
            timed_log = TimedRotatingLog(
                name="integration_test",
                directory=temp_dir,
                filenames=["test.log"],
                when="midnight",
                daystokeep=5
            )
            logger = timed_log.init()
            
            # Log some content
            for i in range(10):
                logger.info(f"Test message {i}")
            
            # Force handlers to flush
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Verify log file exists
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) > 0

    def test_gzip_rotator_timed_suffix_edge_cases(self):
        """Test GZipRotatorTimed with edge cases in suffix extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorTimed(temp_dir, 7)
            
            # Create source file
            source_file = Path(temp_dir) / "test.log"
            source_file.write_text("Test content")
            
            # Test edge cases
            edge_cases = [
                ("file_no_extension", ""),
                ("file.", ""),
                ("file.log.", ""),
                ("", "")
            ]
            
            for dest_filename, expected_suffix in edge_cases:
                source_file.write_text("Test content")  # Reset file
                
                with patch('pythonLogs.timed_rotating.gzip_file_with_sufix') as mock_gzip:
                    rotator(str(source_file), dest_filename)
                    if dest_filename:  # Only call if dest_filename is not empty
                        mock_gzip.assert_called_once_with(str(source_file), expected_suffix)

    def test_timed_rotating_log_double_context_manager_entry(self):
        """Test TimedRotatingLog context manager when init already called."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_double_entry",
                directory=temp_dir
            )
            
            # Call init manually first
            logger1 = timed_log.init()
            
            # Then use as context manager
            with timed_log as logger2:
                # Should return the same logger instance
                assert logger1 is logger2

    def test_timed_rotating_log_handler_configuration(self):
        """Test TimedRotatingLog handler configuration details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            timed_log = TimedRotatingLog(
                name="test_handler_config",
                directory=temp_dir,
                encoding="utf-8",
                when="H",
                daystokeep=10
                # Note: rotateatutc defaults to True from settings
            )
            logger = timed_log.init()
            
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
            assert len(file_handlers) > 0
            
            handler = file_handlers[0]
            assert handler.encoding == "utf-8"
            assert handler.when == "H"  # 'hourly' gets converted to 'H'
            assert handler.backupCount == 10
            assert handler.utc is True  # Default from settings is True
            assert isinstance(handler.rotator, GZipRotatorTimed)
