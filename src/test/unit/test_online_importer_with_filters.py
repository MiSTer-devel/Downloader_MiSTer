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

import unittest

from downloader.config import default_config
from downloader.online_importer import WrongDatabaseOptions
from downloader.other import empty_store
from test.objects import db_test_descr, store_descr, file_descr, file_b, file_a, file_c, folder_a, folder_b, \
    folder_c, config_with_filter, file_one, empty_test_store
from test.fake_online_importer import OnlineImporter


class TestOnlineImporterWithFilters(unittest.TestCase):

    def test_download_db_with_cheat_and_console_files_and_tag_dictionary___without_any_filter___installs_all_cheats_and_console_files(self):
        self.assertEqual(store_with_cheats_and_console_files(), self.download_db_with_cheat_and_console_files_and_tag_dictionary(default_config()))

    def test_download_db_with_cheat_and_console_files_and_tag_dictionary___using_filter_nes___installs_all_nes_files(self):
        self.assertEqual(store_with_all_nes_files(), self.download_db_with_cheat_and_console_files_and_tag_dictionary(config_with_filter('nes')))

    def test_download_db_with_cheat_and_console_files_and_tag_dictionary___using_given_filter___installs_expected_stores(self):
        self.assertFilters(self.download_db_with_cheat_and_console_files_and_tag_dictionary, [
            ('!cheats', store_with_console_files_only),
            ('cheats', store_with_cheats_files_only),
            ('nes', store_with_all_nes_files),
            ('!nes', store_with_all_gb_files),
            ('gb', store_with_all_gb_files),
            ('!gb', store_with_all_nes_files),
            ('nes !cheats', store_with_file_nes_game),
            ('!nes !cheats', store_with_file_gb_game),
            ('gb !cheats', store_with_file_gb_game),
            ('!gb !cheats', store_with_file_nes_game),
            ('nes cheats', store_with_all_cheats_and_nes_game),
            ('!nes cheats', store_with_file_gb_cheat),
            ('gb cheats', store_with_all_cheats_and_gb_game),
            ('!gb cheats', store_with_file_nes_cheat),
            ('!gb !nes !cheats', empty_test_store),
            ('!all', empty_test_store),
            ('!gb !nes', store_with_just_cheats_folder),
            ('all', store_with_cheats_and_console_files),
            ('nes gb', store_with_cheats_and_console_files),
            ('nes gb cheats', store_with_cheats_and_console_files),
            ('something_not_in_db', store_with_cheats_and_console_files),
            ('nes something_not_in_db', store_with_all_nes_files),
            ('!nes something_not_in_db', store_with_all_gb_files),
        ])

    def test_download_db_with_essential_and_cheats_files___given_nes_filter___install_nes_and_essential_files(self):
        self.assertEqual(store_with_essential_and_nes_files(), self.download_db_with_essential_and_cheats_files(config_with_filter('nes')))

    def test_download_db_with_files_a_b_c___using_filter_b___installs_b_only(self):
        self.assertEqual(store_with_file_b(), self.download_db_with_files_a_b_c(config_with_filter('b')))

    def test_download_db_with_files_a_b_c___using_given_filter___installs_expected_stores(self):
        self.assertFilters(self.download_db_with_files_a_b_c, [
            ('b', store_with_file_b),
            ('!b', store_with_files_a_and_c),
            ('a', store_with_file_a),
            ('   a  ', store_with_file_a),
            ('!a', store_with_files_b_and_c),
            ('a b', store_with_files_a_and_b),
            ('   a   b   ', store_with_files_a_and_b),
            ('!a !b', store_with_file_c),
            ('a !b', store_with_file_a),
            ('!a b', store_with_file_b),
            ('a b c', store_with_files_a_b_c),
            ('all', store_with_files_a_b_c),
            ('all a', store_with_files_a_b_c),
            ('!a b c', store_with_files_b_and_c),
            ('a !b c', store_with_files_a_and_c),
            ('a b !c', store_with_files_a_and_b),
            ('a !b !c', store_with_file_a),
            ('!a b !c', store_with_file_b),
            ('!a !b c', store_with_file_c),
            ('!a !b !c', empty_test_store),
            ('!all', empty_test_store),
            ('something_not_in_db', store_with_files_a_b_c),
            ('a something_not_in_db', store_with_file_a),
            ('!a something_not_in_db', store_with_files_b_and_c),
        ])

    def test_download_db_with_one_non_tagged_file_and_tagged_a_file___using_filter_a___installs_file_a_and_non_tagged_file(self):
        self.assertEqual(store_with_one_non_tagged_file_and_file_a(), self.download_db_with_one_non_tagged_file_and_tagged_a_file(config_with_filter('a')))

    def test_download_db_with_one_non_tagged_file_and_tagged_a_file___using_negative_all_filter___installs_nothing(self):
        self.assertEqual(empty_test_store(), self.download_db_with_one_non_tagged_file_and_tagged_a_file(config_with_filter('!all')))

    def test_download_db___using_incorrect_filter___raises_wrong_database_options(self):
        for given_filter in ['!!!b', '@what', '  ', '', '_hidden', 'wha+tever', '"quotes1"', "'quotes2'", '!all a', 'none']:
            with self.subTest(given_filter) as _:
                self.assertRaises(WrongDatabaseOptions, lambda: self.download_db_with_cheat_and_console_files_and_tag_dictionary(config_with_filter(given_filter)))

    def test_download_db_with_file_with_tag_foobar___using_negative_foo_underscore_bar_filter___installs_nothing(self):
        self.assertEqual(empty_test_store(), self.download_db_with_file_with_tag_foobar(config=config_with_filter('!foo_bar')))

    def test_download_db_with_file_with_tag_foobar___using_negative_foo_hyphen_bar_filter___installs_nothing(self):
        self.assertEqual(empty_test_store(), self.download_db_with_file_with_tag_foobar(config=config_with_filter('!foo-bar')))

    def test_download_db_with_file_with_tag_foobar___using_negative_filter_not_matching_tag___installs_file_with_tag_foobar(self):
        self.assertEqual(store_with_file_with_tag_foobar(), self.download_db_with_file_with_tag_foobar(config=config_with_filter('!foobar2')))

    def assertFilters(self, download_interface, test_parameters):
        self.maxDiff = None
        for given_filter, expected_store in test_parameters:
            with self.subTest("filter '%s' installs %s" % (given_filter, expected_store.__name__)) as _:
                self.assertEqual(expected_store(), download_interface(config_with_filter(given_filter)))

    def download_db_with_files_a_b_c(self, config):
        return OnlineImporter(config=config).download_db(db_with_files_a_b_c(), empty_test_store())

    def download_db_with_essential_and_cheats_files(self, config):
        return OnlineImporter(config=config).download_db(db_with_essential_and_cheats_files(), empty_test_store())

    def download_db_with_cheat_and_console_files_and_tag_dictionary(self, config):
        return OnlineImporter(config=config).download_db(db_with_cheats_and_console_files(), empty_test_store())

    def download_db_with_one_non_tagged_file_and_tagged_a_file(self, config):
        return OnlineImporter(config=config).download_db(db_with_one_non_tagged_file_and_file_a(), empty_test_store())

    def download_db_with_file_with_tag_foobar(self, config):
        return OnlineImporter(config=config).download_db(db_with_file_with_tag_foobar(), empty_test_store())


