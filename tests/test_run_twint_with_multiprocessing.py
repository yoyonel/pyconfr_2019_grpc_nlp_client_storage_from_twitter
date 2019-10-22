import logging
import multiprocessing
import queue
from dataclasses import dataclass
from typing import Iterator

import math
import twint
from pyconfr_2019.grpc_nlp.protos.StorageService_pb2 import StoreTweetsResponse

from storage.processors.twint_with_multiprocess import run_twint_with_multiprocessing


def test_run_twint_with_multiprocessing(mocker, caplog):
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

    class MockRpcInitStub:
        def __init__(self, _mp_queue: queue.Queue):
            self._mp_queue = _mp_queue

        def StoreTweetsStream(self, iter_pb2_tweets_responses: Iterator[StoreTweetsResponse]):
            pb2_tweets = list(iter_pb2_tweets_responses)
            for pb2_tweet in pb2_tweets:
                self._mp_queue.put(pb2_tweet)
            return StoreTweetsResponse(nb_tweets_received=len(pb2_tweets),
                                       nb_tweets_stored=len(pb2_tweets))

    mock_rpc_init_stub = mocker.patch('storage.processors.twint_with_multiprocess.rpc_init_stub')
    # Need to use a MultiProcess (synchronized) Queue
    mp_manager = multiprocessing.Manager()
    mp_queue = mp_manager.Queue()
    mock_rpc_init_stub.return_value = MockRpcInitStub(mp_queue)

    # https://docs.pytest.org/en/latest/logging.html
    with caplog.at_level(logging.DEBUG):
        run_twint_with_multiprocessing(
            twint_configs,
            *('Test', 12345),  # dummy connection parameters to instantiate
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

    tweets = list(GenPb2Tweets(mp_queue))
    assert len(tweets) == nb_tweets_by_chunk * nb_twitter_api_requests
