FROM yoyonel/python:3.7.3-slim-stretch-grpc1.21.1

COPY . /app

WORKDIR /app

ARG PYPI_SERVER=https://pypi.org/simple/

ARG APP_ENTRY_POINT=pyconfr_2019_grpc_nlp_client_storage_from_twitter
ENV APP_ENTRY_POINT ${APP_ENTRY_POINT}

RUN pip install --upgrade pip && \
    pip install \
        --extra-index-url ${PYPI_SERVER} \
        $(find dist -maxdepth 1 -type f -printf "%T@ %p\n" | sort -nr | head -1 | cut -d ' ' -f 2) && \
    rm -rf ~/.cache/pip

EXPOSE 50052
CMD ${APP_ENTRY_POINT}