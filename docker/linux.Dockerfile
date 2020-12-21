ARG base_tag=latest
FROM python:${base_tag}

ADD ./artifacts/youtube-dl /bin/

RUN youtube-dl --version && youtube-dl --help
