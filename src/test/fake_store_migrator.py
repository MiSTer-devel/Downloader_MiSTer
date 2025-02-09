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
from downloader.config import default_config
from downloader.constants import DISTRIBUTION_MISTER_DB_ID, K_DATABASES, K_OPTIONS
from downloader.migrations import migrations
from downloader.store_migrator import StoreMigrator as ProductionStoreMigrator
from test.objects import db_options
from test.fake_file_system_factory import FileSystemFactory
from downloader.logger import NoLogger


def default_config_with_distribution_mister():
    config = default_config()
    config[K_DATABASES] = {
        DISTRIBUTION_MISTER_DB_ID: {K_OPTIONS: db_options()}
    }
    return config


class StoreMigrator(ProductionStoreMigrator):
    def __init__(self, maybe_migrations=None, config=None, file_system_factory=None):
        self.config = default_config_with_distribution_mister() if config is None else config
        file_system_factory = file_system_factory if file_system_factory is not None else FileSystemFactory.from_state(config=self.config)
        self.system_file_system = file_system_factory.create_for_system_scope()
        super().__init__(migrations(self.config, file_system_factory) if maybe_migrations is None else maybe_migrations, NoLogger())
