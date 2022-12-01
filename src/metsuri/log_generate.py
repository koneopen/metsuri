"""
Usage: log-generate [options] FILE OUTPUT_LOG_FILE

Options:
  --help            This help.

"""
import docopt
import datetime
import random


def main():
    opts = docopt.docopt(__doc__)

    now = datetime.datetime.now(tz=datetime.timezone.utc)

    def seconds_gen():
        total = 0
        while True:
            yield total
            total += random.randint(1, 100)

    seconds = seconds_gen()

    with open(opts['OUTPUT_LOG_FILE'], "w") as outfile:
        for secs, ll in reversed(list(zip(seconds, reversed(open(opts['FILE'], "r").readlines())))):
            print(f"{(now - datetime.timedelta(seconds=secs)).isoformat()} {ll.rstrip()}", file=outfile)


if __name__ == "__main__":
    main()