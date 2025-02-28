#!/usr/bin/env bash
# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

cd src

echo "default_commit = '$(git rev-parse --short HEAD)'" > "commit.py"
docker build --platform=linux/arm/v7 -t downloader-nuitka . > /dev/null
docker run --platform linux/arm/v7 downloader-nuitka
