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

import subprocess


class LinuxUpdater:
    def __init__(self, file_service, downloader, logger):
        self._downloader = downloader
        self._logger = logger
        self._file_service = file_service
        self._linux_descriptions = []

    def add_db(self, db):
        if 'linux' in db:
            self._linux_descriptions.append({
                'id': db['db_id'],
                'args': db['linux']
            })

    def update_linux(self):

        linux_descriptions_count = len(self._linux_descriptions)
        if linux_descriptions_count == 0:
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
        linux_path = 'linux.7z'

        current_linux_version = 'unknown'
        if self._file_service.is_file('/MiSTer.version'):
            current_linux_version = self._file_service.read_file_contents('/MiSTer.version')

        if current_linux_version == linux['version'][-6:]:
            return

        self._logger.print('Linux will be updated from %s:' % description['id'])
        self._logger.print('Current linux version -> %s' % current_linux_version)
        self._logger.print('Latest linux version -> %s' % linux['version'][-6:])
        self._logger.print()

        self._downloader.queue_file(linux, linux_path)
        if not self._file_service.is_file('/media/fat/linux/7za'):
            self._downloader.queue_file({
                'delete': [],
                'url': 'https://github.com/MiSTer-devel/SD-Installer-Win64_MiSTer/raw/master/7za.gz',
                'hash': 'ed1ad5185fbede55cd7fd506b3c6c699',
                'size': 465600
            }, '/media/fat/linux/7za.gz')

        self._downloader.download_files(False)
        self._logger.print()

        if len(self._downloader.errors()) > 0:
            self._logger.print('Some error happened during the Linux download:')
            for error in self._downloader.errors():
                self._logger.print(error)

            self._logger.print()
            return

        self._run_subprocesses(linux, linux_path)

    def _run_subprocesses(self, linux, linux_path):
        if self._file_service.is_file('/media/fat/linux/7za.gz'):
            result = subprocess.run('gunzip "/media/fat/linux/7za.gz"', shell=True, stderr=subprocess.STDOUT)
            self._file_service.unlink('/media/fat/linux/7za.gz')
            if result.returncode != 0:
                self._logger.print('ERROR! Could not install 7z.')
                self._logger.print('Error code: %d' % result.returncode)
                self._logger.print()
                return

        if not self._file_service.is_file('/media/fat/linux/7za'):
            self._logger.print('ERROR! 7z is not present in the system.')
            self._logger.print('Aborting Linux update.')
            self._logger.print()
            return

        result = subprocess.run('''
                sync
                RET_CODE=
                if /media/fat/linux/7za t "{0}" ; then
                    if [ -d /media/fat/linux.update ]
                    then
                        rm -R "/media/fat/linux.update" > /dev/null 2>&1
                    fi
                    mkdir "/media/fat/linux.update"
                    if /media/fat/linux/7za x -y "{0}" files/linux/* -o"/media/fat/linux.update" ; then
                        RET_CODE=0
                    else
                        rm -R "/media/fat/linux.update" > /dev/null 2>&1
                        sync
                        touch /tmp/downloader_needs_reboot_after_linux_update
                        RET_CODE=101
                    fi
                else
                    echo "Downloaded installer 7z is broken, deleting {0}"
                    RET_CODE=102
                fi
                rm "{0}" > /dev/null 2>&1
                exit $RET_CODE
        '''.format(self._file_service.curl_target_path(linux_path)), shell=True, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            self._logger.print('ERROR! Could not uncompress the linux installer.')
            self._logger.print('Error code: %d' % result.returncode)
            self._logger.print()
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

    def needs_reboot(self):
        return self._file_service.is_file('/tmp/downloader_needs_reboot_after_linux_update')
