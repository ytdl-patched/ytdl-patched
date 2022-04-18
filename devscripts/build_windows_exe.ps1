#!/usr/bin/env pwsh
# $IconName - red or white
# $BuilderName - PyInstaller or py2exe
Param($BuilderName, $IconName)
$ErrorActionPreference = "Stop"

switch ($BuilderName) {
    "PyInstaller" {
        $env:windows_icon="${IconName}"

        write-host "Building an EXE using PyInstaller"
        python -OO pyinst.py

        write-host "Moving built EXE into artifacts/"
        Move-Item dist/ytdl-patched.exe artifacts/
    }
    "py2exe" {
        $env:PY2EXE_WINDOWS_ICON_PATH="icons\youtube_social_squircle_${IconName}.ico"

        write-host "Building an EXE using py2exe"
        python setup.py py2exe

        write-host "Moving built EXE into artifacts/"
        Move-Item ytdl-patched.exe artifacts/
    }
    default {
        throw "Invalid BuilderName: $BuilderName"
    }
}
