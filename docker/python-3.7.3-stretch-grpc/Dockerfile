FROM yoyonel/python:3.7.3-slim-stretch

LABEL description=""

ARG GRPC_VERSION=1.21.1

RUN pip install --no-cache-dir \
    grpcio==${GRPC_VERSION} \
    grpcio-tools==${GRPC_VERSION} && \
    rm -rf ~/.cache/pip