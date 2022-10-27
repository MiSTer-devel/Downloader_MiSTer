#!/usr/bin/env bash
# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

MISTER_IP=${MISTER_IP:-$(cat "mister.ip" | tr -d '[:space:]')}
MISTER_PW=1
if [ -f mister.pw ] ; then
    MISTER_PW=$(cat "mister.pw" | tr -d '[:space:]')
fi

TEMP_SCRIPT="$(mktemp)"

DEBUG="${DEBUG:-true}" MISTER=true ./src/build.sh > "${TEMP_SCRIPT}"
chmod +x "${TEMP_SCRIPT}"

if [ -f dont_download.ini ] ; then
  sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no dont_download.ini "root@${MISTER_IP}:/media/fat/downloader.ini"
fi
sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no "${TEMP_SCRIPT}" "root@${MISTER_IP}:/media/fat/downloader.sh"
sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no downloader.sh "root@${MISTER_IP}:/media/fat/Scripts/downloader.sh"
rm "${TEMP_SCRIPT}"

if [[ "${1:-}" == 'run' ]] ; then
  sshpass -p "${MISTER_PW}" ssh -o StrictHostKeyChecking=no "root@${MISTER_IP}" "/media/fat/downloader.sh ${2:-}"
else
  echo "OK"
fi