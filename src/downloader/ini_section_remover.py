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


import re


def remove_ini_section(content: bytes, section: str) -> tuple[bytes, bool]:
    header = re.compile(
        rb'^[ \t]*\[([^\]\r\n]+)\][ \t]*(?:[;#][^\r\n]*)?(?:\r\n|\n|\r|$)',
        re.MULTILINE,
    )
    matches = list(header.finditer(content))
    section_bytes = section.encode('utf-8').lower()
    for index, match in enumerate(matches):
        if match.group(1).strip().lower() != section_bytes:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        return content[:match.start()] + content[end:], True
    return content, False
