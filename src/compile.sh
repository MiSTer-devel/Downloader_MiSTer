#!/usr/bin/env bash
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

echo "Building Dockerfile.downloader_bin into ${1}..."

cd src

echo "default_commit = '$(git rev-parse --short HEAD)'" > "commit.py"

if [[ "${NUITKA_IMAGE:-}" == "" ]] ; then
  docker buildx build --platform=linux/arm/v7 --load -t arm32v7-nuitka -f src/Dockerfile.nuitka  .
fi
docker buildx build --build-arg BASE_IMAGE="${NUITKA_IMAGE:-arm32v7-nuitka}" --platform=linux/arm/v7 --load -t downloader_bin_builder -f Dockerfile.downloader_bin . > /dev/null
docker create --name downloader_bin_container downloader_bin_builder
docker cp downloader_bin_container:/app/__main__.bin "${1}"
docker rm downloader_bin_container
