FROM mcr.microsoft.com/vscode/devcontainers/universal:linux

ARG INSTALL_NODE="true"
ARG NODE_VERSION="14"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi ; \
    pip3 install --user -U pytest nose flake8 pip && \
    sudo apt update && \
    sudo apt upgrade -y && \
    sudo apt install -y ffmpeg rtmpdump shellcheck pandoc && \
    sudo apt-get clean
