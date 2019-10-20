#!/bin/bash
set -e

export DOCKER_USERNAME="yoyonel"
export DOCKER_IMAGE="${DOCKER_USERNAME}/python:3.7.3-slim-stretch"

source ../versions/set_versions.sh

for VERSION in ${GRPC_VERSIONS}; do
    echo "Building docker image: ${DOCKER_IMAGE}-grpc${VERSION} ..."

    docker build --build-arg GRPC_VERSION=${VERSION} -t ${DOCKER_IMAGE}-grpc${VERSION} .
    docker push ${DOCKER_IMAGE}-grpc${VERSION}
done