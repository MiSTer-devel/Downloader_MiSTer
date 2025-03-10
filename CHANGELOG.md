# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## Version 2.0 - 2025-03-X

TODO!!
Reproduce bug in test: filter out palettes, filter in palettes. It happens too with games/GAMEBOY and games/ATARI "ERROR: /media/fat/|games/Atari2600"


### Added
- The launcher now uses the latest build of Downloader if it's present in the filesystem. The newer version of Downloader will now be installed from [MiSTer Distribution](https://github.com/MiSTer-devel/Distribution_MiSTer) database just like any other standard MiSTer file. Thanks to this, you may now avoid executing remote code altogether by taking [this additional step](README.md#how-to-avoid-executing-remote-code-altogether) during installation. Otherwise, remote code execution only happens once on your first run of Downloader.
- Documented **Custom INI file** support in [README.md](README.md#custom-ini-file), in case you want to use a separate launcher and INI file to install different databases in isolation through that launcher.

### Changed
- Reboot sequence takes much less time, it went from 30+ seconds to 3.
- Fixed database filtering not working properly in various uncommon scenarios. 
- Improved exit error codes. Previously, we were using only exit code 1 to represent any error, but now values from 10 to 19 represent system errors, and values of 20 or above represent update failures. Check the [constants.py](src/downloader/constants.py) file to see the specific error codes.
- Improved release script. Now it's also implemented in python.
- Fixed bug in error handling when restoring user system files during a Linux update by [daph](https://github.com/MiSTer-devel/Downloader_MiSTer/commits?author=daph).
- Better **custom download filters** documentation by [NFGman](https://github.com/MiSTer-devel/Downloader_MiSTer/commits?author=NFGman). Check it [here](docs/download-filters.md).
- Expanded filesystem precaching to speed up the check of already installed files.
- Many minor bug fixes.
- The SSL check mechanism in the launcher has been made more flexible by covering more return codes. From just 60 to codes: 60, 77, 35, 51, 58, 59, 82, 83. It also has an improved routine to install new certificates, in case they are missing in the system.

### Removed
- The distutils dependency was removed, since it's been deprecated for a while (PEP 632) and removed in Python 3.12.
- Removed `base_path` in database-scoped options. Files installed in different locations because of this option will be moved to the standard location. As a reminder, general `base_path` usage was deprecated in the version 1.8, as now multi-drive setups are handled with the **Storage Priority** feature introduced in Downloader 1.5.
- The *offline importer*, a mechanism designed to assist during the migration from the old updater to Downloader, has been removed. Its role was to amend the file duplications that happened with the old updater, but unfortunately it never worked. It required the publication of the original file lists that were renamed, and although some contributors were initially committed to provide them, they could not deliver them in the end. 

## Version 1.8 - 2023-09-21

### Added
- Introduced a free space check before installing files. The minimum free space can be adjusted at your own risk using the `minimum_system_free_space_mb` and `minimum_external_free_space_mb` options in `downloader.ini`. More information is available in the README file.
- Added the capability to back up and restore system files during Linux updates (wizzo). For more information, see: https://github.com/MiSTer-devel/Downloader_MiSTer/pull/35
- Introduced a new test bench to realistically measure system performance during development.

### Changed
- Implemented file system caching that improves the speed of short runs (runs with no updates) by around 3x when the system has been recently initialized.
- Databases are now processed in parallel during file installations, increasing overall speed. This results in a 5-15% speed improvement with stable Ethernet connections, and I've measured up to a 50% speed improvement on less reliable Wi-Fi connections.
- Introduced a job system to manage concurrency. Currently, it is used for fetching, installing, and validating files.
- Reworked the build script to reduce the bundle size, slightly speeding up the time the launcher takes to download it during each Downloader run.
- Local storage is now saved without compression, saving around a second in all runs but using slightly more system space (typically less than 5 MB).
- Improved handling of file and folder creation errors.
- Fixed a bug affecting non-Keep-Alive connections.
- Fixed a bug that occurred when trying to hash a corrupted file.
- Fixed a bug affecting the download filters feature under certain conditions.
- Reimplemented the debug script in Python, adding additional options and features. This is useful primarily for development.
- Various other fixes and improvements.

### Removed
- Deprecated the `base_path` option. While it is still used internally, it has been removed from the README and is no longer intended for user customization.

## Version 1.7 - 2023-04-28

### Added
- Database-scoped filters can now inherit the terms from the global filter (the filter under the `[MiSTer]` section). In a database-scoped filter, you may add the term `[mister]` to bring all the global filter terms into the scope. This is useful to apply different filters to different DBs while sharing some common terms. More info [in the database-scoped filters section](docs/download-filters.md#database-scoped-filters-using-the-filter-property-in-another-section-other-than-mister).
- Filters on database-scoped default options may also use global filter inheritance. This is useful as users expect to apply the global filter to all DBs by default, and DBs with database-scoped default filters were taking precedence over global filters when inheritance was not available. So DB maintainers can now easily solve this UX issue by adding the term `[mister]` to the database-scoped default filter.
- Added support for the yc.txt file.
- Added ntpdate mitigation code to the launcher to deal with installations where the system clock is not configured.
- Added message with instructions for users that have an old MiSTer installation.

### Changed
- Optimisations on the HTTP Client to allow more requests going on at the same time.
- Added types to several files to improve the codebase maintainability.
- Several lesser fixes and improvements.

## Version 1.6 - 2022-10-27

### Added
- PC Launcher was added. It allows users to run Downloader on a PC. [Documentation](docs/pc-launcher.md).
- Added support for files gamecontrollerdb and gamecontrollerdb_user.

### Changed
- The minimum python version required is now 3.9 instead of 3.5 (MiSTer OS has python version 3.9 since September 2021).
- Code that used Linux utilities has been substituted with code using native python libraries. This makes Downloader cross-platform.
- The file downloader module now uses python threads instead of CURL. This brings a significant speed boost during bulk downloads. General speed improvement is measured to be between 1.47x and 2.52x for standard use cases on MiSTer.
- File validation now happens in the main thread after each file has been downloaded asynchronously.
- When called from `update.sh`, the configuration file `downloader.ini` will be read instead of `update.ini`. Reason is: Since Downloader is now distributed through that launcher, this case needs to reflect better the behaviour described in the documentation.
- Simplified SSL Certificates installation in the launcher file `downloader.sh`.
- Zip support now also includes a special case for single files that facilitates the distribution of very big files.
- Improved error reporting when there are certificate and mount errors to be more informative to the end user.
- Improved messages on files not getting installed because they are marked as overwrite protected in the database.
- Several lesser fixes and improvements.

### Removed
- Removed CLI output section that showed file validations with the `+` symbol, as now file validation happens during bulk downloads.
- Removed documentation about `base_system_path` as is not meant to be used by users.

## Version 1.5 - 2022-05-06

### Added
- Support for **Storage Priority Resolution**: External Storage will be used for installing new files under certain conditions. More info [in the options section](README.md#options).
- `base_path` as a database-scoped option.
- Routine for fixing certificates when they are not working correctly.
- Support for PDFViewer, glow and lesskey (for reading docs files).
- Documentation for `tag` property on the Custom Databases documentation page (useful for filtering).
- Verbose option in `downloader.ini` for printing debug output while running Downloader.
- Critical parts of the script are benchmarked, and the resulting output is printed when the verbose option is activated.
- New entrypoint for displaying connected external drives by calling the launcher with the argument `--print-drives`.

### Changed
- Internal DB save is not attempted when no changes have been detected. This change saves time and spares writes on the SD.
- Many optimizations have been performed, taking advantage of the information provided by the new benchmarks.
- Improved readability of custom database documentation (tonurics).
- Fields `base_files_url`, `db_files`, `zips`, `default_options` are now not mandatory on Custom Databases.
- Download Filter terms can now start with numbers.
- Fixed INI path resolution when Downloader was called from unusual locations.
- Improved internal implementation for zip summaries.
- Other general improvements: refactors, fixes, test coverage, code cleanup...

### Removed
- Removed `url_safe_characters` option as it's no longer useful. Now database URLs need to be strictly correct.

## Version 1.4 - 2022-01-21

### Added
- Support for **custom download filters**: Users can now avoid installing files that they are not interested in. More info [here](docs/download-filters.md).

### Changed
- Fixing makedirs errors.
- Improved backup handling when a file is downloaded but the hash is wrong.
- Option url_safe_characters introduced (which is used at`urllib.parse.quote(safe)`). 
- Better logging for `update_only_linux` and `update_linux=false`.
- Output is stored in the correct order in the logs when a Linux Update happens.
- Custom databases can now trigger sleeps through its header property.
- Better log when a file has override protection and could be updated.
- Other general improvements: optimizations, more test coverage, code cleanup...

## Version 1.3 - 2021-12-04

### Added
- Support for **database-scoped default options**: Custom databases can now redefine the default option values that will apply to them.
- Support for **database-scoped options**: Users can now also define options that apply only to a given database.

More info for both additions can be found [here](https://github.com/theypsilon/Downloader_MiSTer/blob/main/docs/custom-databases.md#default-options).
### Changed
- Storing changes on zip summary hash. This avoids wasting time downloading an unnecessary file in some runs.
- Better compression method for the local store. Saves some space in the SD, while the added run time is negligible.
- Better validation of `downloader.ini` file.
- The download of the database json files is now done in parallel, which is a bit faster.
- Old mister file is now saved in the root of the SD as `.MiSTer.old`. This prevents an error that affected some users of the **cifs** script.
- Fixing hash validation errors getting ignored in some cases.
- Other minor fixes and optimizations.

## Version 1.2 - 2021-11-06

### Added
- Support for custom databases: https://github.com/MiSTer-devel/Downloader_MiSTer/blob/main/docs/custom-databases.md
- Database and path validations.

### Changed
- Validation changes for options `base_path` and `base_system_path`. They now need to always start with `/media/*` otherwise downloader will show an error.
- Minor fixes.

## Version 1.1 - 2021-10-17

### Added
- Zip first-class support for faster distribution of big packs of files (Cheats, Palettes, Filters, MRA-Alternatives, etc...).
- New Cheats and Palettes folders coming from the Distribution repository.

### Changed
- Increased waiting time before reboot, as a measure to avoid problems during linux updates.
- Running time is more realistic now.
- Other tweaks and optimizations.

## Version 1.0 - 2021-09-15

### Added
- Safe downloads from the distribution repository with hash verification.
- Linux updater.
- Config file `downloader.ini` for changing download settings and target storage.
- Internal database for tracking changes and renaming/removing files and folders when needed.
- Offline importer for adding existing files into the downloader internal database, with the help of the db.json.zip file from the distribution repository. This is meant for people copy/pasting the whole distribution repository content into their SD as part of an offline installation.
- Logging at `Scripts/.config/downloader/downloader.log`
