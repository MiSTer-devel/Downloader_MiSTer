#!/usr/bin/env python3
# Copyright (c) 2021-2024 José Manuel Barroso Galindo <theypsilon@gmail.com>

import subprocess
import os
import time

subprocess.run(['git', 'add', 'dont_download.sh'], check=True)
subprocess.run(['git', 'commit', '-m', 'BOT: New dont_download.sh'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

subprocess.run(['git', 'fetch', 'origin', 'main'], check=True)

diff_cmd = "git diff main:dont_download.sh origin/main:dont_download.sh"
filter_cmd = "grep '^[+-]' | grep -v 'export COMMIT' | grep -v '^\+\+\+' | grep -v '^---'"
changes = subprocess.getoutput(f"{diff_cmd} | {filter_cmd} | wc -l")

if int(changes) >= 1:
    print("There are changes to push:\n")
    print(changes)
    print()
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)

    has_latest = subprocess.run(['gh', 'release', 'list'], capture_output=True, text=True)
    if "latest" not in has_latest.stdout:
        subprocess.run(['gh', 'release', 'create', 'latest'], stderr=subprocess.DEVNULL)

    time.sleep(15)

    subprocess.run(['md5sum', 'dont_download.zip', '>', 'dont_download.zip.md5'], shell=True)

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
