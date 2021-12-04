#!/usr/bin/env bash
# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

TEMP_ZIP1="$(mktemp -u).zip"
TEMP_ZIP2="$(mktemp -u).zip"
BIN="/tmp/dont_download.zip"
COMMIT="$(git rev-parse --short HEAD)"

pin_metadata() {
  touch -a -m -t 202108231405 "${1}"
}

cd src

find downloader -type f -iname "*.py" -print0 | while IFS= read -r -d '' file ; do pin_metadata "${file}" ; done
pin_metadata __main__.py
zip -q -0 -D -X -A -r "${TEMP_ZIP1}" __main__.py downloader -x "*/__pycache__/*"
pin_metadata "${TEMP_ZIP1}"
echo '#!/usr/bin/env python3' | cat - "${TEMP_ZIP1}" > "${TEMP_ZIP2}"
pin_metadata "${TEMP_ZIP2}"
rm "${TEMP_ZIP1}"
cd ..

cat <<-EOF
#!/usr/bin/env bash
set -euo pipefail
export DOWNLOADER_LAUNCHER_PATH="\${DOWNLOADER_LAUNCHER_PATH:-\${0}}"
export COMMIT="${COMMIT}"
uudecode -o - "\${0}" | xzcat -d -c > "${BIN}"
chmod a+x "${BIN}"
"${BIN}"
exit 0
EOF

uuencode - < <(xzcat -z < "${TEMP_ZIP2}")
rm "${TEMP_ZIP2}" > /dev/null 2>&1 || true
