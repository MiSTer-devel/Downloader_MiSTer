#!/usr/bin/env bash
# Copyright (c) 2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

if ! gh release list | grep -q "latest" ; then
    gh release create "latest" || true
    sleep 15s
fi

cd src
cp pc_launcher.py downloader_pc_launcher.py
zip "MiSTer_Downloader_PC_Launcher.zip" downloader_pc_launcher.py
gh release upload "latest" "MiSTer_Downloader_PC_Launcher.zip" --clobber
