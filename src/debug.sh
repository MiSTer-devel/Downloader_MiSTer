#!/usr/bin/env bash
# Copyright (c) 2021-2023 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

MISTER_IP=${MISTER_IP:-$(cat "mister.ip" | tr -d '[:space:]')}
MISTER_PW=1
if [ -f mister.pw ] ; then
    MISTER_PW=$(cat "mister.pw" | tr -d '[:space:]')
fi

send_build() {
  local TEMP_SCRIPT="$(mktemp)"
  DEBUG="${DEBUG:-true}" MISTER=true ./src/build.sh > "${TEMP_SCRIPT}"
  chmod +x "${TEMP_SCRIPT}"

  if [ -f dont_download.ini ] ; then
    sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no dont_download.ini "root@${MISTER_IP}:/media/fat/downloader.ini"
  fi
  sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no "${TEMP_SCRIPT}" "root@${MISTER_IP}:/media/fat/downloader.sh"
  sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no downloader.sh "root@${MISTER_IP}:/media/fat/Scripts/downloader.sh"
  rm "${TEMP_SCRIPT}"
}

store_push() {
  zip -o downloader.json.zip downloader.json
  sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no downloader.json.zip "root@${MISTER_IP}:/media/fat/Scripts/.config/downloader/downloader.json.zip"
}

store_pull() {
  rm -f downloader.json.zip downloader.json
  sshpass -p "${MISTER_PW}" scp -o StrictHostKeyChecking=no "root@${MISTER_IP}:/media/fat/Scripts/.config/downloader/downloader.json.zip" downloader.json.zip
  unzip -o downloader.json.zip
}

touch_file() {
  sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" "cd /media/fat; rm -f ${1}; touch ${1}"
}

run_command() {
  send_build
  sshpass -p "${MISTER_PW}" ssh -o StrictHostKeyChecking=no "root@${MISTER_IP}" "/media/fat/downloader.sh ${1:-}"
}

run_launcher() {
  send_build
  sshpass -p "${MISTER_PW}" ssh -o StrictHostKeyChecking=no "root@${MISTER_IP}" "/media/fat/Scripts/downloader.sh ${1:-}"
}

case "${1:-}" in
  'store')
    case "${2:-}" in
      'push') store_push ;;
      'pull') store_pull ;;
      *) echo "Usage: $0 store [push|pull]"; exit 1 ;;
    esac
    ;;
  'touch')
    if [[ -n "${2:-}" ]]; then
      touch_file "$2"
    else
      echo "Usage: $0 touch <file>"
      exit 1
    fi
    ;;
  'run') run_command "${2:-}" ;;
  'launcher') run_launcher "${2:-}" ;;
  *)
    send_build
    echo "OK"
    ;;
esac
