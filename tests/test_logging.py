from freezegun import freeze_time
import os
import datetime
from metsuri.serial_logger import LogFile, collect_serial_debug
from metsuri.log_uploader import get_log_entries, get_timestamp
import unittest.mock as mock
import pytest
import serial


def test_logfile(log_file_name):
    assert not os.path.exists(log_file_name)
    with LogFile(log_file_name):
        pass
    lines = open(log_file_name).readlines()
    assert len(lines) == 2
    assert "started" in lines[0]
    assert "stopped" in lines[1]


@pytest.mark.xfail
def test_freezegun():
    with freeze_time(datetime.datetime(year=2020, month=1, day=1,
                                       microsecond=400000),
                     tz_offset=4) as frozen:
        dt1 = datetime.datetime.now(tz=datetime.timezone.utc)
        dt2 = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        assert dt1 == dt2


def test_timestamps(log_file_name):
    with freeze_time(datetime.datetime(year=2020, month=1, day=1,
                                       microsecond=400000)) as frozen:

        with LogFile(log_file_name) as log:
            frozen.tick()
            log.write_line("foo")
            frozen.tick()
            log.write_line("bar")
    lines = open(log_file_name).readlines()
    assert len(lines) == 4
    assert "foo" in lines[1]
    assert "bar" in lines[2]
    assert lines[1].startswith("2020-01-01T00:00:01.400+00:00")

    entries = list(get_log_entries(log_file_name))
    assert len(entries) == 4
    assert entries[1][0] == datetime.datetime(year=2020, month=1, day=1,
                                              hour=0, second=1,
                                              microsecond=400000, tzinfo=datetime.timezone.utc)


def test_upgraded_logfile(log_file_name):
    log_data = """\
    2020-01-01 00:00:01.400+00:00 foo
    [2020-01-01 00:00:01.500+00:00]: bar
    [2020-01-01T00:00:01.600+00:00]: qux
    2020-01-01T00:00:01.600: zap
    2020-01-01T00:00:01.700 zappa"""
    with open(log_file_name, "w") as fp:
        fp.write(log_data)
        fp.close()

    with freeze_time(datetime.datetime(year=2020, month=1, day=1,
                                       microsecond=400000), tz_offset=5) as frozen:
        entries = list(get_log_entries(log_file_name))

    assert len(entries) == 5
    assert "foo" in entries[0].message

    local_tzinfo = datetime.datetime(year=2020, month=1, day=1).astimezone().tzinfo

    assert entries[3][0] == datetime.datetime(year=2020, month=1, day=1,
                                              hour=0, minute=0, second=1,
                                              microsecond=600000,
                                              tzinfo=local_tzinfo)
    assert entries[4][0] == datetime.datetime(year=2020, month=1, day=1,
                                              hour=0, minute=0, second=1,
                                              microsecond=700000,
                                              tzinfo=local_tzinfo)


def test_upgraded_logfile_and_timestamp(log_file_name):
    log_data = """\
    2020-01-01 00:00:01.400+00:00 foo
    [2020-01-01 00:00:01.500+00:00]: bar
    [2020-01-01T00:00:01.550+00:00]: qux
    2020-01-01T04:00:01.600: zap
    2020-01-01T04:00:01.700 zappa dappa"""
    with open(log_file_name, "w") as fp:
        fp.write(log_data)

    entries = list(get_log_entries(log_file_name))

    assert [e[1] for e in entries] == ["foo", "bar", "qux", "zap",
                                       "zappa dappa"]

    with open(log_file_name + ".lus", "w") as fp:
        fp.write("2020-01-01T03:00:01.599")

    with freeze_time(datetime.datetime(year=2020, month=1, day=1,
                                       microsecond=400000)):
        entries = list(get_log_entries(log_file_name))

    assert len(entries) == 2
    assert [e[1] for e in entries] == ["zap", "zappa dappa"]

    local_tzinfo = datetime.datetime(year=2020, month=1, day=1).astimezone().tzinfo

    assert entries[0][0] == datetime.datetime(year=2020, month=1, day=1,
                                              hour=4, minute=0, second=1,
                                              microsecond=600000,
                                              tzinfo=local_tzinfo)
    assert entries[1][0] == datetime.datetime(year=2020, month=1, day=1,
                                              hour=4, minute=0, second=1,
                                              microsecond=700000,
                                              tzinfo=local_tzinfo)


def test_get_timestamp(log_file_name):
    with open(log_file_name + ".lus", "w") as fp:
        fp.write("2020-01-01T03:00:01.599+00:00")
    ts = get_timestamp(log_file_name)
    assert ts == datetime.datetime(year=2020, month=1, day=1,
                                   hour=3, minute=0, second=1,
                                   microsecond=599000,
                                   tzinfo=datetime.timezone.utc)


def test_write_line_returns_written(log_file_name):
    with freeze_time(datetime.datetime(year=2020, month=1, day=1),
                     tz_offset=3) as frozen:
        with LogFile(log_file_name) as log:
            written = log.write_line("foo")
            assert "2020-01-01T03:00:00" in written
            assert "foo" in written


def test_linefeeds(log_file_name):
    with LogFile(log_file_name) as log:
        log.write_line("foo\n")

    lines = list(map(lambda l: l.strip(), open(log_file_name).readlines()))
    assert all(lines)
    assert len(lines) == 3


def test_flushing(log_file_name):
    with mock.patch('metsuri.serial_logger.open', create=True) as mock_open:
        mock_open.return_value.tell.return_value = 0

        with LogFile(log_file_name) as log:
            # should be called when opening the log.
            mock_open.return_value.flush.assert_called()
            mock_open.return_value.flush.reset_mock()
            mock_open.return_value.flush.assert_not_called()

            log.write_line("foo\n")
            mock_open.return_value.flush.assert_called()


