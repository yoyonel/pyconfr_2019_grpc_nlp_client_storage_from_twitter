#! /bin/sh

export DOCKER_USERNAME="yoyonel"
export DOCKER_IMAGE="${DOCKER_USERNAME}/python:3.7.3-slim-stretch"

echo "Building docker image: ${DOCKER_IMAGE} ..."

docker build -t ${DOCKER_IMAGE} .
docker push ${DOCKER_IMAGE}
