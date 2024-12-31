# -*- encoding: utf-8 -*-
import pytest
import tempfile
import os
from pythonLogs import log_utils
import logging


class TestLogUtils:
    @classmethod
    def setup_class(cls):
        """setup_class"""
        pass

    @classmethod
    def teardown_class(cls):
        """teardown_class"""
        pass

    def test_get_stream_handler(self):
        level = log_utils.get_level("DEBUG")
        _, formatter = log_utils.get_logger_and_formatter("appname", "%Y-%m-%dT%H:%M:%S", False, "UTC")
        stream_hdlr = log_utils.get_stream_handler(level, formatter)
        assert isinstance(stream_hdlr, logging.StreamHandler)

    def test_check_filename_instance(self):
        filenames = "test1.log"
        with pytest.raises(TypeError) as exec_info:
            log_utils.check_filename_instance(filenames)
        assert type(exec_info.value) is TypeError
        assert filenames in str(exec_info.value)
        assert "Unable to parse filenames" in str(exec_info.value)

    def test_check_directory_permissions(self):
        # test permission error on access
        directory = os.path.join(tempfile.gettempdir(), "test")
        os.makedirs(directory, mode=0o444, exist_ok=True)
        assert os.path.exists(directory) == True
        with pytest.raises(PermissionError) as exec_info:
            log_utils.check_directory_permissions(directory)
        assert type(exec_info.value) is PermissionError
        assert "Unable to access directory" in str(exec_info.value)
        log_utils.delete_file(directory)
        assert os.path.exists(directory) == False

        # test permission error on creation
        directory = "/non-existent-directory"
        with pytest.raises(PermissionError) as exec_info:
            log_utils.check_directory_permissions(directory)
        assert type(exec_info.value) is PermissionError
        assert "Unable to create directory" in str(exec_info.value)

    def test_remove_old_logs(self):
        directory = os.path.join(tempfile.gettempdir(), "test")
        os.makedirs(directory, mode=0o755, exist_ok=True)
        assert os.path.exists(directory) == True
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".gz")
        log_utils.remove_old_logs(directory, 1)
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == False
        log_utils.delete_file(directory)
        assert os.path.exists(directory) == False

    def test_delete_file(self):
        directory = tempfile.gettempdir()
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".log")
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == True
        log_utils.delete_file(file_path)
        assert os.path.isfile(file_path) == False

    def test_is_older_than_x_days(self):
        directory = tempfile.gettempdir()
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".log")
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == True

        result = log_utils.is_older_than_x_days(file_path, 1)
        assert result == True

        result = log_utils.is_older_than_x_days(file_path, 5)
        assert result == False

        log_utils.delete_file(file_path)
        assert os.path.isfile(file_path) == False

    def test_get_level(self):
        level = log_utils.get_level(11111111)
        assert level == logging.INFO

        level = log_utils.get_level("")
        assert level == logging.INFO

        level = log_utils.get_level("INFO")
        assert level == logging.INFO

        level = log_utils.get_level("DEBUG")
        assert level == logging.DEBUG

        level = log_utils.get_level("WARNING")
        assert level == logging.WARNING

        level = log_utils.get_level("ERROR")
        assert level == logging.ERROR

        level = log_utils.get_level("CRITICAL")
        assert level == logging.CRITICAL

    def test_get_log_path(self):
        directory = tempfile.gettempdir()
        filename = "test1.log"
        log_utils.get_log_path(directory, filename)

        directory = "/non-existent-directory"
        filename = "test2.log"
        with pytest.raises(FileNotFoundError) as exec_info:
            log_utils.get_log_path(directory, filename)
        assert type(exec_info.value) is FileNotFoundError
        assert "Unable to open log file for writing" in str(exec_info.value)

        directory = tempfile.gettempdir()
        filename = "test3.log"
        file_path = str(os.path.join(directory, filename))
        with open(file_path, "w") as file:
            file.write("test")
        assert os.path.isfile(file_path) == True
        os.chmod(file_path, 0o111)
        with pytest.raises(PermissionError) as exec_info:
            log_utils.get_log_path(directory, filename)
        assert type(exec_info.value) is PermissionError
        assert "Unable to open log file for writing" in str(exec_info.value)
        log_utils.delete_file(file_path)
        assert os.path.isfile(file_path) == False

    def test_get_format(self):
        show_location = True
        name = "test1"
        timezone = "UTC"
        result = log_utils.get_format(show_location, name, timezone)
        assert result == (
            f"[%(asctime)s.%(msecs)03d+0000]:[%(levelname)s]:[{name}]:"
            "[%(filename)s:%(funcName)s:%(lineno)d]:%(message)s"
        )

        show_location = False
        name = "test2"
        timezone = "America/Los_Angeles"
        result = log_utils.get_format(show_location, name, timezone)
        assert result == f"[%(asctime)s.%(msecs)03d-0800]:[%(levelname)s]:[{name}]:%(message)s"

        show_location = False
        name = "test3"
        timezone = "Australia/Queensland"
        result = log_utils.get_format(show_location, name, timezone)
        assert result == f"[%(asctime)s.%(msecs)03d+1000]:[%(levelname)s]:[{name}]:%(message)s"

    def test_gzip_file_with_sufix(self):
        directory = tempfile.gettempdir()
        tmpfilewrapper = tempfile.NamedTemporaryFile(dir=directory, suffix=".log")
        file_path = tmpfilewrapper.name
        assert os.path.isfile(file_path) == True
        sufix = "test1"
        result = log_utils.gzip_file_with_sufix(file_path, sufix)
        file_path_no_suffix = file_path.split(".")[0]
        assert result == f"{file_path_no_suffix}_{sufix}.log.gz"
        log_utils.delete_file(result)
        assert os.path.isfile(result) == False

        # test a non-existent file
        file_path = "/non-existent-directory/test2.log"
        sufix = "test2"
        result = log_utils.gzip_file_with_sufix(file_path, sufix)
        assert result is None

    def test_get_timezone_function(self):
        timezone = "UTC"
        result = log_utils.get_timezone_function(timezone)
        assert result.__name__ == "gmtime"

        timezone = "localtime"
        result = log_utils.get_timezone_function(timezone)
        assert result.__name__ == "localtime"

        timezone = "America/Los_Angeles"
        result = log_utils.get_timezone_function(timezone)
        assert result.__name__ == "<lambda>"
