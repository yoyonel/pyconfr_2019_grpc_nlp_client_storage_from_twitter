import builtins
import logging
import multiprocessing
import queue
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import partial
from multiprocessing import Pool as MPPool
from typing import Any, Callable, Optional

import twint
from google.protobuf.json_format import MessageToDict
from mock import patch
from pyconfr_2019.grpc_nlp.protos import StorageService_pb2, StorageService_pb2_grpc, Tweet_pb2
from pyconfr_2019.grpc_nlp.protos.StorageService_pb2_grpc import StorageServiceStub
from pyconfr_2019.grpc_nlp.tools.fct_logger import init_logger
from pyconfr_2019.grpc_nlp.tools.grouper import grouper_it
from pyconfr_2019.grpc_nlp.tools.rpc_init_stub import rpc_init_stub
from pyconfr_2019.grpc_nlp.tools.timestamps import tweet_datetime_to_utc_timestamp

logger = logging.getLogger(__name__)


def run_twint_with_multiprocessing(
        twint_configs,
        rpc_storage_addr,
        rpc_storage_port,
        nb_tweets_by_chunk=20,
        log_level: Optional[str] = None
):
    """

    Args:
        twint_configs:
        rpc_storage_addr:
        rpc_storage_port:
        nb_tweets_by_chunk:
        log_level:

    Returns:

    """
    mp_manager = multiprocessing.Manager()
    mp_queue = mp_manager.Queue()
    mp_event_twint_worker_is_finish = mp_manager.Event()

    # declare (only) one consumer for storing twint's tweets into db (though gRPC (storage) service).
    mp_worker_consumer = multiprocessing.Process(
        name="consumer: tweets from twint",
        target=loop_consume_tweets_from_twint_mp,
        kwargs={
            'queue_sync_with_twint': mp_queue,
            'event_twint_worker_is_finish': mp_event_twint_worker_is_finish,
            'twitter_analyzer_storage_addr': rpc_storage_addr,
            'twitter_analyzer_storage_port': rpc_storage_port,
            'nb_tweets_by_chunk': nb_tweets_by_chunk,
            'log_level': log_level,
        }
    )
    # This is critical! The consumer function has an infinite loop
    # Which means it will never exit unless we set daemon to true
    mp_worker_consumer.daemon = True
    mp_worker_consumer.start()

    # for each twint config (i.e twint tweets producer)
    # link to the same multiprocessing queue
    for twint_config in twint_configs:
        twint_config.Store_object = True
        twint_config.Store_object_tweets_list = mp_queue

    # Init a multiprocessing pool for all twint configs (producers)
    # Launch worker on search (tweets) method
    nb_producers = len(twint_configs)
    mp_pool_producers = MPPool(nb_producers)
    _ = mp_pool_producers.map(
        partial(worker_on_twint_run_search,
                use_capture_printouts=True,
                log_level=log_level),  # argument apply to all calls
        twint_configs  # map on all twint configurations
    )
    mp_pool_producers.close()
    # wait until all producers finish
    mp_pool_producers.join()
    logger.debug("All producers (nb=%d) are finished", nb_producers)

    # set the event (flag) to notify all consumers that twint producers are finished
    mp_event_twint_worker_is_finish.set()
    # wait until all consumers finished
    mp_worker_consumer.join()
    logger.debug("All consumers (nb=1) are finished")

    assert mp_queue.qsize() == 0


def loop_consume_tweets_from_twint_mp(
        queue_sync_with_twint: queue.Queue,
        twitter_analyzer_storage_addr,
        twitter_analyzer_storage_port,
        event_twint_worker_is_finish,
        nb_tweets_by_chunk,
        log_level: Optional[str] = None
):
    """
    AttributeError: Can't pickle local object '...'
    https://github.com/ouspg/trytls/issues/196#issuecomment-239676366

    https://github.com/grpc/grpc/tree/master/examples/python/multiprocessing
    https://github.com/grpc/grpc/blob/master/examples/python/multiprocessing/client.py

    Args:
        queue_sync_with_twint:
        twitter_analyzer_storage_addr:
        twitter_analyzer_storage_port:
        event_twint_worker_is_finish:
        nb_tweets_by_chunk:
        log_level:

    Returns:

    """
    if log_level:
        init_logger(log_level)

    # init gRPC stub to access to Storage service(r)
    storage_rpc_stub = None
    if twitter_analyzer_storage_addr and twitter_analyzer_storage_port:
        storage_rpc_stub = rpc_init_stub(
            twitter_analyzer_storage_addr,
            twitter_analyzer_storage_port,
            StorageService_pb2_grpc.StorageServiceStub,
            service_name='[twint-multiprocessing] twitter analyzer storage'
        )

    def _func_exit_loop():
        #
        # To create code that needs to wait for all queued tasks to be
        # completed, the preferred technique is to use the join() method.
        # return (event_twint_worker_is_finish.is_set()
        #         and queue_sync_with_twint.qsize() == 0)
        return event_twint_worker_is_finish.is_set()

    loop_store_tweets(queue_sync_with_twint,
                      storage_rpc_stub,
                      func_is_time_to_exit=_func_exit_loop,
                      func_apply_to_input=_convert_tweet_from_twint_to_pb2,
                      nb_tweets_by_chunk=nb_tweets_by_chunk)


