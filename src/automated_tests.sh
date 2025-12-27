#!/usr/bin/env bash
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

cd src
echo "Unit Tests:"
python3 -m unittest discover -s test/unit
echo
echo "Integration Tests:"
python3 -m unittest discover -s test/integration
echo
echo "System Quick Tests:"
python3 -m unittest discover -s test/system/quick -v
echo

if [[ "${1:-}" != "--slow" ]] && [[ "${1:-}" != "-s" ]] ; then
    echo "Done. For running all system tests do: ${0} --slow"
    exit 0
fi

echo "System Slow Tests:"
python3 -m unittest discover -s test/system/slow -v
echo
echo "Done"