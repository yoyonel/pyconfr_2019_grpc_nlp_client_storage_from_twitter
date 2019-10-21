import logging
import math

import twint

from storage.processors.twint_with_multiprocess import run_twint_with_multiprocessing


def test_run_twint_with_multiprocessing(caplog):
    twint_configs = []
    twitter_users = ["PyConFr"]
    twint_limit = 25
    nb_tweets_by_chunk = 20
    twint_debug = False
    for twitter_user in twitter_users:
        twint_config = twint.Config()
        twint_config.Username = twitter_user
        twint_config.Limit = twint_limit  # bug with the Limit parameter not working only factor of 25 tweets
        twint_config.Debug = twint_debug
        twint_configs.append(twint_config)
    twitter_analyzer_storage_host = (None, None)
    with caplog.at_level(logging.DEBUG):
        run_twint_with_multiprocessing(
            twint_configs,
            *twitter_analyzer_storage_host,
            nb_tweets_by_chunk=nb_tweets_by_chunk,
            log_level="debug"
        )
    assert len(caplog.records) == math.ceil(twint_limit / float(nb_tweets_by_chunk))
