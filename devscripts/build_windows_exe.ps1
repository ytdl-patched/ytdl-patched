#!/usr/bin/env pwsh
# $IconName - red or white
# $BuilderName - PyInstaller or py2exe
Param($BuilderName, $IconName)
$ErrorActionPreference = "Stop"

switch ($BuilderName) {
    "PyInstaller" {
        $IconArg = @()
        if ($IconName) {
            $IconArg = "--icon", "icons\youtube_social_squircle_${IconName}.ico"
        }
        write-host "Building an EXE using PyInstaller"
        python -OO pyinst.py

        write-host "Moving built EXE into artifacts/"
        Move-Item youtube-dl.exe artifacts/
    }
    "py2exe" {
        $env:PY2EXE_WINDOWS_ICON_PATH="icons\youtube_social_squircle_${IconName}.ico"

        write-host "Building an EXE using py2exe"
        python setup.py py2exe

        write-host "Moving built EXE into artifacts/"
        Move-Item youtube-dl.exe artifacts/
    }
    default {
        throw "Invalid BuilderName: $BuilderName"
    }
}
