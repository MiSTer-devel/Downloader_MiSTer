# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

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
