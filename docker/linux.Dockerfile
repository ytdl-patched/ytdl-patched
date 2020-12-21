ARG base_tag=latest
FROM python:${base_tag}

ADD artifacts/youtube-dl /bin/

RUN chmod a+x /bin/youtube-dl && \
    youtube-dl --version && youtube-dl --help
