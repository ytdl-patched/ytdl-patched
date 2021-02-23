FROM mcr.microsoft.com/vscode/devcontainers/python:3

RUN pip3 install --user -U pytest nose flake8 pip && \
    sudo apt update && \
    sudo apt upgrade -y && \
    sudo apt install -y ffmpeg rtmpdump && \
    sudo apt-get clean

USER root
