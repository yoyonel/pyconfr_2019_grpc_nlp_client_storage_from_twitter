FROM python:3.7.3-slim-stretch

LABEL description="A python 3.7.3 image based on Debian 9.9 (stretch), with pipenv installed"

RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir pipenv>=2018.11.26 && \
    rm -rf ~/.cache/pip

RUN apt-get update && apt-get install -y \
    git \
 && rm -rf /var/lib/apt/lists/*