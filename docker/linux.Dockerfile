ARG base_tag=latest
FROM python:${base_tag}

ADD artifacts/youtube-dl /usr/bin/

RUN chmod a+x /usr/bin/youtube-dl && \
    youtube-dl --version && youtube-dl --help
