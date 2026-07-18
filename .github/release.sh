#!/usr/bin/env python3
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

import subprocess
import time
from pathlib import Path


def md5sum(source_file, target_file):
    result = subprocess.run(['md5sum', source_file], capture_output=True, check=True, text=True)
    with open(target_file, 'w') as f:
        f.write(result.stdout)


def read_release_patch(path):
    value = Path(path).read_text(encoding='utf-8').strip()
    if not value.isascii() or not value.isdigit() or str(int(value)) != value:
        raise ValueError(f'Invalid release patch in {path}: {value!r}')
    return int(value)


def validate_next_release_patch(current_path, next_path):
    current_release_patch = read_release_patch(current_path)
    next_release_patch = read_release_patch(next_path)
    if next_release_patch != current_release_patch + 1:
        raise ValueError(
            f'Release patch {next_release_patch} does not follow {current_release_patch}.'
        )
    return next_release_patch


def rollback_release(old_commit, bot_commit):
    subprocess.run([
        'git',
        'push',
        f'--force-with-lease=refs/heads/main:{bot_commit}',
        'origin',
        f'{old_commit}:refs/heads/main',
    ], check=True)


def main():
    next_release_patch = validate_next_release_patch('.github/release_patch', 'release_patch')

    has_latest = subprocess.run(['gh', 'release', 'list'], capture_output=True, text=True)
    if "latest" not in has_latest.stdout:
        subprocess.run(['gh', 'release', 'create', 'latest'], stderr=subprocess.DEVNULL)
        time.sleep(15)

    md5sum('dont_download.zip', 'dont_download.zip.md5')

    old_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    Path('.github/release_patch').write_text(f'{next_release_patch}\n', encoding='utf-8')

    subprocess.run(['git', 'add', '.github/release_patch', 'dont_download.sh', 'latest.id'], check=True)
    subprocess.run(['git', 'commit', '-m', 'BOT: New dont_download.sh'], check=True)
    bot_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
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
        rollback_release(old_commit, bot_commit)
        raise


if __name__ == '__main__':
    main()
