ARG base_tag=latest
FROM python:${base_tag}

RUN mkdir -p /opt/bin
ENV PATH="$PATH:/opt/bin"

ADD artifacts/youtube-dl /opt/bin/

RUN chmod a+x /opt/bin/youtube-dl && \
    youtube-dl --version && youtube-dl --help
