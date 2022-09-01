#!/usr/bin/env bash
# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

export CACERT_PATH="/etc/ssl/certs/cacert.pem" # Default path for cacert.pem in MiSTer distro

# download_file: downloads <url> to <file>
download_file() {
    local DOWNLOAD_PATH="${1}"
    local DOWNLOAD_URL="${2}"

    # Loop: 1 time + 60 retries fixing SSL = 61 attempts
    for (( COUNTER=0; COUNTER<=60; COUNTER+=1 )); do

        # The first time do not sleep.
        # For every other time, sleep for 1 second. This is to avoid hitting the server too hard.
        if [ ${COUNTER} -ge 1 ] ; then
            echo "Before rertying #${COUNTER}: wait a second..."
            sleep 1s
        fi

        set +e # Disable errexit so we can catch the return code from curl, if it fails.
        # --fail: Fail silently (no output at all) on server errors.
        # --location: Follow any redirections.
        # --output: Write the output to a file.
        curl ${CURL_SSL:-} --fail --location --output "${DOWNLOAD_PATH}" "${DOWNLOAD_URL}" &> /dev/null
        local CMD_RET=$?
        set -e # Enable errexit, now that we've caught the return code from curl.

        # Decide what to do based on the return code from curl.
        case ${CMD_RET} in
            0)
                export CURL_SSL="${CURL_SSL:-}"
                return
                ;;
            60)
                if [ -f ${CACERT_PATH} ] ; then
                    export CURL_SSL="--cacert ${CACERT_PATH}"
                    continue
                fi

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
                    echo; echo "Installing cacert.pem from https://curl.se"
                    curl --insecure --location -o ${CACERT_PATH} "https://curl.se/ca/cacert.pem"
                    sync
                    [ "${RO_ROOT}" == "true" ] && mount / -o remount,ro
                    echo
                    echo "Done. SSL certificates have been fixed."
                    export CURL_SSL="--cacert ${CACERT_PATH}"
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
                    echo
                    continue
                fi

                echo "No secure connection is possible without fixing the certificates."
                exit 1
                ;;
            # Command not found, Please install curl
            127)
                echo "curl is not installed. File a bug report at 'https://github.com/MiSTer-devel/Distribution_MiSTer'"
                exit 1
                ;;

             # If curl returns a non-zero return code (except 60, that means certs have issues), then exit.
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

SCRIPT_PATH="/tmp/downloader.sh"

# Delete the downloader script if it already exists.
rm ${SCRIPT_PATH} 2> /dev/null || true

# Download the 'dont_download.sh' script.
download_file "${SCRIPT_PATH}" "https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/dont_download.sh"

chmod +x "${SCRIPT_PATH}"

# Run the 'dont_download.sh' script.
export DOWNLOADER_LAUNCHER_PATH="${BASH_SOURCE[0]}"

if ! "${SCRIPT_PATH}" ; then
    echo -e "Downloader failed!\n"
    exit 1
fi

rm ${SCRIPT_PATH} 2> /dev/null || true

exit 0
