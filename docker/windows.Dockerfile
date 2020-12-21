ARG base_tag=windowsservercore-1806
FROM python:${base_tag}

RUN powershell New-Item -ItemType "directory" -Path C:/Users/ContainerAdministrator/AppData/Local -Name youtube-dl
ADD artifacts/youtube-dl.exe C:/Users/ContainerAdministrator/AppData/Local/youtube-dl

RUN youtube-dl --version ; youtube-dl --help
