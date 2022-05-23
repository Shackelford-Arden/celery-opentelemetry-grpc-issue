FROM python:3.8.13-slim-bullseye

WORKDIR /opt/code

RUN apt-get update -qq && apt-get install -yqq curl && export PATH="/root/.local/bin:$PATH"

ENV PATH="/root/.local/bin:$PATH"
ENV GRPC_ENABLE_FORK_SUPPORT=1
ENV GRPC_POLL_STRATEGY="epoll1"

COPY . .

RUN curl -sSL https://install.python-poetry.org | python3 - && poetry config virtualenvs.create false && poetry install --no-root --no-dev