def db_with_files_a_b_c():
    return db_test_descr(files={
        file_a: file_descr(tags=['a']),
        file_b: file_descr(tags=['b']),
        file_c: file_descr(tags=['c'])
    }, folders={
        folder_a: {'tags':['a']},
        folder_b: {'tags':['b']},
        folder_c: {'tags':['c']}
    })


def store_with_files_a_b_c():
    return store_descr(files={
        file_a: file_descr(),
        file_b: file_descr(),
        file_c: file_descr()
    }, folders={folder_a: {}, folder_b: {}, folder_c: {}})

def store_with_file_a():
    return store_descr(files={file_a: file_descr()}, folders={folder_a: {}})

def store_with_files_a_and_b():
    return store_descr(files={file_a: file_descr(), file_b: file_descr()}, folders={folder_a: {}, folder_b: {}})

def store_with_files_a_and_c():
    return store_descr(files={file_a: file_descr(), file_c: file_descr()}, folders={folder_a: {}, folder_c: {}})

def store_with_file_b():
    return store_descr(files={file_b: file_descr()}, folders={folder_b: {}})

def store_with_files_b_and_c():
    return store_descr(files={file_b: file_descr(), file_c: file_descr()}, folders={folder_b: {}, folder_c: {}})

def store_with_file_c():
    return store_descr(files={file_c: file_descr()}, folders={folder_c: {}})

file_nes_cheat = 'nes_cheat'
file_gb_cheat = 'gb_cheat'
file_nes_game = 'nes_game'
file_gb_game = 'gb_game'
tag_dictionary = {
    'cheats': 0,
    'nes': 1,
    'gb': 2
}
tag_cheats = 0
tag_nes = 1
tag_gb = 2
tag_essential = 3

