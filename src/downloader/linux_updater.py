# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import subprocess
import json
import sys
import tempfile
import os.path
from typing import Dict, List
from downloader.config import Config
from downloader.constants import FILE_7z_util_uninstalled, FILE_7z_util_uninstalled_description, FILE_Linux_uninstalled, FILE_downloader_needs_reboot_after_linux_update, FILE_MiSTer_version, FILE_7z_util, FILE_Linux_user_files
from downloader.db_entity import DbEntity
from downloader.file_system import FileSystem
from downloader.jobs.fetch_file_worker import SafeFileFetcher
from downloader.logger import Logger


class LinuxUpdater:
    def __init__(self, logger: Logger, config: Config, file_system: FileSystem, fetcher: SafeFileFetcher):
        self._config = config
        self._logger = logger
        self._file_system = file_system
        self._fetcher = fetcher
        self._linux_descriptions = []
        self._user_files = []

    def update_linux(self, dbs: List[DbEntity]):
        self._logger.bench('Update Linux start.')
        self._update_linux_impl(dbs)
        self._logger.bench('Update Linux done.')

    def _update_linux_impl(self, dbs: List[DbEntity]) -> None:
        for db in dbs:
            if db.linux is not None:
                self._linux_descriptions.append({
                    'id': db.db_id,
                    'args': db.linux
                })

        linux_descriptions_count = len(self._linux_descriptions)
        if linux_descriptions_count == 0:
            self._logger.debug('linux_descriptions_count: 0')
            return

        if linux_descriptions_count > 1:
            self._logger.print('Too many databases try to update linux.')
            self._logger.print('Only 1 can be processed.')
            self._logger.print('Ignoring:')
            for ignored in self._linux_descriptions[1:]:
                self._logger.print(' - %s' % ignored['id'])
            self._logger.print()

        description = self._linux_descriptions[0]

        linux = description['args']
        self._logger.debug('linux: ' + json.dumps(linux, indent=4))

        current_linux_version = self.get_current_linux_version()
        if current_linux_version == linux['version'][-6:]:
            self._logger.debug('current_linux_version "%s" matches db linux: %s' % (current_linux_version, linux['version']))
            return

        for source, destination in FILE_Linux_user_files:
            if self._file_system.is_file(source):
                self._logger.print('Custom "%s" file will be installed to the updated Linux system from the "linux" folder.' % (os.path.basename(source)))
                self._user_files.append((source, destination))

        self._logger.print('Linux will be updated from %s:' % description['id'])
        self._logger.print('Current linux version -> %s' % current_linux_version)
        self._logger.print('Latest linux version -> %s' % linux['version'][-6:])
        self._logger.print()

        self._logger.print('Fetching the new Linux image...')
        error = self._fetcher.fetch_file(linux, FILE_Linux_uninstalled)
        if error is not None:
            self._logger.print('ERROR! Could not fetch the Linux image.')
            self._logger.print(error)
            return

        if not self._file_system.is_file(FILE_7z_util):
            self._logger.print('Fetching 7za.gz file...')
            error = self._fetcher.fetch_file(FILE_7z_util_uninstalled_description(), FILE_7z_util_uninstalled)
            if error is not None:
                self._logger.print('ERROR! Could not fetch the 7za.gz file.')
                self._logger.print(error)
                return

        self._run_subprocesses(linux)

    def get_current_linux_version(self):
        return self._file_system.read_file_contents(FILE_MiSTer_version) if self._file_system.is_file(FILE_MiSTer_version) else 'unknown'

    def _run_subprocesses(self, linux: Dict[str, str]) -> None:
        if self._file_system.is_file(FILE_7z_util_uninstalled):
            sys.stdout.flush()
            result = subprocess.run(f'gunzip "{FILE_7z_util_uninstalled}"', shell=True, stderr=subprocess.STDOUT)
            self._file_system.unlink(FILE_7z_util_uninstalled)
            if result.returncode != 0:
                self._logger.print('ERROR! Could not install 7z.')
                self._logger.print('Error code: %d' % result.returncode)
                self._logger.print()
                return

        if not self._file_system.is_file(FILE_7z_util):
            self._logger.print('ERROR! 7z is not present in the system.')
            self._logger.print('Aborting Linux update.')
            self._logger.print()
            return

        sys.stdout.flush()
        result = subprocess.run('''
                sync
                RET_CODE=
                if {0} t "{1}" ; then
                    if [ -d /media/fat/linux.update ]
                    then
                        rm -R "/media/fat/linux.update" > /dev/null 2>&1
                    fi
                    mkdir "/media/fat/linux.update"
                    if {0} x -y "{1}" files/linux/* -o"/media/fat/linux.update" ; then
                        RET_CODE=0
                    else
                        rm -R "/media/fat/linux.update" > /dev/null 2>&1
                        sync
                        RET_CODE=101
                    fi
                else
                    echo "Downloaded installer 7z is broken, deleting {1}"
                    RET_CODE=102
                fi
                rm "{1}" > /dev/null 2>&1
                exit $RET_CODE
        '''.format(FILE_7z_util, FILE_Linux_uninstalled), shell=True, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            self._logger.print('ERROR! Could not uncompress the linux installer.')
            self._logger.print('Error code: %d' % result.returncode)
            self._logger.print()
            return

        if len(self._user_files) > 0:
            clean_restore = self._restore_user_files()
            if not clean_restore:
                return

        self._logger.print()
        self._logger.print("======================================================================================")
        self._logger.print("Hold your breath: updating the Kernel, the Linux filesystem, the bootloader and stuff.")
        self._logger.print("Stopping this will make your SD unbootable!")
        self._logger.print()
        self._logger.print("If something goes wrong, please download the SD Installer from")
        self._logger.print(linux['url'])
        self._logger.print("and copy the content of the files/linux/ directory in the linux directory of the SD.")
        self._logger.print("Reflash the bootloader with the SD Installer if needed.")
        self._logger.print("======================================================================================")
        self._logger.print()

        sys.stdout.flush()
        result = subprocess.run('''
                    sync
                    mv -f "/media/fat/linux.update/files/linux/linux.img" "/media/fat/linux/linux.img.new"
                    mv -f "/media/fat/linux.update/files/linux/"* "/media/fat/linux/"
                    rm -R "/media/fat/linux.update" > /dev/null 2>&1
                    sync
                    /media/fat/linux/updateboot
                    sync
                    mv -f "/media/fat/linux/linux.img.new" "/media/fat/linux/linux.img"
                    sync
                    touch /tmp/downloader_needs_reboot_after_linux_update
        ''', shell=True, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            self._logger.print('ERROR! Something went wrong during the Linux update, try again later.')
            self._logger.print('Error code: %d' % result.returncode)
            self._logger.print()

    def _restore_user_files(self) -> bool:
        temp_dir = tempfile.mkdtemp()
        self._logger.debug('Created temporary directory for image: %s' % temp_dir)

        mount_cmd = 'mount -t ext4 /media/fat/linux.update/files/linux/linux.img {0}'.format(temp_dir)
        self._logger.debug('Mounting temporary Linux image with command: %s' % mount_cmd)
        result = subprocess.run(mount_cmd, shell=True, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            self._logger.print('ERROR! Could not mount updated Linux image, try again later.')
            self._logger.print('Error code: %d' % result.returncode)
            self._logger.print()
            return False

        copy_error = False
        self._logger.print('Restoring user Linux configuration files:')
        for source, destination in self._user_files:
            image_destination = temp_dir + destination
            self._logger.debug('Copying "%s" to "%s"' % (source, image_destination))
            self._logger.print(' - Installing "%s" to "%s"...' % (source, destination), end='')
            try:
                self._file_system.copy(source, image_destination)
            except Exception as e:
                self._logger.print('ERROR! Could not be installed.')
                self._logger.debug('Could not copy "%s" to "%s": %s' % (source, destination, str(e)))
                copy_error = True
                break
            else:
                self._logger.print('OK!')
        self._logger.print()

        unmount_cmd = 'umount {0}'.format(temp_dir)
        self._logger.debug('Unmounting Linux image with command: %s' % unmount_cmd)
        result = subprocess.run(unmount_cmd, shell=True, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            self._logger.print('ERROR! Could not unmount updated temporary Linux image.')
            self._logger.print('Error code: %d' % result.returncode)
            self._logger.print()
            return False

        if copy_error:
            self._logger.print('ERROR! Could not restore user Linux configuration files.')
            self._logger.print()
            return False

        return True

    def needs_reboot(self):
        return self._file_system.is_file(FILE_downloader_needs_reboot_after_linux_update)
