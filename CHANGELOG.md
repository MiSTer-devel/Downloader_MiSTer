# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

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
