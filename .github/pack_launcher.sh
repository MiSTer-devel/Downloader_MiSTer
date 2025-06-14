#!/usr/bin/env bash
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

if ! gh release list | grep -q "latest" ; then
    gh release create "latest" || true
    sleep 15s
fi

cp downloader.sh update.sh
zip "MiSTer_Downloader.zip" update.sh
gh release upload "latest" "MiSTer_Downloader.zip" --clobber
