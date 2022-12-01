"""
Usage: serial-logger [options] PORT LOGFILE

Options:
  --no-stdout          Disable echoing to stdout.
  --rotate-every INTERVAL
                       Rotate logs every INTERVAL time period. Specify as
                       days (d), hours (h), minutes (m) and seconds (s).
                       For example, 1d12h30s. [default: 1d]
  --retain NUM         Retain this many rotated logs. [default: 5]
  --verbose            Enable verbose logging (internal to the logger).
"""
import serial
import docopt
import os
import datetime
import logging
from typing import Optional
from metsuri.log_download import parse_interval
from metsuri.log_uploader import parse_log_line
import time

logger = logging.getLogger(__name__)


class LogFile:
    def __init__(self,
                 filename: str,
                 rotation_interval: Optional[datetime.timedelta] = None,
                 num_retained_logfiles: Optional[int] = None,
                 copy_to_stdout: bool = False):
        self.filename = filename
        self.rotation_interval = rotation_interval
        self.num_retained_logfiles = num_retained_logfiles
        self.file = open(filename, "a+")

        self.rotation_timestamp = self._get_rotation_timestamp()
        self.to_stdout = copy_to_stdout
        self._write_line_internal("**** started logging ****")

    def _get_rotation_timestamp(self) -> datetime.datetime:
        """
        Obtain accurate timestamp of the last rotation from the beginning of
        an existing log file.

        :return: ts
        """
        cur_pos = self.file.tell()
        if cur_pos > 0:
            self.file.seek(0)
            line = self.file.readline()
            ts, _ = parse_log_line(line)
            self.file.seek(cur_pos)
        else:
            ts = datetime.datetime.now(datetime.timezone.utc)
        return ts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._write_line_internal("**** stopped logging ****")
        self.file.close()

    @staticmethod
    def _parse_int(string):
        try:
            return int(string)
        except ValueError:
            return None

    def rotate_logs(self):
        self.file.close()
        log_dir, base = os.path.split(self.filename)
        log_dir = log_dir if log_dir else "."
        to_rotate = filter(
            None,
            map(lambda fn: self._parse_int(fn[len(base + "."):]),
                filter(lambda fn: fn.startswith(base + "."),
                       os.listdir(log_dir))))

        for suffix_int in sorted(to_rotate, reverse=True):
            filename = f"{self.filename}.{suffix_int}"
            if suffix_int >= self.num_retained_logfiles:
                os.remove(filename)
            else:
                os.rename(filename, f"{self.filename}.{suffix_int + 1}")

        os.rename(self.filename, f"{self.filename}.1")
        self.rotation_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self.file = open(self.filename, "w")

    def _write_line_internal(self, line):
        formatted = self.format_line(line)
        if self.to_stdout:
            print(formatted, end='')
        self.file.write(formatted)
        self.file.flush()
        return formatted

    def write_line(self, line):
        if self.rotation_interval is not None:
            if datetime.datetime.now(datetime.timezone.utc) - self.rotation_timestamp >= self.rotation_interval:
                self.rotate_logs()
        return self._write_line_internal(line)

    @classmethod
    def timestamp(cls):
        return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')

    @classmethod
    def format_line(cls, line):
        return f"{cls.timestamp()} {line.rstrip()}\n"


def collect_serial_debug(port, logfile, disable_stdout=False):
    disconnected = True
    try:
        while True:
            try:
                if disconnected:
                    ser = serial.Serial(port=port, baudrate=115200,
                                        timeout=None)
                    logfile.write_line("**** USB connected ****")
                    disconnected = False
                line = ser.readline()
            except serial.SerialException as e:
                # most likely USB has been disconnected. wait a bit and retry.
                if not disconnected:
                    try:
                        # Try to avoid case where the USB device changes path
                        ser.close()
                    except serial.SerialException as extra:
                        pass
                    logfile.write_line("**** USB disconnected ****")
                    disconnected = True
                    logger.error("USB disconnected with error", exc_info=e)
                else:
                    logger.info("Got error, USB already disconnected", exc_info=e)
                time.sleep(1)
                continue
            logfile.write_line(line.decode('ascii', errors='replace'))
    except StopIteration:
        pass


def main():
    opts = docopt.docopt(__doc__)
    if opts['--verbose']:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level,
                        format='%(asctime)s [%(levelname)s] %('
                               'filename)s:%(lineno)s %(funcName)s %('
                               'message)s',
                        datefmt="%Y-%m-%dT%H:%M:%S%z"
                        )
    with LogFile(opts['LOGFILE'],
                 rotation_interval=parse_interval(opts['--rotate-every']),
                 num_retained_logfiles=int(opts['--retain']),
                 copy_to_stdout=not bool(opts['--no-stdout'])) as logfile:
        collect_serial_debug(opts['PORT'], logfile, opts['--no-stdout'])


if __name__ == '__main__':
    main()