def worker_on_twint_run_search(
        twint_config,
        use_capture_printouts: bool = False,
        log_level: Optional[str] = None,
):
    # https://stackoverflow.com/questions/26923050/how-do-i-name-the-processes-in-a-multiprocessing-pool
    multiprocessing.current_process().name = f"producer: twint's tweets from <{twint_config.Username}>"

    if log_level:
        init_logger(log_level)

    def mock_logger_debug(_, *__, **___):
        pass

    # https://stackoverflow.com/questions/3024925/create-a-with-block-on-several-context-managers
    # https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack
    ctx_managers_capture_outputs = [
        patch.object(logging, 'debug', mock_logger_debug),
        patch.object(builtins, 'print', mock_logger_debug)
    ]

    with ExitStack() as stack:
        for mgr in ctx_managers_capture_outputs if use_capture_printouts else []:
            stack.enter_context(mgr)
        # Patch the entry point "append" for twint's store object container.
        # The patch connect append to put, and allow to use multiprocessing.Queue
        setattr(twint_config.Store_object_tweets_list, "append",
                twint_config.Store_object_tweets_list.put)
        logger.debug("Starting worker on (twint) searching tweets from twitter user=<%s>", twint_config.Username)
        twint.run.Search(twint_config)
        logger.debug("Stopping worker on (twint) searching tweets from twitter user=<%s>", twint_config.Username)


def _convert_tweet_from_twint_to_pb2(tweet) -> Tweet_pb2.Tweet:
    return Tweet_pb2.Tweet(
        created_at=tweet_datetime_to_utc_timestamp(tweet.datetime, tweet.timezone),
        text=tweet.tweet,
        user_id=tweet.user_id,
        lang='',
        tweet_id=tweet.id,
        user_name=tweet.username,
    )


def loop_store_tweets(
        queue_with_pb2_tweets: queue.Queue,
        storage_rpc_stub: Optional[StorageServiceStub],
        func_is_time_to_exit: Callable[[], bool],
        func_apply_to_input: Callable[[Any], Any] = lambda i: i,
        nb_tweets_by_chunk: int = 50,
):
    def _stream_chunk_tweets():
        # https://anandology.com/python-practice-book/iterators.html
        @dataclass
        class GenPb2Tweets:
            queue: queue.Queue
            #
            timeout: float = field(default=1.00)

            def __iter__(self):
                return self

            def __next__(self):
                while True:
                    try:
                        pb2_tweets = func_apply_to_input(self.queue.get(timeout=self.timeout))
                        break
                    except queue.Empty:
                        if func_is_time_to_exit():
                            raise StopIteration
                return pb2_tweets

        for _chunk_tweets in grouper_it(GenPb2Tweets(queue_with_pb2_tweets),
                                        nb_tweets_by_chunk):
            yield _chunk_tweets

    for chunk_tweets in _stream_chunk_tweets():
        tweets = [
            StorageService_pb2.StoreTweetsRequest(tweet=tweet)
            for tweet in chunk_tweets
        ]

        def _format_debug_infos():
            return ", ".join(
                f"{user_name}#{counter}"
                for user_name, counter in Counter([tweet.tweet.user_name.lower() for tweet in tweets]).items()
            )

        logger.debug("gRPC: store %d tweets from users=(%s) in db ...", len(tweets), _format_debug_infos())

        if storage_rpc_stub:
            # -> gRPC Storage service
            store_tweets_stream_response = MessageToDict(
                storage_rpc_stub.StoreTweetsStream(iter(tweets)),
                including_default_value_fields=True
            )
            logger.debug(f"Response(StoreTweetsStream) = {store_tweets_stream_response}")
        # tweets from queue stored in database, so the queue task is done (for this chunk)
        queue_with_pb2_tweets.task_done()

    # logger.debug("nb_check_executed_for_exit=%d", nb_check_executed_for_exit)
