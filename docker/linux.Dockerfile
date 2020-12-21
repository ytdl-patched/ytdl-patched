ARG base_tag=latest
FROM python:${base_tag}

ADD youtube-dl /bin/

RUN youtube-dl --version && youtube-dl --help
