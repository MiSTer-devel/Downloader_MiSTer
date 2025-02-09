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

from downloader.migrations.migration_v1 import MigrationV1
from downloader.migrations.migration_v2 import MigrationV2
from downloader.migrations.migration_v3 import MigrationV3
from downloader.migrations.migration_v4 import MigrationV4
from downloader.migrations.migration_v5 import MigrationV5
from downloader.migrations.migration_v6 import MigrationV6
from downloader.migrations.migration_v7 import MigrationV7
from downloader.migrations.migration_v8 import MigrationV8
from downloader.migrations.migration_v9 import MigrationV9


def migrations(config, file_system_factory):
    return [
        MigrationV1(),
        MigrationV2(),
        MigrationV3(),
        MigrationV4(),
        MigrationV5(config, file_system_factory),
        MigrationV6(file_system_factory),
        MigrationV7(config),
        MigrationV8(),
        MigrationV9()
    ]
