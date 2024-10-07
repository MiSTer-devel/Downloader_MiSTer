#!/usr/bin/env bash

set -euo pipefail

CUR_DIR=$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)
BASE_DIR=$(cd "${CUR_DIR}/../../../../" && pwd)

cd "${BASE_DIR}"

MISTER_IP=${MISTER_IP:-$(cat "mister.ip" | tr -d '[:space:]')}
MISTER_PW=1
if [ -f mister.pw ] ; then
    MISTER_PW=$(cat "mister.pw" | tr -d '[:space:]')
fi

MISTER=true ./src/build.sh > /tmp/double_check_downloader2.sh
chmod +x /tmp/double_check_downloader2.sh

echo "Setting up scripts..."
sshpass -p "${MISTER_PW}" scp downloader.sh "root@${MISTER_IP}":/tmp/double_check_downloader1.sh
sshpass -p "${MISTER_PW}" scp ${CUR_DIR}/double_check_downloader1.ini "root@${MISTER_IP}":/tmp/double_check_downloader1.ini
sshpass -p "${MISTER_PW}" scp /tmp/double_check_downloader2.sh "root@${MISTER_IP}":/tmp/double_check_downloader2.sh
sshpass -p "${MISTER_PW}" scp ${CUR_DIR}/double_check_downloader2.ini "root@${MISTER_IP}":/tmp/double_check_downloader2.ini

echo "Scripts installed."
echo
echo "Executing double_check_downloader1.sh"
sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" "rm -rf /media/fat/delme_double_check_downloader1/ 2> /dev/null || true"
echo
sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" /tmp/double_check_downloader1.sh

echo
echo "Executing double_check_downloader2.sh"
sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" "rm -rf /media/fat/delme_double_check_downloader2/ 2> /dev/null || true"
echo
sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" /tmp/double_check_downloader2.sh

echo
echo "Copying results..."
sshpass -p "${MISTER_PW}" scp "root@${MISTER_IP}":/media/fat/delme_double_check_downloader1/Scripts/.config/downloader/downloader.json.zip /tmp/store1.json.zip
sshpass -p "${MISTER_PW}" scp "root@${MISTER_IP}":/media/fat/delme_double_check_downloader2/Scripts/.config/downloader/downloader.json.zip /tmp/store2.json.zip

echo
echo "Comparing outputs..."

"${CUR_DIR}/compare_stores.py /tmp/store1.json.zip /tmp/store2.json.zip"

echo
echo
echo "Stores are equivalent."
echo
echo "Cleaning up..."
sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" "rm -rf /media/fat/delme_double_check_downloader1/"
sshpass -p "${MISTER_PW}" ssh "root@${MISTER_IP}" "rm -rf /media/fat/delme_double_check_downloader2/"

echo
echo "Done."