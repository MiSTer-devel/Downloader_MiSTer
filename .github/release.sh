#!/usr/bin/env python3
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

import subprocess
import time

def md5sum(source_file, target_file):
    result = subprocess.run(['md5sum', source_file], capture_output=True, check=True, text=True)
    with open(target_file, 'w') as f:
        f.write(result.stdout)

has_latest = subprocess.run(['gh', 'release', 'list'], capture_output=True, text=True)
if "latest" not in has_latest.stdout:
    subprocess.run(['gh', 'release', 'create', 'latest'], stderr=subprocess.DEVNULL)
    time.sleep(15)

md5sum('dont_download.zip', 'dont_download.zip.md5')

old_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()

subprocess.run(['git', 'add', 'dont_download.sh', 'latest.id'], check=True)
subprocess.run(['git', 'commit', '-m', 'BOT: New dont_download.sh'], check=True)
subprocess.run(['git', 'push', 'origin', 'main'], check=True)

try:
    subprocess.run([
        'gh', 'release', 'upload', 'latest', '--clobber',
        'dont_download.zip',
        'dont_download.zip.md5',
        'downloader.zip',
        'downloader_bin',
    ], check=True)
except:
    subprocess.run(['git', 'push', '--force', 'origin', f'{old_commit}:refs/heads/main'], check=True)
    raise
