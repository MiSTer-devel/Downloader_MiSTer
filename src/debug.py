#!/usr/bin/env python3
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

import os
import sys
import tempfile
import subprocess
import time
import argparse
import traceback
from pathlib import Path


def chdir_root(): os.chdir(str(Path(__file__).parent.parent))
def read_file_or(file, default): return open(file, 'r').read().strip() if os.path.exists(file) else default
def mister_ip(): return os.environ.get('MISTER_IP', read_file_or('mister.ip', None))
def mister_pw(): return read_file_or('mister.pw', '1')
def scp_path(p): return f'root@{mister_ip()}:{p}' if p.startswith('/media') else p
def exports(env=None, **_kwargs): return " ".join(f"export {key}={value};" for key, value in (env or {}).items())
def scp_file(src, dest, **kwargs): _ssh_pass('scp', [scp_path(src), scp_path(dest)], **kwargs)
def exec_ssh(cmd, **kwargs): return _ssh_pass('ssh', [f'root@{mister_ip()}', f'{exports(**kwargs)}{cmd}'], **kwargs)
def run_build(**kwargs): send_build(**kwargs) if _skip_send(**kwargs) else None, exec_ssh(f'/media/fat/downloader.sh', **kwargs)
def run_launcher(**kwargs): send_build(**kwargs) if _skip_send(**kwargs) else None, exec_ssh(f'/media/fat/Scripts/downloader.sh', **kwargs)
def run_compile(**kwargs): send_compile(**kwargs), exec_ssh(f'/media/fat/downloader_bin', **kwargs)
def store_push(ws='', **kwargs): scp_file('downloader.json', f'/media/fat/{ws}Scripts/.config/downloader/downloader.json', **kwargs)
def store_pull(ws='', **kwargs): scp_file(f'/media/fat/{ws}Scripts/.config/downloader/downloader.json', 'downloader.json', **kwargs)
def log_pull(ws='', **kwargs): scp_file(f'/media/fat/{ws}Scripts/.config/downloader/downloader.log', 'downloader.log', **kwargs)

def _skip_send(env=None, **_kwargs): return env is None or not env.get('SKIP_SEND', True)

def send_build(env=None, **kwargs):
    env = {"SKIP_REMOVALS": "true", 'DEBUG': 'true', **os.environ.copy(), **(env or {}), 'MISTER': 'true'}
    with tempfile.NamedTemporaryFile(delete=False) as tmp: subprocess.run(['./src/build.sh'], stderr=sys.stdout, stdout=tmp, env=env, check=True)
    os.chmod(tmp.name, 0o755)

    if os.path.exists('dont_download.ini'): scp_file('dont_download.ini', '/media/fat/downloader.ini', **kwargs)

    scp_file(tmp.name, '/media/fat/downloader.sh', **kwargs)
    scp_file('downloader.sh', '/media/fat/Scripts/downloader.sh', **kwargs)

    os.remove(tmp.name)

def send_compile(env=None, **kwargs):
    env = {'DEBUG': 'true', **os.environ.copy(), **(env or {}), 'MISTER': 'true'}
    subprocess.run(['./src/compile.sh', 'downloader_bin'], check=True, env=env)
    os.chmod('downloader_bin', 0o755)
    scp_file('downloader_bin', '/media/fat/downloader_bin', **kwargs)

def _ssh_pass(cmd, args, out=None, retries=True, **kwargs):
    for i in range(4):
        try: return subprocess.run(['sshpass', '-p', mister_pw(), cmd, '-o', 'StrictHostKeyChecking=no', *args], check=True, stdout=out)
        except subprocess.CalledProcessError as e:
            if not retries or i >= 3: raise e
            traceback.print_exc()
            time.sleep(30 * (i + 1))

def operations_dict(**kwargs):
    return {
        'store_push': lambda: [store_push(**kwargs), print('OK')],
        'store_pull': lambda: [store_pull(**kwargs), print('OK')],
        'log_pull': lambda: [log_pull(**kwargs), print('OK')],
        'build': lambda: [send_build(**kwargs), print('OK')],
        'run': lambda: run_build(**kwargs),
        'compile': lambda: [send_compile(**kwargs), print('OK')],
        'run_compile': lambda: run_compile(**kwargs),
        'launcher': lambda: run_launcher(**kwargs),
        'copy': lambda: [scp_file(sys.argv[2], f'/media/fat/{sys.argv[2]}'), print('OK')],
        'rcopy': lambda: [scp_file(f'/media/fat/{sys.argv[2]}', sys.argv[2]), print('OK')],
    }

def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=list(operations_dict()), nargs='?', default=None)
    parser.add_argument('parameter', nargs='?', default='')
    parser.add_argument('--retries', help='Enable retries on SSH commands')
    parser.add_argument('--ws', help='Different workspace', default='')
    args = parser.parse_args()

    operations = operations_dict(retries=args.retries, ws=args.ws, env=os.environ.copy())
    op = operations.get(args.command, operations['build'])
    op()

if __name__ == '__main__':
    _main()
