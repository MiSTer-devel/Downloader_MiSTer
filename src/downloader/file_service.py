# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# You can download the latest version of this tool from:
# https://github.com/MiSTer-devel/Downloader_MiSTer

import os
import hashlib
from pathlib import Path
import shutil
import json
from .other import run_stdout, run_successfully
from .config import AllowDelete
import subprocess


class FileService:
    def __init__(self, config, logger):
        self._config = config
        self._logger = logger
        self._system_paths = set()

    def add_system_path(self, path):
        self._system_paths.add(path)

    def is_file(self, path):
        return os.path.isfile(self._path(path))

    def read_file_contents(self, path):
        with open(self._path(path), 'r') as f:
            return f.read()

    def write_file_contents(self, path, content):
        with open(self._path(path), 'w') as f:
            return f.write(content)

    def touch(self, path):
        return Path(self._path(path)).touch()

    def move(self, source, target):
        os.makedirs(str(Path(self._path(target)).parent), exist_ok=True)
        os.replace(self._path(source), self._path(target))

    def copy(self, source, target):
        return shutil.copyfile(self._path(source), self._path(target))

    def hash(self, path):
        return hash_file(self._path(path))

    def makedirs(self, path):
        return os.makedirs(self._path(path), exist_ok=True)

    def makedirs_parent(self, path):
        return os.makedirs(str(Path(self._path(path)).parent), exist_ok=True)

    def folder_has_items(self, path):
        result = False
        for _ in os.scandir(self._path(path)):
            result = True
        return result

    def folders(self):
        raise Exception('folders Not implemented')

    def remove_folder(self, path):
        if self._config['allow_delete'] != AllowDelete.ALL:
            return

        self._logger.print('Deleting empty folder %s' % path)
        os.rmdir(self._path(path))

    def curl_target_path(self, path):
        return self._path(path)

    def unlink(self, path):
        verbose = not path.startswith('/tmp/')
        if self._config['allow_delete'] != AllowDelete.ALL:
            if self._config['allow_delete'] == AllowDelete.OLD_RBF and path[-4:].lower() == ".rbf":
                return self._unlink(path, verbose)

            return True

        return self._unlink(path, verbose)

    def clean_expression(self, expr):
        if self._config['allow_delete'] != AllowDelete.ALL:
            return True

        if expr[-1:] == '*':
            self._logger.debug('Cleaning %s ' % Path(expr).name, end='')
            result = subprocess.run('rm "%s"*' % self._path(expr[0: -1]), shell=True, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        else:
            return self._unlink(expr, True)

    def load_db_from_file(self, path, suffix=None):
        path = self._path(path)
        if suffix is None:
            suffix = Path(path).suffix.lower()
        if suffix == '.json':
            return self._load_json(path)
        elif suffix == '.zip':
            return self._load_json_from_zip(path)
        else:
            raise Exception('File type "%s" not supported' % suffix)

    def _load_json_from_zip(self, path):
        json_str = run_stdout("unzip -p %s" % path)
        return json.loads(json_str)

    def _load_json(self, file_path):
        with open(file_path, "r") as f:
            return json.loads(f.read())

    def save_json_on_zip(self, db, path):
        json_name = Path(path).stem
        json_path = '/tmp/%s' % json_name
        with open(json_path, 'w') as f:
            json.dump(db, f)

        zip_path = Path(self._path(path)).absolute()

        run_successfully('cd /tmp/ && zip -qr -0 %s %s' % (zip_path, json_name), self._logger)

        self._unlink(json_path, False)

    def unzip_contents(self, file, path):
        result = subprocess.run(['unzip', '-q', '-o', self._path(file), '-d', self._path(path)], shell=False, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            raise Exception("Could not unzip %s: %s" % (file, result.returncode))
        self._unlink(self._path(file), False)

    def _unlink(self, path, verbose):
        if verbose:
            self._logger.print('Removing %s' % path)
        try:
            Path(self._path(path)).unlink()
            return True
        except Exception as _:
            return False

    def _path(self, path):
        if path[0] == '/':
            return path

        base_path = self._config['base_system_path'] if path in self._system_paths else self._config['base_path']

        return '%s/%s' % (base_path, path)


def hash_file(path):
    with open(path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
        return file_hash.hexdigest()
