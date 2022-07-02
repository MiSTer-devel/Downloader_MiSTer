#!/usr/bin/env bash
set -euo pipefail
export DOWNLOADER_LAUNCHER_PATH="${DOWNLOADER_LAUNCHER_PATH:-${0}}"
export COMMIT=fee2378
uudecode -o - "${0}" | xzcat -d -c > "/tmp/dont_download.zip"
chmod a+x "/tmp/dont_download.zip"
"/tmp/dont_download.zip" "${1:-}"
exit 0
begin 644 -
`
end
