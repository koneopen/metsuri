"""
Usage: log-check [options] LOG_FILE

Options:
  --verbose            Enable verbose logging.

"""
import docopt
import logging
from metsuri.log_uploader import get_log_entries

logger = logging.getLogger(__name__)


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
    try:
        line_number = 0
        for line_number, line in enumerate(get_log_entries(opts["LOG_FILE"])):
            pass
        else:
            print(f"Successfully processed {line_number} lines of log.")
    except Exception as e:
        logger.exception(f"Got error {e}")


if __name__ == "__main__":
    main()