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
from downloader.constants import distribution_mister_db_id
from downloader.db_options import DbOptionsKind
from downloader.migrations import migrations
from downloader.store_migrator import StoreMigrator as ProductionStoreMigrator
from test.objects import db_options
from test.fake_file_system import FileSystemFactory
from test.fake_logger import NoLogger


def default_config_with_distribution_mister():
    config = default_config()
    config['databases'] = {
        distribution_mister_db_id: {'options': db_options(kind=DbOptionsKind.INI_SECTION, base_path='/media/fat')}
    }
    return config


class StoreMigrator(ProductionStoreMigrator):
    def __init__(self, maybe_migrations=None, file_system_factory=None, config=None):
        self.config = default_config_with_distribution_mister() if config is None else config
        file_system_factory = FileSystemFactory(config=self.config) if file_system_factory is None else file_system_factory
        self.system_file_system = file_system_factory.create_for_system_scope()
        super().__init__(migrations(self.config, file_system_factory) if maybe_migrations is None else maybe_migrations, NoLogger())
