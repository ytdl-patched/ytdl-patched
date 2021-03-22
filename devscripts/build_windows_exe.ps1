#!/usr/bin/env pwsh
# $IconName - red or white
# $BuilderName - PyInstaller or py2exe
Param($BuilderName, $IconName)

switch ($BuilderName) {
    "PyInstaller" {
        $IconArg = @()
        if ($IconName) {
            $IconArg = "--icon", "icons\youtube_social_squircle_${IconName}.ico"
        }
        write-host "Building an EXE using PyInstaller"
        python -OO devscripts/pyinstaller_zopfli.py `
            --onefile --console --distpath . `
            @IconArg `
            -n youtube-dl youtube_dl\__main__.py

        write-host "Moving built EXE into artifacts/"
        Move-Item youtube-dl.exe artifacts/
    }
    "py2exe" {
        $IconArg = @()
        if ($IconName) {
            $IconArg = "--icon", "icons\youtube_social_squircle_${IconName}.ico"
        }
        write-host "Building an EXE using py2exe"
        python setup.py py2exe @IconArg

        write-host "Moving built EXE into artifacts/"
        Move-Item youtube-dl.exe artifacts/
    }
    default {
        throw "Invalid BuilderName: $BuilderName"
    }
}
