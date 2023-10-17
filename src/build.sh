#!/usr/bin/env bash
# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

DOWNLOADER_ZIP="downloader.zip"
TEMP_ZIP2="${ZIP_FILE:-$(mktemp -u).zip}"
BIN="/tmp/dont_download.zip"
UUDECODE_CMD=$({ [[ "${MISTER:-false}" == "false" ]] && [[ "$(uname -s)" == "Darwin" ]] ; } && echo "uudecode -p" || echo "uudecode -o -")
TEMPDIR="$(mktemp -d)"

pin_metadata() {
  touch -a -m -t 202108231405 "${1}"
}

cd src

cp -r downloader "${TEMPDIR}/downloader"
echo "default_commit = '$(git rev-parse --short HEAD)'" > "${TEMPDIR}/commit.py"
cp __main__.py "${TEMPDIR}/__main__.py"
find "${TEMPDIR}" -type f -name '*.py' -exec perl -i -0pe 's/"""(.*?)"""/""/sg; s/^\s*#.*\n//mg; s/^\s*\n//mg' {} +
find "${TEMPDIR}" -type f ! -name '*.py' -exec rm -f {} +
find "${TEMPDIR}" -type f -iname "*.py" -print0 | while IFS= read -r -d '' file ; do pin_metadata "${file}" ; done
pushd "${TEMPDIR}" >/dev/null 2>&1
zip -q -0 -D -X -A -r "${DOWNLOADER_ZIP}" __main__.py commit.py downloader -x "*/__pycache__/*"
pin_metadata "${DOWNLOADER_ZIP}"
echo '#!/usr/bin/env python3' | cat - "${DOWNLOADER_ZIP}" > "${TEMP_ZIP2}"
pin_metadata "${TEMP_ZIP2}"
popd >/dev/null 2>&1
cp "${TEMPDIR}/${DOWNLOADER_ZIP}" .
cd ..

cat <<-EOF
#!/usr/bin/env bash
set -euo pipefail
export DOWNLOADER_LAUNCHER_PATH="\${DOWNLOADER_LAUNCHER_PATH:-\${0}}"
${UUDECODE_CMD} "\${0}" | xzcat -d -c > "${BIN}"
chmod a+x "${BIN}"
"${BIN}" "\${1:-}"
exit 0
EOF

uuencode - < <(xzcat -z < "${TEMP_ZIP2}")

rm -rf "${TEMPDIR}" >/dev/null 2>&1
