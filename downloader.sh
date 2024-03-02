#!/bin/bash
# Copyright (c) 2021-2024 José Manuel Barroso Galindo <theypsilon@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# You can download the latest version of this tool from:
# https://github.com/MiSTer-devel/Downloader_MiSTer

set -euo pipefail

SCRIPT_PATH="/tmp/downloader.sh"
LATEST_SCRIPT_PATH="/media/fat/Scripts/.config/downloader/downloader_latest.sh"
CACERT_PEM="/etc/ssl/certs/cacert.pem"

if (( $(date +%Y) < 2000 )) ; then
    NTP_SERVER="0.pool.ntp.org"
    echo "Syncing date and time with $NTP_SERVER"
    echo
    if ntpdate -s -b -u $NTP_SERVER ; then
        echo "Date and time is:"
        echo "$(date)"
        echo
    elif [[ "${CURL_SSL:-}" != "--insecure" ]] ; then
        echo "Unable to sync."
        echo "Please, try again later."
        exit 1
    fi
fi

if [ -s "${CACERT_PEM}" ] ; then
    export CURL_CA_BUNDLE="${CACERT_PEM}"
fi

download_file() {
    local DOWNLOAD_PATH="${1}"
    local DOWNLOAD_URL="${2}"
    for (( COUNTER=0; COUNTER<=60; COUNTER+=1 )); do
        if [ ${COUNTER} -ge 1 ] ; then
            sleep 1s
        fi

        set +e
        if [[ "${DOWNLOAD_PATH}" == "/dev/null" ]]; then
            curl ${CURL_SSL:-} --silent --fail --location -I "${DOWNLOAD_URL}" > /dev/null 2>&1
        else
            curl ${CURL_SSL:-} --silent --fail --location -o "${DOWNLOAD_PATH}" "${DOWNLOAD_URL}"
        fi
        local CMD_RET=$?
        set -e

        case ${CMD_RET} in
            0)
                export CURL_SSL="${CURL_SSL:-}"
                return
                ;;
            60|77|35|51|58|59|82|83)
                set +e
                dialog --keep-window --title "Bad Certificates" --defaultno \
                    --yesno "CA certificates need to be fixed, do you want me to fix them?\n\nNOTE: This operation will delete files at /etc/ssl/certs" \
                    7 65
                local DIALOG_RET=$?
                set -e

                if [[ "${DIALOG_RET}" == "0" ]] ; then
                    local RO_ROOT="false"
                    if mount | grep "on / .*[(,]ro[,$]" -q ; then
                        RO_ROOT="true"
                    fi
                    [ "${RO_ROOT}" == "true" ] && mount / -o remount,rw
                    rm /etc/ssl/certs/* 2> /dev/null || true
                    echo
                    echo "Installing cacert.pem from https://curl.se"
                    curl --insecure --location -o /tmp/cacert.pem "https://curl.se/ca/cacert.pem"
                    curl --insecure --location -o /tmp/cacert.pem.sha256 "https://curl.se/ca/cacert.pem.sha256"

                    local DOWNLOAD_SHA256=$(cat /tmp/cacert.pem.sha256 | awk '{print $1}')
                    local CALCULATED_SHA256=$(sha256sum /tmp/cacert.pem | awk '{print $1}')

                    if [[ "${DOWNLOAD_SHA256}" == "${CALCULATED_SHA256}" ]]; then
                        mv /tmp/cacert.pem /etc/ssl/certs/cacert.pem
                        sync
                    else
                        echo "Checksum validation for downloaded CA certificate failed."
                        continue
                    fi

                    [ "${RO_ROOT}" == "true" ] && mount / -o remount,ro
                    echo
                    export CURL_SSL="--cacert /etc/ssl/certs/cacert.pem"
                    continue
                fi

                set +e
                dialog --keep-window --title "Insecure Connection" --defaultno \
                    --yesno "Would you like to run this tool using an insecure connection?\n\nNOTE: You should fix the certificates instead." \
                    7 67
                DIALOG_RET=$?
                set -e

                if [[ "${DIALOG_RET}" == "0" ]] ; then
                    echo
                    echo "WARNING! Connection is insecure."
                    export CURL_SSL="--insecure"
                    sleep 5s
                    echo
                    continue
                fi

                echo "No secure connection is possible without fixing the certificates."
                exit 1
                ;;
            *)
                echo "No Internet connection, please try again later."
                exit 1
                ;;
        esac
    done

    echo "Internet connection failed, please try again later."
    exit 1
}

echo "Running MiSTer Downloader"
echo

rm ${SCRIPT_PATH} 2> /dev/null || true

if [ -s "${LATEST_SCRIPT_PATH}" ] ; then
    cp "${LATEST_SCRIPT_PATH}" "${SCRIPT_PATH}"
    if [[ "${CURL_SSL:-}" != "--insecure" ]] ; then
        download_file "/dev/null" "https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/downloader.sh"
    fi
else
    download_file "${SCRIPT_PATH}" "https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/dont_download.sh"
fi

chmod +x "${SCRIPT_PATH}"

export DOWNLOADER_LAUNCHER_PATH="${BASH_SOURCE[0]}"

if ! "${SCRIPT_PATH}" ; then
    echo -e "Downloader failed!\n"
    exit 1
fi

rm ${SCRIPT_PATH} 2> /dev/null || true

exit 0