def test_closing(log_file_name):
    with mock.patch('metsuri.serial_logger.open', create=True) as mock_open:
        mock_open.return_value.tell.return_value = 0

        with LogFile(log_file_name) as log:
            log.write_line("foo\n")
            mock_open.return_value.close.assert_not_called()
        mock_open.return_value.close.assert_called_once()


def test_serial_logging(log_file_name):
    with mock.patch('serial.Serial') as MockSerial:
        MockSerial.return_value.readline.side_effect = \
            "foo\n".encode("ascii"), "bar\n".encode("ascii"), \
            "baz\n".encode("ascii"), \
            StopIteration("foo")
        with LogFile(log_file_name) as log:
            collect_serial_debug("/dev/ttyUSB0", log, True)


def test_serial_logging_survives_disconnecting_usb(log_file_name):
    with mock.patch('serial.Serial') as MockSerial, \
            mock.patch('time.sleep') as mock_sleep:
        MockSerial.name = "class"
        initial_serial = mock.MagicMock()
        initial_serial.name = "initial"
        initial_serial.readline = mock.MagicMock(side_effect=[
            "foo\n".encode("ascii"),
            serial.SerialException("foo"),
            StopIteration("foo")
        ])
        last_serial = mock.MagicMock()
        last_serial.name = "last"
        last_serial.readline.side_effect = [
            "bar\n".encode("ascii"),
            StopIteration("foo")
        ]
        MockSerial.side_effect = [initial_serial,
                                  serial.SerialException("fail1"),
                                  serial.SerialException("fail2"),
                                  serial.SerialException("fail3"),
                                  last_serial]
        with LogFile(log_file_name) as log:
            collect_serial_debug("/dev/ttyUSB0", log)
            mock_sleep.assert_called()
        lines = open(log_file_name).readlines()
        # both "foo" and "bar" need to be found
        assert "foo" in lines[2]
        # Log event for disconnection and reconnection emitted
        assert "USB disconnected" in lines[3]
        assert len(list(filter(lambda xx: "USB disconnected" in xx, lines))) == 1
        assert "USB connected" in lines[4]
        assert "bar" in lines[5]


def test_serial_logging_with_stdout(log_file_name):
    with mock.patch('serial.Serial') as MockSerial, \
            mock.patch('metsuri.serial_logger.print') as mock_print:
        MockSerial.return_value.readline.side_effect = \
            "foo\n".encode("ascii"), "bar\n".encode("ascii"), \
            "baz\n".encode("ascii"), StopIteration("foo")
        with LogFile(log_file_name, copy_to_stdout=True) as log:
            collect_serial_debug("/dev/ttyUSB0", log)
        print_arg = mock_print.call_args_list[1][0][0]
        assert isinstance(print_arg, str)
        assert "USB connected" in print_arg
        print_arg = mock_print.call_args_list[2][0][0]
        assert "foo" in print_arg


def test_log_rotation(log_file_name):
    with freeze_time(datetime.datetime(year=2020, month=1, day=1),
                     tz_offset=3) as frozen:
        open(log_file_name + ".foo", "w").write("foo")
        with LogFile(log_file_name, rotation_interval=datetime.timedelta(days=1)) as log:
            log.write_line("foo 1")
            frozen.tick(delta=datetime.timedelta(hours=12))
            log.write_line("foo 2")
            frozen.tick(delta=datetime.timedelta(hours=13))
            log.write_line("foo 3")
            log.write_line("foo 4")
            log.write_line("foo 5")
    assert os.path.exists(log_file_name)
    assert "foo 2" not in open(log_file_name).read()
    # log should have been rotated.
    assert os.path.exists(log_file_name + ".1")
    assert not os.path.exists(log_file_name + ".2")


def test_log_rotation_get_timestamp_on_reopen(log_file_name):
    with freeze_time(datetime.datetime(year=2020, month=1, day=1),
                     tz_offset=3) as frozen:
        open(log_file_name + ".foo", "w").write("foo")
        with LogFile(log_file_name, rotation_interval=datetime.timedelta(days=1)) as log:
            log.write_line("foo 1")
            frozen.tick(delta=datetime.timedelta(hours=12))
            log.write_line("foo 2")
            frozen.tick(delta=datetime.timedelta(hours=11))
            log.write_line("foo 3")

        assert not os.path.exists(log_file_name + ".1")
        with LogFile(log_file_name, rotation_interval=datetime.timedelta(days=1)) as log:
            frozen.tick(delta=datetime.timedelta(minutes=59))
            log.write_line("foo 4")
            assert not os.path.exists(log_file_name + ".1")
            frozen.tick(delta=datetime.timedelta(minutes=2))
            log.write_line("foo 5")

            assert os.path.exists(log_file_name + ".1")


def test_log_rotation_num_retained(log_file_name):
    with freeze_time(datetime.datetime(year=2020, month=1, day=1),
                     tz_offset=3) as frozen:
        with LogFile(log_file_name, rotation_interval=datetime.timedelta(hours=1),
                     num_retained_logfiles=3) as log:
            for ii in range(10):
                frozen.tick(delta=datetime.timedelta(minutes=30))
                log.write_line(f"foo {ii}")
    assert os.path.exists(log_file_name)
    assert "foo 9" in open(log_file_name).read()
    # log should have been rotated.
    assert os.path.exists(log_file_name + ".3")
    assert not os.path.exists(log_file_name + ".4")

