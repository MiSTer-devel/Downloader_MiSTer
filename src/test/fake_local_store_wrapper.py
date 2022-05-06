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
from downloader.local_store_wrapper import LocalStoreWrapper as ProductionLocalStoreWrapper, StoreWrapper as ProductionStoreWrapper


class LocalStoreWrapper(ProductionLocalStoreWrapper):
    def __init__(self, local_store, crate=None):
        if crate is not None:
            crate.needs_save = False
        self._crate = crate
        super().__init__(local_store)

    def mark_force_save(self):
        if self._crate is not None:
            self._crate.needs_save = True
        super().mark_force_save()


class StoreWrapper(ProductionStoreWrapper):
    def __init__(self, store, top_wrapper=None, crate=None):
        self._top_wrapper = top_wrapper or LocalStoreWrapper({}, crate)
        super().__init__(store, self._top_wrapper)
