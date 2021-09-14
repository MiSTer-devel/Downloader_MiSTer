#!/usr/bin/env bash
# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

cd src
echo "Unit Tests:"
python3 -m unittest discover -s test/unit
echo
echo "Integration Tests:"
python3 -m unittest discover -s test/integration
