# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import hashlib
import json
from typing import Any, Mapping, Optional


EXTERNAL_STORE_FINGERPRINTS = 'external_store_fingerprints'


def external_store_fragment_fingerprint(drive: str, fragment: dict[str, Any]) -> str:
    canonical_fragment = json.dumps(fragment, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.md5(f'{drive}\0{canonical_fragment}'.encode()).hexdigest()


def external_store_manifest(drive: str, external_store: dict[str, Any], db_ids: set[str]) -> dict[str, str]:
    return {
        db_id: external_store_fragment_fingerprint(drive, fragment)
        for db_id, fragment in external_store.get('dbs', {}).items()
        if db_id in db_ids
    }


def external_store_manifest_fragments(manifest: Mapping[str, Any]) -> dict[str, str]:
    old_shape = manifest.get('db_fragments')
    if isinstance(old_shape, dict):
        return {db_id: fingerprint for db_id, fingerprint in old_shape.items() if isinstance(fingerprint, str)}
    return {db_id: fingerprint for db_id, fingerprint in manifest.items() if isinstance(fingerprint, str)}


def expected_external_store_fingerprints(figp: Mapping[str, Any]) -> Optional[set[str]]:
    expected = figp.get(EXTERNAL_STORE_FINGERPRINTS)
    if not isinstance(expected, list):
        return None
    return set(expected)


def has_external_store_fingerprint_metadata(figp: Mapping[str, Any]) -> bool:
    return expected_external_store_fingerprints(figp) is not None
