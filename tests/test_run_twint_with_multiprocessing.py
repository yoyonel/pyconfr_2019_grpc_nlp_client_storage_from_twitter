import logging
import math
import multiprocessing
from collections import defaultdict

import pytest
import queue
from dataclasses import dataclass
from typing import Iterator, List

import twint
from pyconfr_2019.grpc_nlp.protos.StorageService_pb2 import StoreTweetsResponse, StoreTweetsRequest

from storage.processors.twint_with_multiprocess import run_twint_with_multiprocessing

cache_multiprocessing = {}


@pytest.fixture
def build_twint_configs():
    def _build_twint_configs(twitter_users=("PyConFr", "PyCon")):
        twint_configs = []
        twint_limit = 25
        twint_debug = False
        for twitter_user in twitter_users:
            twint_config = twint.Config()
            twint_config.Username = twitter_user
            twint_config.Limit = twint_limit  # bug with the Limit parameter not working only factor of 25 tweets
            twint_config.Debug = twint_debug
            twint_configs.append(twint_config)
        return twint_configs

    return _build_twint_configs


def test_run_twint_with_multiprocessing(build_twint_configs, mocker, caplog):
    nb_tweets_by_chunk = 20
    twitter_users = ("PyConFr", "PyCon", "ThePSF")
    twint_configs = build_twint_configs(twitter_users)
    twint_limit = twint_configs[0].Limit

    class MockRpcInitStub:
        def __init__(self, _mp_queue: queue.Queue):
            self._mp_queue = _mp_queue

        def StoreTweetsStream(self, iter_pb2_tweets_responses: Iterator[StoreTweetsResponse]):
            i_tweet = 0
            for i_tweet, pb2_tweet in enumerate(iter_pb2_tweets_responses, start=1):
                self._mp_queue.put(pb2_tweet)
            return StoreTweetsResponse(nb_tweets_received=i_tweet,
                                       nb_tweets_stored=i_tweet)

    mock_rpc_init_stub = mocker.patch('storage.processors.twint_with_multiprocess.rpc_init_stub')
    # Need to use a MultiProcess (synchronized) Queue
    mp_manager = multiprocessing.Manager()
    mp_queue = mp_manager.Queue()
    mock_rpc_init_stub.return_value = MockRpcInitStub(mp_queue)

    # https://docs.pytest.org/en/latest/logging.html
    with caplog.at_level(logging.DEBUG):
        run_twint_with_multiprocessing(
            twint_configs,
            # dummy connection parameters to instantiate
            rpc_storage_addr="Test",
            rpc_storage_port=12345,
            # a connection to rpc storage server
            nb_tweets_by_chunk=nb_tweets_by_chunk,
            log_level="debug"
        )

    nb_twitter_api_requests = math.ceil(twint_limit / float(nb_tweets_by_chunk))
    assert len(caplog.records) == nb_twitter_api_requests

    # Generator on tweets saved in MP Queue
    @dataclass
    class GenPb2Tweets:
        queue: queue.Queue

        def __iter__(self):
            return self

        def __next__(self):
            while True:
                try:
                    pb2_tweets = self.queue.get_nowait()
                    break
                except queue.Empty:
                    raise StopIteration
            return pb2_tweets

    store_tweets_request = list(GenPb2Tweets(mp_queue))  # type: List[StoreTweetsRequest]
    assert len(store_tweets_request) == nb_tweets_by_chunk * nb_twitter_api_requests * len(twint_configs)

    tweets_by_users = defaultdict(list)
    for store_tweet_request in store_tweets_request:
        tweet = store_tweet_request.tweet
        tweets_by_users[tweet.user_name].append(tweet)
    assert sorted(list(map(str.lower, tweets_by_users.keys()))) == sorted(map(str.lower, twitter_users))
