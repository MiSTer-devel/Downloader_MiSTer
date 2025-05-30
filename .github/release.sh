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
md5sum('src/downloader.zip', 'downloader.zip.md5')
md5sum('src/downloader_bin', 'downloader_bin.md5')

subprocess.run(['git', 'add', 'dont_download.sh', 'latest.id'], check=True)
subprocess.run(['git', 'commit', '-m', 'BOT: New dont_download.sh'], check=True)
subprocess.run(['git', 'push', 'origin', 'main'], check=True)

subprocess.run([
    'gh', 'release', 'upload', 'latest', '--clobber',
    'dont_download.zip',
    'dont_download.zip.md5',
    'src/downloader.zip',
    'downloader.zip.md5',
    'src/downloader_bin',
    'downloader_bin.md5'
  ], check=True)
