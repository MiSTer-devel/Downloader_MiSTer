#!/usr/bin/env bash

set -euo pipefail

MISTER_IP=${MISTER_IP:-$(cat "mister.ip" | tr -d '[:space:]')}
MISTER_PW=1
if [ -f mister.pw ] ; then
    MISTER_PW=$(cat "mister.pw" | tr -d '[:space:]')
fi

CUR_DIR=$(dirname "$0")

sshpass -p "${MISTER_PW}" scp ${CUR_DIR}/corruption_db1.json "root@${MISTER_IP}":/media/fat/db1.json
sshpass -p "${MISTER_PW}" scp ${CUR_DIR}/corruption_db2.json "root@${MISTER_IP}":/media/fat/db2.json
sshpass -p "${MISTER_PW}" scp ${CUR_DIR}/corruption_repro_cycle.sh "root@${MISTER_IP}":/media/fat/repro.sh
./src/build.sh > ${CUR_DIR}/corruption_downloader.sh
sshpass -p "${MISTER_PW}" scp ${CUR_DIR}/corruption_downloader.sh "root@${MISTER_IP}":/media/fat/corruption_downloader.sh

while true
do
    set +e
	sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" tail -n ${1:-0} -f /media/fat/repro.log
    set -e
	sleep 0.5
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
    echo
done
