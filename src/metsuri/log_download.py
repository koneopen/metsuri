"""
Usage: log-download [options] LOG_GROUP STREAM_PREFIX OUTPUT
       log-download list-streams [options] LOG_GROUP [STREAM_PREFIX]

Export log streams with prefix STREAM_PREFIX from LOG_GROUP.

Command list-streams can be used to enumerate possible log-streams.

The logs are downloaded to the OUTPUT directory, which is created if it
does not exist.

Time period handling:

The `--from`, `--to` and `--interval` specify the period from which the
logs are dumped. If both `--from` and `--to` are specified, those will be
used and `--interval` will be ignored. If either `--to` or `--from` is
specified along with `--interval`, the period will be calculated from the
values. If only `--from` is specified, logs are dumped from that time to
current time. If only `--to` is specified, a default `--interval` of "1d"
will be used.

If neither --from or --to is specified, a default value for --to is taken to
be the current time and result is calculated as above depending on --interval.

Options:
  --interval INTERVAL  Use INTERVAL as the time window.
  --from TIME          Use TIME as the beginning of the window, specified in
                       ISO-8601 format.
  --to TIME            Use TIME as the end of the window, specified in
                       ISO-8601 format. If unspecified, use current time.
  --verbose            Enable verbose logging.
"""
import boto3
import logging
import docopt
import datetime
import os
import re
from rich.logging import RichHandler
import rich.progress as rp


logger = logging.getLogger(__name__)


def get_streams(client, log_group: str, stream_prefix: str):
    params = {}
    if stream_prefix:
        params['logStreamNamePrefix'] = stream_prefix
    # max 50 stream at this time
    response = client.describe_log_streams(
        logGroupName=log_group,
        **params
    )
    streams = [stream['logStreamName'] for stream in response['logStreams']]
    return streams


def log_download(client, log_group: str, stream_prefix: str, output: str,
                 from_time: datetime.datetime, to_time: datetime.datetime,
                 progress):

    streams = get_streams(client, log_group, stream_prefix)
    if not streams:
        print(f"No streams found from log group \"{log_group}\" with "
              f"prefix \"{stream_prefix}\"")
        return

    progress.console.log("Downloading " + ', '.join(streams))

    event_params = {'startTime': int(from_time.timestamp() * 1000),
                    'endTime': int(to_time.timestamp() * 1000)}

    start = event_params['startTime']
    total = event_params['endTime'] - start

    # If stream is empty, file should not be created
    for stream in progress.track(streams, description="All streams"):
        current_token = ""
        next_token = None

        current_params = event_params.copy()
        task = progress.add_task(f" {stream}", total=total)
        output_file = None
        while current_token != next_token:
            if next_token:
                current_params['nextToken'] = next_token
            response = client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream,
                startFromHead=True,
                **current_params)
            current_token = next_token

            for ev in response['events']:
                if output_file is None:
                    os.makedirs(output, exist_ok=True)
                    output_file = open(os.path.join(output, stream), "w",
                                       encoding="utf-8")
                timestamp = datetime.datetime.fromtimestamp(
                    ev['timestamp'] / 1000,
                    tz=datetime.timezone.utc).astimezone().isoformat(
                    sep=' ',
                    timespec='milliseconds')
                print(f"{timestamp} {ev['message']}", file=output_file)
                progress.update(task, completed=ev['timestamp'] - start)
            next_token = response['nextForwardToken']
        progress.update(task, completed=total)


def parse_period(from_, given_interval, to):
    if given_interval:
        interval = parse_interval(given_interval)
    else:
        interval = datetime.timedelta(days=1)

    to_time = from_time = None
    if to:
        to_time = datetime.datetime.fromisoformat(to).astimezone()
    if from_:
        from_time = datetime.datetime.fromisoformat(from_).astimezone()

    if not to_time:
        if from_time and given_interval:
            to_time = from_time + interval
        else:
            to_time = datetime.datetime.now(datetime.timezone.utc)

    if not from_time:
        from_time = to_time - interval

    return from_time, to_time


interval_pattern = re.compile(
    r'((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?')


def parse_interval(interval: str):
    m = interval_pattern.fullmatch(interval)
    if not m:
        raise ValueError("Invalid interval")
    return datetime.timedelta(
        **dict(map(lambda x: (x[0], int(x[1])),
                   filter(lambda x: x[1] is not None,
                            m.groupdict().items()))))


def main():
    opts = docopt.docopt(__doc__)
    if opts['--verbose']:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level,
                        handlers=[RichHandler(rich_tracebacks=True)])

    client = boto3.client('logs')
    if opts['list-streams']:
        streams = get_streams(client, opts['LOG_GROUP'],
                              opts['STREAM_PREFIX'])
        print("Available log streams:\n\n  " + "\n  ".join(streams))
    else:
        with rp.Progress(
                rp.SpinnerColumn(),
                rp.TextColumn("[progress.description]{task.description}"),
                rp.BarColumn(),
                rp.TextColumn(
                    "[progress.percentage]{task.percentage:>3.0f}%"),
                rp.TimeRemainingColumn(),
                rp.TimeElapsedColumn()) as progress:

            from_time, to_time = parse_period(opts['--from'],
                                              opts['--interval'],
                                              opts['--to'])

            log_download(client,
                         opts['LOG_GROUP'], opts['STREAM_PREFIX'],
                         opts['OUTPUT'],
                         from_time=from_time, to_time=to_time,
                         progress=progress)


if __name__ == "__main__":
    main()
