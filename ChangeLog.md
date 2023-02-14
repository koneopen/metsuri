# ChangeLog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2023-02-14

### Changed

- Project hosted in GitHub as an open source project.
- License is MIT.

### Fixed

- Tolerate timestamps that do not parse with datetime. These can occur if logger loses power during writing of log lines, causing huge year values, for example.

## [0.4.0] - 2022-05-13

### Added

- Requested log stream will be created if it did not exist already.
- Added `--version` to `log-uploader`.

## [0.3.0] - 2022-03-11

### Added

- Added `--ignore-timestamp` to `log-uploader`, which can be used to re-upload a log file even if the corresponding `*.lus` file would make the contents to be otherwise skipped. Mostly for testing.
- Added `log-generate` helper to generate current log files from arbitrary text files.
- Added `log-check` helper to iterate through a log file to check for possible errors.

### Fixed

- Allow starting the `serial-logger` without an attached USB cable. The logger will start logging immediately once the USB is attached.
- Allow starting the log-uploader with a non-existent log file with `--watch`.
- Allow using a log-stream name with common prefix that exactly matches a single file, e.g., `customer-name` and `customer-name-group`.

## [0.2.2] - 2021-10-06

### Fixed

- Fix issue with trying to upload batches larger than AWS PutLogEvents max batch size.
- Be more graceful with ill-formatted log event lines, with, e.g., missing timestamps.
- Fix issue with trying to upload batch with events spanning more than 24 hours.

## [0.2.1] - 2021-04-22

### Fixed
- Attempt to fix an issue causing logger to get stuck while logging without any indication of error. At least should see from the internal log where it gets stuck.

### Changed
- Use `rich` package for nicer progress output for `log-download`.

## [0.2.0]

### Changed
- The whole thing is now a self-contained package, allowing to be installed in a virtual environment, hopefully making setup easier in the future.

### Added
- Added `tox` setup to allow running tests against different python versions.

### Fixed
- Do not choke on non-unicode characters in log file. Catch exceptions in log file reader process and pass exceptions to main process for handling.

## [0.1.1]

### Fixed
- Fixed to work with python 3.7, the default in the current Raspbian
- Fixed USB detach/attach functionality to be lot more robust

## [0.1.0]

### Changed
- If one of `--to` or `--from` is passed alongside `--interval`, the value of `--interval` is used to determine the other end of the time period. Behavior stays the same if both `--to` and `--from` are provided; in that case `--interval` is ignored.

### Added
- Added `--verbose` option to `serial_logger.py` and `log_uploader.py`.
- `log_download.py list-streams` command to show possible log streams to download.
- Added this changelog.

### Fixed
- Open files with 'utf-8' codec on Windows with `log_download.py` to better support Unicode input.
- In case log is written fairly seldom, timeout and send smaller batches even if log file has not been appended.
