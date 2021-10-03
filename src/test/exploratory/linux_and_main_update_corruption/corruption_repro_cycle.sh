#!/usr/bin/env python3

import subprocess
import time
import sys
import os
import hashlib
from datetime import datetime
from pathlib import Path
from shutil import copy2

class Logger:
    def __init__(self, file):
        self._logfile = file
        self._local_repository = None

    def print(self, *args, sep='', end='\n', flush=True):
        now = datetime.now()
        print('[%s] ' % now, *args, sep=sep, end=end, file=sys.stdout, flush=flush)
        print('[%s] ' % now, *args, sep=sep, end=end, file=self._logfile, flush=flush)

repro_log = open('/media/fat/repro.log', 'a+')
logger = Logger(repro_log)

def hash_file(path):
    with open(path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
        return file_hash.hexdigest()

def test_main_hash(expected_hash):
  if not Path('/media/fat/MiSTer').exists():
    return
  actual_hash = hash_file('/media/fat/MiSTer')
  if expected_hash != actual_hash:
    logger.print('Got it!')
    logger.print('%s != %s' % (expected_hash, actual_hash))
    copy2('/media/fat/repro.log', '/media/fat/failed_repro.log')
    exit()

connected = False
while not connected:
  process_result = subprocess.run(['curl', '--insecure', 'https://www.github.com/'], shell=False, stderr=subprocess.STDOUT, stdout=subprocess.DEVNULL)

  if process_result.returncode == 0:
    connected = True
  else:
    logger.print('*')
    time.sleep(5)

time.sleep(1)
logger.print('START!')
logger.print('Argument List:' + str(sys.argv))
logger.print()

subprocess.run(['ps', '-o', 'pid,user,ppid,args'], shell=False, stderr=repro_log, stdout=repro_log)
logger.print('PARENT ID: ' + str(os.getppid()))
logger.print()

repro_semaphore = '/media/fat/repro_semaphore'
db_url = None
if Path(repro_semaphore).exists():
  db_url = '/media/fat/db1.json'
  logger.print('DB 1!')
  Path(repro_semaphore).unlink()
  test_main_hash('e82a5f13cf9561f5db31e6b630e6d323')
else:
  db_url ='/media/fat/db2.json'
  logger.print('DB 2!')
  Path(repro_semaphore).touch()
  test_main_hash('f782dd65a0d548f7cda6eba1e2b05f36')

with open('/media/fat/corruption_downloader.ini', 'w') as f:
  f.write('[mister]\n')
  f.write('allow_reboot = 0\n')
  f.write('verbose = true\n')
  f.write('[repro_test]\n')
  f.write('db_url = "%s"\n' % db_url)

os.environ["CURL_SSL"] = "--insecure"

try:
  Path('/tmp/downloader_needs_reboot_after_linux_update').unlink()
  logger.print('Removed file: /tmp/downloader_needs_reboot_after_linux_update')
except:
  logger.print('Did NOT remove /tmp/downloader_needs_reboot_after_linux_update')

tail = subprocess.Popen(['tail', '-n', '0', '-f', 'repro.log'], shell=False)
subprocess.run(['/media/fat/corruption_downloader.sh'], shell=False, stderr=repro_log, stdout=repro_log)
tail.kill()

logger.print('Rebooting manually in 10...')

time.sleep(2)
repro_log.close()
time.sleep(4)
subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)
time.sleep(4)
subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)
time.sleep(30)
subprocess.run(['reboot', 'now'], shell=False, stderr=subprocess.STDOUT)
#subprocess.run(['fpga', '0xffd05054', '0'], shell=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
#subprocess.Popen(['fpga', '0xffd05004', '2'], shell=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
