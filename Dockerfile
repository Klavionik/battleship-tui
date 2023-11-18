FROM python:3.11.6-slim-bullseye
ENV PYTHONUNBUFFERED=1
ARG VERSION
ENV VERSION=$VERSION
WORKDIR /app

# GCC is required to build Blacksheep wheels on ARM arch.
RUN apt-get update && apt-get install -y curl gcc
COPY requirements-server.txt ./
RUN pip install -r requirements-server.txt
COPY . .

ARG USER=app
ARG UID=1000
RUN groupadd $USER --gid $UID
RUN useradd $USER --uid $UID --gid $UID --no-create-home
USER app:app
EXPOSE 8000
