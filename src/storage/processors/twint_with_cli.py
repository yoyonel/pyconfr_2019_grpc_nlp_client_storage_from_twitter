from mock import patch
from twint.cli import main as twint_main


def run_twint_with_cli(twint_configs):
    # https://stackoverflow.com/questions/18160078/how-do-you-write-tests-for-the-argparse-portion-of-a-python-module
    for twint_config in twint_configs:
        with patch('twint.cli.argparse._sys.argv',
                   ['twint',
                    '-u', twint_config.Username,
                    '--limit', str(twint_config.Limit)
                    ]):
            twint_main()
