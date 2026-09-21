FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev libjpeg62-turbo-dev zlib1g-dev \
    libturbojpeg0-dev ca-certificates && rm -rf /var/lib/apt/lists/*
