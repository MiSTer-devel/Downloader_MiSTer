#!/usr/bin/env python3
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

import subprocess
import os
import time

subprocess.run(['git', 'add', 'dont_download.sh', 'latest.id'], check=True)
subprocess.run(['git', 'commit', '-m', 'BOT: New dont_download.sh'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

subprocess.run(['git', 'fetch', 'origin', 'main'], check=True)

diff_output = subprocess.run(['git', 'diff', 'main:latest.id', 'origin/main:latest.id'], capture_output=True, text=True, check=True).stdout
lines = diff_output.split('\n')
changes = [line for line in lines if line.startswith('+') or line.startswith('-')]
changes = [line for line in changes if not line.startswith('+++') and not line.startswith('---') and 'export COMMIT' not in line]

if len(changes) >= 1:
    print("There are changes to push:\n")
    print(diff_output)
    print('...\n')
    print(changes)
    print('...\n')
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)

    has_latest = subprocess.run(['gh', 'release', 'list'], capture_output=True, text=True)
    if "latest" not in has_latest.stdout:
        subprocess.run(['gh', 'release', 'create', 'latest'], stderr=subprocess.DEVNULL)
        time.sleep(15)

    result = subprocess.run(['md5sum', 'dont_download.zip'], capture_output=True, check=True, text=True)
    with open('dont_download.zip.md5', 'w') as f:
        f.write(result.stdout)

    subprocess.run(['gh', 'release', 'upload', 'latest', 'dont_download.zip', '--clobber'], check=True)
    subprocess.run(['gh', 'release', 'upload', 'latest', 'dont_download.zip.md5', '--clobber'], check=True)
    subprocess.run(['gh', 'release', 'upload', 'latest', 'src/downloader.zip', '--clobber'], check=True)

    print("\nNew dont_download.sh can be used.")
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write("NEW_RELEASE=yes\n")
else:
    print("Nothing to be updated.")
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write("NEW_RELEASE=no\n")
