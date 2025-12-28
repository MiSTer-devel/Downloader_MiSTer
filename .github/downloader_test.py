#!/usr/bin/env python3
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

import argparse
import os
import subprocess
import tempfile


def test(db_id: str, db_url: str):
    with tempfile.TemporaryDirectory() as temp_folder:
        downloader_source = os.environ.get('DOWNLOADER_SOURCE', 'https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/dont_download.sh')

        if downloader_source.startswith('http://') or downloader_source.startswith('https://'):
            log(f'downloading downloader.sh from {downloader_source}')
            curl(downloader_source, temp_folder + '/downloader.sh')
        else:
            log(f'copying downloader.sh from {downloader_source}')
            run(['cp', downloader_source, temp_folder + '/downloader.sh'])

        run(['chmod', '+x', 'downloader.sh'], cwd=temp_folder)

        downloader_ini_content = f"""
            [MiSTer]
            base_path = {temp_folder}/
            base_system_path = {temp_folder}/
            update_linux = false
            allow_reboot  = 0
            verbose = false
            downloader_retries = 0
    
            [{db_id}]
            db_url = {db_url}
        """
        log('downloader.ini content:')
        log(downloader_ini_content)

        with open(temp_folder + '/downloader.ini', 'w') as fini:
            fini.write(downloader_ini_content)

        run(['./downloader.sh'], cwd=temp_folder,
            env={'DEBUG': 'true', 'LOGLEVEL': 'debug', 'CURL_SSL': '', 'SKIP_FREE_SPACE_CHECKS': 'true'})

def run(commands, env=None, cwd=None):
    log(' '.join(commands))
    if env is not None: log('with env:', env)
    if cwd is not None: log('with cwd:', cwd)
    subprocess.run(commands, cwd=cwd, env=env, check=True, stderr=subprocess.STDOUT)

def curl(url, output_path):
    log(f'Downloading {url} to {output_path}')
    run(['curl', '--fail', '--location', '--output', output_path, url])

def log(*text):
    print(*text, flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test downloader with custom database')
    parser.add_argument('db_id', help='Database ID (e.g., distribution_mister)')
    parser.add_argument('db_url', help='Database URL')
    args = parser.parse_args()
    test(db_id=args.db_id, db_url=args.db_url)