def db_with_cheats_and_console_files():
    return db_test_descr(files={
        file_nes_cheat: file_descr(tags=[tag_nes, tag_cheats]),
        file_gb_cheat: file_descr(tags=[tag_gb, tag_cheats]),
        file_nes_game: file_descr(tags=[tag_nes]),
        file_gb_game: file_descr(tags=[tag_gb]),
    }, tag_dictionary=tag_dictionary, folders={
        'cheats': {'tags': [tag_cheats]},
        'cheats/nes': {'tags': [tag_cheats, tag_nes]},
        'cheats/gb': {'tags': [tag_cheats, tag_gb]},
        'nes': {'tags': [tag_nes]},
        'gb': {'tags': [tag_gb]},
    })

def store_with_cheats_and_console_files():
    return store_descr(files={
        file_nes_cheat: file_descr(),
        file_gb_cheat: file_descr(),
        file_nes_game: file_descr(),
        file_gb_game: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/nes': {},
        'cheats/gb': {},
        'nes': {},
        'gb': {},
    })

def store_with_just_cheats_folder():
    return store_descr(folders={'cheats': {}})

def store_with_console_files_only():
    return store_descr(files={
        file_nes_game: file_descr(),
        file_gb_game: file_descr(),
    }, folders={
        'nes': {},
        'gb': {},
    })

def store_with_cheats_files_only():
    return store_descr(files={
        file_nes_cheat: file_descr(),
        file_gb_cheat: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/nes': {},
        'cheats/gb': {},
    })

def store_with_all_nes_files():
    return store_descr(files={
        file_nes_cheat: file_descr(),
        file_nes_game: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/nes': {},
        'nes': {},
    })

def store_with_all_gb_files():
    return store_descr(files={
        file_gb_cheat: file_descr(),
        file_gb_game: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/gb': {},
        'gb': {},
    })

def store_with_file_nes_cheat():
    return store_descr(files={file_nes_cheat: file_descr()}, folders={
        'cheats': {},
        'cheats/nes': {},
    })

def store_with_file_gb_cheat():
    return store_descr(files={file_gb_cheat: file_descr()}, folders={
        'cheats': {},
        'cheats/gb': {}
    })

def store_with_file_nes_game():
    return store_descr(files={file_nes_game: file_descr()}, folders={
        'nes': {},
    })

def store_with_file_gb_game():
    return store_descr(files={file_gb_game: file_descr()}, folders={
        'gb': {},
    })

def store_with_all_cheats_and_nes_game():
    return store_descr(files={
        file_nes_cheat: file_descr(),
        file_gb_cheat: file_descr(),
        file_nes_game: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/nes': {},
        'cheats/gb': {},
        'nes': {},
    })

def store_with_all_cheats_and_gb_game():
    return store_descr(files={
        file_nes_cheat: file_descr(),
        file_gb_cheat: file_descr(),
        file_gb_game: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/nes': {},
        'cheats/gb': {},
        'gb': {},
    })


def db_with_essential_and_cheats_files():
    return db_test_descr(files={
        file_one: file_descr(tags=[tag_essential]),
        file_nes_cheat: file_descr(tags=[tag_nes, tag_cheats]),
        file_gb_cheat: file_descr(tags=[tag_gb, tag_cheats]),
    }, tag_dictionary={
        'cheats': tag_cheats,
        'nes': tag_nes,
        'gb': tag_gb,
        'essential': tag_essential
    }, folders={
        'cheats': {'tags': [tag_cheats]},
        'cheats/nes': {'tags': [tag_cheats, tag_nes]},
        'cheats/gb': {'tags': [tag_cheats, tag_gb]},
    })


def store_with_essential_and_nes_files():
    return store_descr(files={
        file_one: file_descr(),
        file_nes_cheat: file_descr(),
    }, folders={
        'cheats': {},
        'cheats/nes': {},
    })


def db_with_one_non_tagged_file_and_file_a():
    return db_test_descr(files={
        file_a: file_descr(tags=['a']),
        file_one: file_descr()
    }, folders={
        folder_a: {'tags':['a']},
    })


def store_with_one_non_tagged_file_and_file_a():
    return store_descr(files={
        file_a: file_descr(),
        file_one: file_descr(),
    }, folders={
        folder_a: {}
    })


def db_with_file_with_tag_foobar():
    return db_test_descr(files={file_one: file_descr(tags=['foobar'])})


def store_with_file_with_tag_foobar():
    return store_descr(files={file_one: file_descr()})
