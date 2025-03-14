#!/usr/bin/env bash
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

DOWNLOADER_ZIP="downloader.zip"
TEMP_ZIP2="${ZIP_FILE:-$(mktemp -u).zip}"
BIN="/tmp/dont_download.zip"
TEMPDIR="$(mktemp -d)"

pin_metadata() {
  touch -a -m -t 202108231405 "${1}"
}

cd src

cp -r downloader "${TEMPDIR}/downloader"
echo "default_commit = '$(git rev-parse --short HEAD)'" > "${TEMPDIR}/commit.py"
cp __main__.py "${TEMPDIR}/__main__.py"
if [[ "${SKIP_REMOVALS:-false}" != "true" ]] ; then
  find "${TEMPDIR}" -type f -name '*.py' -exec perl -i -0pe 's/"""(.*?)"""/""/sg; s/^\s*#.*\n//mg; s/^\s*\n//mg' {} +
fi
#if which strip-hints > /dev/null ; then
#  find "${TEMPDIR}" -type f -name '*.py' -exec strip-hints --inplace {} \; 2> /dev/null
#fi
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
tail -n +8 "\${0}" | xzcat -d -c > "${BIN}"
chmod a+x "${BIN}"
"${BIN}" "\${1:-}"
exit 0
EOF

xzcat -z < "${TEMP_ZIP2}"

rm -rf "${TEMPDIR}" >/dev/null 2>&1
