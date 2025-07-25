#!/usr/bin/env python3
"""Test the size rotating logger implementation."""
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pythonLogs.size_rotating import SizeRotatingLog, GZipRotatorSize


class TestSizeRotatingLog:
    """Test cases for the SizeRotatingLog class."""
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_initialization(self):
        """Test SizeRotatingLog initialization with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_size",
                directory=temp_dir,
                level="INFO"
            )
            assert size_log.appname == "test_size"
            assert size_log.directory == temp_dir
            assert size_log.level == logging.INFO

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_initialization_with_all_params(self):
        """Test SizeRotatingLog initialization with all parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                level="DEBUG",
                name="test_comprehensive",
                directory=temp_dir,
                filenames=["test1.log", "test2.log"],
                maxmbytes=10,
                daystokeep=30,
                encoding="utf-8",
                datefmt="%Y-%m-%d %H:%M:%S",
                timezone="UTC",
                streamhandler=True,
                showlocation=True
            )
            assert size_log.appname == "test_comprehensive"
            assert size_log.filenames == ["test1.log", "test2.log"]
            assert size_log.maxmbytes == 10
            assert size_log.daystokeep == 30
            assert size_log.streamhandler is True
            assert size_log.showlocation is True

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_init_method(self):
        """Test the init method of SizeRotatingLog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_init",
                directory=temp_dir,
                filenames=["test.log"]
            )
            logger = size_log.init()
            
            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_init"
            assert len(logger.handlers) > 0

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_context_manager(self):
        """Test SizeRotatingLog as context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with SizeRotatingLog(
                name="test_context",
                directory=temp_dir
            ) as logger:
                assert isinstance(logger, logging.Logger)
                assert logger.name == "test_context"
                logger.info("Test message in context")

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_context_manager_cleanup(self):
        """Test context manager cleanup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_cleanup",
                directory=temp_dir
            )
            
            with size_log as logger:
                initial_handler_count = len(logger.handlers)
                assert initial_handler_count > 0
            
            # After context exit, handlers should be cleaned up
            final_handler_count = len(logger.handlers)
            assert final_handler_count == 0

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_multiple_files(self):
        """Test SizeRotatingLog with multiple log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_multiple",
                directory=temp_dir,
                filenames=["app.log", "error.log", "debug.log"]
            )
            logger = size_log.init()
            
            # Should have handlers for each file (plus stream handler if enabled)
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
            assert len(file_handlers) == 3

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_with_stream_handler(self):
        """Test SizeRotatingLog with stream handler enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_stream",
                directory=temp_dir,
                streamhandler=True
            )
            logger = size_log.init()
            
            # Should have both file and stream handlers
            stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
            
            assert len(stream_handlers) >= 1
            assert len(file_handlers) >= 1

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_cleanup_logger_error_handling(self):
        """Test error handling in _cleanup_logger method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_error_cleanup",
                directory=temp_dir
            )
            logger = size_log.init()
            
            # Add a mock handler that will raise an error on close
            mock_handler = Mock()
            mock_handler.close.side_effect = OSError("Test error")
            logger.addHandler(mock_handler)
            
            # Should handle the error gracefully
            SizeRotatingLog.cleanup_logger(logger)
            
            # Mock handler should still be removed despite the error
            assert mock_handler not in logger.handlers

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_invalid_filenames(self):
        """Test SizeRotatingLog with invalid filenames' parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            size_log = SizeRotatingLog(
                name="test_invalid",
                directory=temp_dir,
                filenames="invalid_string"  # Should be list or tuple
            )
            
            with pytest.raises(TypeError, match="Unable to parse filenames"):
                size_log.init()

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_size_rotating_log_actual_logging(self):
        """Test actual logging functionality with file creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = "test_actual.log"
            size_log = SizeRotatingLog(
                name="test_actual",
                directory=temp_dir,
                filenames=[log_file],
                level="INFO"
            )
            logger = size_log.init()
            
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


