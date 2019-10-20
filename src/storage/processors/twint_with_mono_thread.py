import logging

import twint
from google.protobuf.json_format import MessageToDict
from pyconfr_2019.grpc_nlp.protos import StorageService_pb2, StorageService_pb2_grpc
from pyconfr_2019.grpc_nlp.tools.rpc_init_stub import rpc_init_stub

from storage.processors.twint_with_multiprocess import _convert_tweet_from_twint_to_pb2

logger = logging.getLogger(__name__)


def run_mono_thread_twint(twint_config: twint.Config, storage_rpc_stub):
    """

    Args:
        twint_config:
        storage_rpc_stub:

    Returns:

    """
    tweets_list = []

    twint_config.Store_object = True
    twint_config.Store_object_tweets_list = tweets_list
    twint.run.Search(twint_config)

    if not tweets_list:
        logger.error(f"No tweets found from twitter_user={twint_config.Username}")
        return

    def _stream_tweets():
        for tweet in tweets_list:
            yield StorageService_pb2.StoreTweetsRequest(
                tweet=_convert_tweet_from_twint_to_pb2(tweet)
            )

    store_tweets_stream_response = MessageToDict(
        storage_rpc_stub.StoreTweetsStream(_stream_tweets()),
        including_default_value_fields=True
    )
    logger.debug(f"Response(StoreTweetsStream) = {store_tweets_stream_response}")


def run_twint_in_mono_thread(twint_configs, twitter_analyzer_storage_addr, twitter_analyzer_storage_port):
    # Init gRPC services Storage
    storage_rpc_stub = rpc_init_stub(twitter_analyzer_storage_addr,
                                     twitter_analyzer_storage_port,
                                     StorageService_pb2_grpc.StorageServiceStub,
                                     service_name='[twint-mono_thread] twitter analyzer storage')
    for twint_config in twint_configs:
        run_mono_thread_twint(twint_config, storage_rpc_stub)
