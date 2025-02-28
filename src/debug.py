#!/usr/bin/env python3
# Copyright (c) 2021-2023 José Manuel Barroso Galindo <theypsilon@gmail.com>

import os
import sys
import tempfile
import subprocess
import time
import zipfile
import argparse
import traceback
from pathlib import Path


def chdir_root(): os.chdir(str(Path(__file__).parent.parent))
def read_file_or(file, default): return open(file, 'r').read().strip() if os.path.exists(file) else default
def mister_ip(): return os.environ.get('MISTER_IP', read_file_or('mister.ip', None))
def mister_pw(): return read_file_or('mister.pw', '1')
def scp_path(p): return f'root@{mister_ip()}:{p}' if p.startswith('/media') else p
def exports(env=None): return " ".join(f"export {key}={value};" for key, value in (env or {}).items())
def scp_file(src, dest, **kwargs): _ssh_pass('scp', [scp_path(src), scp_path(dest)], **kwargs)
def exec_ssh(cmd, env=None, **kwargs): return _ssh_pass('ssh', [f'root@{mister_ip()}', f'{exports(env)}{cmd}'], **kwargs)
def run_build(**kwargs): send_build(env={"SKIP_REMOVALS": "true"}), exec_ssh(f'/media/fat/downloader.sh', **kwargs)
def run_launcher(**kwargs): send_build(**kwargs), exec_ssh(f'/media/fat/Scripts/downloader.sh', **kwargs)
def run_compile(**kwargs): send_compile(**kwargs), exec_ssh(f'/media/fat/downloader_bin', **kwargs)
def store_push(**kwargs): scp_file('downloader.json', '/media/fat/Scripts/.config/downloader/downloader.json', **kwargs)
def store_pull(**kwargs): scp_file('/media/fat/Scripts/.config/downloader/downloader.json', 'downloader.json', **kwargs)
def log_pull(**kwargs): scp_file('/media/fat/Scripts/.config/downloader/downloader.log', 'downloader.log', **kwargs)

def send_build(env=None, **kwargs):
    env = {'DEBUG': 'true', **os.environ.copy(), **(env or {}), 'MISTER': 'true'}
    with tempfile.NamedTemporaryFile(delete=False) as tmp: subprocess.run(['./src/build.sh'], stdout=tmp, env=env, check=True)
    os.chmod(tmp.name, 0o755)

    if os.path.exists('dont_download.ini'): scp_file('dont_download.ini', '/media/fat/downloader.ini', **kwargs)

    scp_file(tmp.name, '/media/fat/downloader.sh', **kwargs)
    scp_file('downloader.sh', '/media/fat/Scripts/downloader.sh', **kwargs)

    os.remove(tmp.name)

def send_compile(env=None, **kwargs):
    with tempfile.NamedTemporaryFile(delete=False) as tmp: subprocess.run(['./src/compile.sh'], stdout=tmp, env=env, check=True)
    os.chmod(tmp.name, 0o755)
    scp_file(tmp.name, '/media/fat/downloader_bin', **kwargs)
    os.remove(tmp.name)

def operations_dict(env=None, retries=False):
    return {
        'store_push': lambda: store_push(retries=retries),
        'store_pull': lambda: store_pull(retries=retries),
        'log_pull': lambda: log_pull(retries=retries),
        'build': lambda: [send_build(env=env, retries=retries), print('OK')],
        'run': lambda: run_build(env=env, retries=retries),
        'compile': lambda: send_compile(env=env, retries=retries),
        'run_compile': lambda: run_compile(env=env, retries=retries),
        'launcher': lambda: run_launcher(env=env, retries=retries),
        'copy': lambda: scp_file(sys.argv[2], f'/media/fat/{sys.argv[2]}'),
    }

def _ssh_pass(cmd, args, out=None, retries=True):
    for i in range(4):
        try: return subprocess.run(['sshpass', '-p', mister_pw(), cmd, '-o', 'StrictHostKeyChecking=no', *args], check=True, stdout=out)
        except subprocess.CalledProcessError as e:
            if not retries or i >= 3: raise e
            traceback.print_exc()
            time.sleep(30 * (i + 1))

def _main():
    operations = operations_dict()
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=list(operations), nargs='?', default=None)
    parser.add_argument('parameter', nargs='?', default='')
    op = operations.get(parser.parse_args().command, operations['build'])
    op()

if __name__ == '__main__':
    _main()
