FROM mcr.microsoft.com/vscode/devcontainers/universal:linux

ENV PATH="$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:$PATH"

ARG NODE_VERSION="14"
RUN ( umask 0002 && . $HOME/.nvm/nvm.sh && nvm install ${NODE_VERSION} || true ) && \
    sed -i 's/# export LANG/export LANG/' ~/.bashrc && \
    pip3 install --user -U pytest nose flake8 pip && \
    sudo apt update && \
    sudo apt upgrade -y && \
    sudo apt install -y ffmpeg rtmpdump shellcheck pandoc && \
    sudo apt-get update && \
    sudo apt-get install -y --no-install-recommends software-properties-common && \
    sudo add-apt-repository -y ppa:git-core/ppa && \
    sudo apt-get update && \
    sudo apt-get install -y --no-install-recommends \
        bzip2 ca-certificates \
        curl \
        file \
        fonts-dejavu-core \
        g++ \
        git \
        less \
        libz-dev \
        locales \
        make \
        netbase \
        openssh-client \
        patch \
        sudo \
        uuid-runtime \
        tzdata && \
    sudo rm -rf /var/lib/apt/lists/* && \
    sudo mkdir -p /home/linuxbrew/.linuxbrew && \
    sudo chown -R codespace:codespace /home/linuxbrew/ && \
    git clone https://github.com/Homebrew/brew /home/linuxbrew/.linuxbrew/ && \
    true && \
    brew doctor && \
    echo "eval \$($(brew --prefix)/bin/brew shellenv)" >> ~/.bash_profile && \
    HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_AUTO_UPDATE=1 brew tap homebrew/core nao20010128nao/my && \
    brew install-bundler-gems && \
    brew install nao20010128nao/my/advcomp && \
    brew cleanup --prune 0 && \
    { git -C /home/linuxbrew/.linuxbrew config --unset gc.auto; true; } && \
    { git -C /home/linuxbrew/.linuxbrew config --unset homebrew.devcmdrun; true; } && \
    rm -rf ~/.cache && \
    chmod -R g+w,o-w /home/linuxbrew/.linuxbrew
