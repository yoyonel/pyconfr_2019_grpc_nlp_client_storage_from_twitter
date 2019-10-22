#!/usr/bin/env python
"""
    -u EmmanuelMacron Trump PyCon OpenGL Lyon Paris Marseille Bordeaux Toulouse

    # multiprocessing with linux shell and no database storing/saving.
    ╰─ time (twint -u EmmanuelMacron --limit 500 & twint -u Trump --limit 500 & twint -u PyCon --limit 500 & twint -u OpenGL --limit 500 & wait)
    ( twint -u EmmanuelMacron --limit 500 & twint -u Trump --limit 500 & twint -u)  28.56s user 2.92s system 103% cpu 30.502 total

    --process run_twint_with_multiprocessing -u EmmanuelMacron Trump PyCon -l 500  --log_level info
    2019-09-01 12:33:19 - client_rpc_storage_from_twitter_into_db - INFO - Time elapsed: 32.2337887

    TODO:
      - write unit tests ! :p
"""
import argparse
import logging
import os
import signal
import sys
from timeit import default_timer as timer

import twint
from pyconfr_2019.grpc_nlp.tools.fct_logger import init_logger

from storage.processors.twint_with_cli import run_twint_with_cli
from storage.processors.twint_with_multiprocess import run_twint_with_multiprocessing

logger = logging.getLogger(__name__)

SIGNALS = [signal.SIGINT, signal.SIGTERM]


def process(args: argparse.Namespace):
    def _signal_handler(_sig, _):
        """ Empty signal handler used to override python default one """
        logger.info("sig: {} intercepted. Closing application.".format(_sig))
        # https://stackoverflow.com/questions/73663/terminating-a-python-script
        sys.exit()

    # Signals HANDLER (to exit properly)
    for sig in SIGNALS:
        signal.signal(sig, _signal_handler)

    twint_configs = []
    for twitter_user in args.twitter_users:
        twint_config = twint.Config()
        twint_config.Username = twitter_user
        twint_config.Limit = args.twint_limit  # bug with the Limit parameter not working only factor of 25 tweets
        twint_config.Debug = args.twint_debug
        twint_configs.append(twint_config)

    twitter_analyzer_storage_host = (args.twitter_analyzer_storage_addr,
                                     args.twitter_analyzer_storage_port)
    if args.processor == 'run_twint_with_cli':
        run_twint_with_cli(twint_configs)
    elif args.processor == 'run_twint_with_multiprocessing':
        run_twint_with_multiprocessing(twint_configs, *twitter_analyzer_storage_host, log_level=args.log_level)


def build_parser(parser=None, **argparse_options):
    """
    Args:
        parser (argparse.ArgumentParser):
        **argparse_options (dict):
    Returns:
    """
    if parser is None:
        parser = argparse.ArgumentParser(**argparse_options)

    argparse_default = "(default=%(default)s)."

    # TODO: grab parser from twint lib and getting all options available (by inheritance)
    parser.add_argument('-p', '--processor',
                        dest='processor',
                        type=str,
                        choices=['run_twint_with_multiprocessing',
                                 'run_twint_with_cli'],
                        default='run_twint_with_multiprocessing',
                        help=f"Processor to use to grab tweets (from Twinter). {argparse_default}")
    parser.add_argument('-u', '--twitter_users',
                        dest='twitter_users',
                        nargs='+',
                        type=str,
                        required=True,
                        help="Twitter user.")

    parser.add_argument("-l", "--twint_limit",
                        dest="twint_limit",
                        type=int,
                        required=False,
                        default=100,
                        help=f"Twint limit for scrapping tweets. {argparse_default}")

    parser.add_argument("--twint_debug",
                        dest="twint_debug",
                        action="store_true",
                        help="Activate Debug mode for twint (printout results in logs).")
    # GRPC SERVICES
    # - STORAGE
    parser.add_argument("--twitter_analyzer_storage_addr",
                        default=os.environ.get('GRPC_STORAGE_SERVICE_HOST', 'localhost'),
                        type=str,
                        help=f"{argparse_default}")
    parser.add_argument("--twitter_analyzer_storage_port",
                        default=int(os.environ.get('GRPC_STORAGE_PORT', '50052')),
                        type=int,
                        help=f"{argparse_default}",
                        metavar='')

    parser.add_argument(
        '-ll', '--log_level',
        type=str, required=False, default='debug',
        choices=['debug', 'warning', 'info', 'error', 'critical'],
        help=f"The logger filter level. {argparse_default}",
    )
    parser.add_argument(
        '-lf', '--log_file',
        type=str, required=False,
        help="The path to the file into which the logs will be streamed. "
             f"{argparse_default}",
    )

    parser.add_argument("-v", "--verbose",
                        action="store_true", default=False,
                        help="increase output verbosity (enable 'DEBUG' level log). "
                             f"{argparse_default}")

    return parser


def parse_arguments(args=None):
    """
    Returns:
        argparse.Namespace:
    """
    return build_parser().parse_args(args)


def main(args=None):
    start = timer()

    # Deal with inputs (stdin, parameters, etc ...)
    args = parse_arguments(args)

    init_logger(args.log_level)

    process(args)

    end = timer()
    logger.info(f"Time elapsed: {end - start}")


if __name__ == '__main__':
    main()
    sys.exit(0)
