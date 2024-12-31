# -*- encoding: utf-8 -*-
import gzip
import os
import tempfile
from datetime import datetime
from pythonLogs import BasicLog, SizeRotatingLog, TimedRotatingLog
from pythonLogs.log_utils import delete_file


class TestLogs:
    @classmethod
    def setup_class(cls):
        cls.directory = tempfile.gettempdir()
        cls.filenames = ("testA.log", "testB.log", "testC.log")

    @classmethod
    def teardown_class(cls):
        for filename in cls.filenames:
            file_path = str(os.path.join(cls.directory, filename))
            if os.path.isfile(file_path):
                delete_file(file_path)

    def test_basic_log(self, caplog):
        level = "INFO"
        log = BasicLog(
            level=level,
            name="app",
            encoding="UTF-8",
            datefmt="%Y-%m-%dT%H:%M:%S",
            timezone="UTC",
            showlocation=False,
        ).init()
        log.info("test_basic_log")
        assert level in caplog.text
        assert "test_basic_log" in caplog.text

    def test_size_rotating_log(self, caplog):
        # creating files with 2MB
        for filename in self.filenames:
            file_path = str(os.path.join(self.directory, filename))
            with open(file_path, "wb") as f:
                f.seek((2 * 1024 * 1024) - 1)
                f.write(b"\0")

        # creating an exisiting gz file to force rotation number
        fname_no_ext = self.filenames[0].split(".")[0]
        existing_gz_filename = f"{fname_no_ext}_1.log.gz"
        existing_gz_file_path = str(os.path.join(self.directory, existing_gz_filename))
        with gzip.open(existing_gz_file_path, "wb") as fout:
            fout.write(b"")
        new_gz_filename_rotated = f"{fname_no_ext}_2.log.gz"
        new_gz_filepath_rotated = str(os.path.join(self.directory, new_gz_filename_rotated))

        level = "INFO"
        log = SizeRotatingLog(
            level=level,
            name="app",
            directory=self.directory,
            filenames=self.filenames,
            maxmbytes=1,
            daystokeep=7,
            encoding="UTF-8",
            datefmt="%Y-%m-%dT%H:%M:%S",
            timezone="UTC",
            streamhandler=True,
            showlocation=False,
        ).init()
        log.info("test_size_rotating_log")
        assert level in caplog.text
        assert "test_size_rotating_log" in caplog.text

        # delete .gz files
        assert os.path.isfile(new_gz_filepath_rotated) == True
        delete_file(new_gz_filepath_rotated)
        for filename in self.filenames:
            gz_file_name = f"{os.path.splitext(filename)[0]}_1.log.gz"
            gz_file_path = os.path.join(tempfile.gettempdir(), gz_file_name)
            assert os.path.isfile(gz_file_path) == True
            delete_file(gz_file_path)

    def test_timed_rotating_log(self, caplog):
        level = "INFO"
        year = 2020
        month = 10
        day = 10

        log = TimedRotatingLog(
            level=level,
            name="app",
            directory=self.directory,
            filenames=self.filenames,
            when="midnight",
            sufix="%Y%m%d",
            daystokeep=7,
            encoding="UTF-8",
            datefmt="%Y-%m-%dT%H:%M:%S",
            timezone="UTC",
            streamhandler=True,
            showlocation=False,
        ).init()
        log.info("start_test_timed_rotating_log")
        assert level in caplog.text
        assert "start_test_timed_rotating_log" in caplog.text

        # change files datetime
        epoch_times = datetime(year, month, day, 1, 1, 1).timestamp()
        for filename in self.filenames:
            file_path = str(os.path.join(self.directory, filename))
            os.utime(file_path, (epoch_times, epoch_times))

        log = TimedRotatingLog(
            level=level,
            name="app",
            directory=self.directory,
            filenames=self.filenames,
            when="midnight",
            sufix="%Y%m%d",
            daystokeep=7,
            encoding="UTF-8",
            datefmt="%Y-%m-%dT%H:%M:%S",
            timezone="UTC",
            streamhandler=True,
            showlocation=False,
        ).init()
        log.info("end_test_timed_rotating_log")
        assert level in caplog.text
        assert "end_test_timed_rotating_log" in caplog.text

        # delete test.gz files
        for filename in self.filenames:
            gz_file = f"{os.path.splitext(filename)[0]}_{year}{month}{day}"
            gz_file_name = f"{gz_file}.log.gz"
            gz_file_path = os.path.join(tempfile.gettempdir(), gz_file_name)
            assert os.path.exists(gz_file_path)
            delete_file(str(gz_file_path))