class TestGZipRotatorSize:
    """Test cases for the GZipRotatorSize class."""
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_initialization(self):
        """Test GZipRotatorSize initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorSize(temp_dir, 7)
            assert rotator.directory == temp_dir
            assert rotator.daystokeep == 7

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_call_with_empty_file(self):
        """Test GZipRotatorSize with empty source file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorSize(temp_dir, 7)
            
            # Create empty source file
            source_file = Path(temp_dir) / "empty.log"
            source_file.touch()
            
            # Should not process empty files
            rotator(str(source_file), "dest.log")
            
            # Source file should still exist (not processed)
            assert source_file.exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_call_with_content(self):
        """Test GZipRotatorSize with file containing content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorSize(temp_dir, 7)
            
            # Create source file with content
            source_file = Path(temp_dir) / "content.log"
            source_file.write_text("Test log content\nMore content\n")
            
            # Process the file
            rotator(str(source_file), "dest.log")
            
            # Source file should be processed (removed)
            assert not source_file.exists()
            
            # Should have created a gzipped file
            gz_files = list(Path(temp_dir).glob("*.gz"))
            assert len(gz_files) > 0

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_get_new_file_number(self):
        """Test _get_new_file_number method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some existing numbered log files
            (Path(temp_dir) / "test_1.log.gz").touch()
            (Path(temp_dir) / "test_3.log.gz").touch()
            (Path(temp_dir) / "test_5.log.gz").touch()
            (Path(temp_dir) / "other_2.log.gz").touch()  # Different filename
            
            # Should return 6 (max + 1 for "test" files)
            new_number = GZipRotatorSize._get_new_file_number(temp_dir, "test")
            assert new_number == 6

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_get_new_file_number_no_existing_files(self):
        """Test _get_new_file_number with no existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_number = GZipRotatorSize._get_new_file_number(temp_dir, "test")
            assert new_number == 1

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_get_new_file_number_with_special_chars(self):
        """Test _get_new_file_number with special characters in filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with special characters that need escaping
            filename = "test-app[special]"
            (Path(temp_dir) / f"{filename}_1.log.gz").touch()
            (Path(temp_dir) / f"{filename}_2.log.gz").touch()
            
            new_number = GZipRotatorSize._get_new_file_number(temp_dir, filename)
            assert new_number == 3

    def test_gzip_rotator_size_error_handling(self):
        """Test GZipRotatorSize error handling for directory access."""
        # Test with non-existent directory
        rotator = GZipRotatorSize("/non/existent/directory", 7)
        
        # Should handle OSError gracefully and return 1
        new_number = GZipRotatorSize._get_new_file_number("/non/existent/directory", "test")
        assert new_number == 1

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_call_with_nonexistent_source(self):
        """Test GZipRotatorSize with non-existent source file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorSize(temp_dir, 7)
            
            # Call with non-existent source file
            rotator("/non/existent/file.log", "dest.log")
            
            # Should not crash and not create any files
            gz_files = list(Path(temp_dir).glob("*.gz"))
            assert len(gz_files) == 0

    @patch('pythonLogs.size_rotating.remove_old_logs')
    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_calls_remove_old_logs(self, mock_remove_old_logs):
        """Test that GZipRotatorSize calls remove_old_logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            rotator = GZipRotatorSize(temp_dir, 7)
            
            # Create source file with content
            source_file = Path(temp_dir) / "test.log"
            source_file.write_text("Test content")
            
            rotator(str(source_file), "dest.log")
            
            # Should have called remove_old_logs
            mock_remove_old_logs.assert_called_once_with(temp_dir, 7)

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issues with TemporaryDirectory - see equivalent Windows-specific test file")
    def test_gzip_rotator_size_integration(self):
        """Test GZipRotatorSize integration with actual rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup SizeRotatingLog with GZipRotatorSize
            size_log = SizeRotatingLog(
                name="integration_test",
                directory=temp_dir,
                filenames=["test.log"],
                maxmbytes=1,  # Small size to trigger rotation
                daystokeep=5
            )
            logger = size_log.init()
            
            # Log enough content to potentially trigger rotation
            large_message = "A" * 1000  # 1KB message
            for i in range(50):  # 50KB total
                logger.info(f"Message {i}: {large_message}")
            
            # Force handlers to flush
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Verify log file exists
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) > 0
