#!/usr/bin/env bash
# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

MISTER_IP=${MISTER_IP:-$(cat "mister.ip" | tr -d '[:space:]')}
MISTER_PW=1
if [ -f mister.pw ] ; then
    MISTER_PW=$(cat "mister.pw" | tr -d '[:space:]')
fi

TEMP_SCRIPT="$(mktemp)"

if [[ "${1:-}" == 'store' ]] ; then
  if [[ "${2:-}" == 'push' ]] ; then
    zip -o downloader.json.zip downloader.json
    sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no downloader.json.zip "root@${MISTER_IP}:/media/fat/Scripts/.config/downloader/downloader.json.zip"
  elif [[ "${2:-}" == 'pull' ]] ; then
    rm -f downloader.json.zip downloader.json
    sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no "root@${MISTER_IP}:/media/fat/Scripts/.config/downloader/downloader.json.zip" downloader.json.zip
    unzip -o downloader.json.zip
  else
    echo "Usage: $0 store [push|pull]"
    exit 1
  fi
  exit 0
elif [[ "${1:-}" == "touch" ]] ; then
  if [[ "${2:-}" != "" ]] ; then
    sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" "cd /media/fat; rm -f ${2}; touch ${2}"
  else
    echo "Usage: $0 touch <file>"
    exit 1
  fi
  exit 0
fi

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