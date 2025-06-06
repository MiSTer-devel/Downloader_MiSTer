# MiSTer Downloader

This tool installs and **updates all the cores** and other extra files for your *MiSTer*. It also updates the menu core, the MiSTer firmware and the Linux system. The source for all downloads is the [MiSTer Distribution](https://github.com/MiSTer-devel/Distribution_MiSTer) repository.

### Setup and Usage

This tool is usually pre-installed in your MiSTer. If not, download this [ZIP file](https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/MiSTer_Downloader.zip) and extract `update.sh` to your `/Scripts` folder on your primary SD card (create that folder if it doesn't exist). You only need to perform this operation once, since this tool self-updates itself.

To use it, on your MiSTer main menu, go to the *Scripts* screen, and select `update`.

### Options

You may create a `/media/fat/downloader.ini` file to tweak some parameters.

Here you can see the default parameters and the options that you may change:

```ini
[MiSTer]
; storage_priority defines how this tool will use external storage during the installation
;         of files that are designed for external locations (usually games & docs files).
;         
;         * Examples of external storage are USB Drives or CIFS partitions detected by MiSTer.
;
;         * When you have more than one external storage, the one used will be determined
;           by the first path match following the path priority described here:
;             https://mister-devel.github.io/MkDocs_MiSTer/cores/paths/
;
; Options:
;   'prefer_sd' -> This tool will install new files on a external location if a parent folder
;                  is present. (Parent folder examples: games/NES, docs/AO486)
;
;   'prefer_external' -> This tool will always install new files on a external location
;                        even if no parent folders are present.
;
;   'off' -> Disables this feature. Affected files will always be installed in your SD.
storage_priority = 'prefer_sd'

; update_linux options:
;   true -> Updates Linux when there is a new update (very recommended).
;   false -> Doesn't update Linux.
update_linux = true

; allow_reboot options:
;   0 -> Don't allow this tool to ever reboot automatically.
;   1 -> Allow this tool to reboot the system after any system file has been updated.
;   2 -> Allow this tool to reboot the system only after Linux has been updated.
allow_reboot = 1

; allow_delete options:
;   0 -> Don't allow this tool to delete anything at all.
;   1 -> Allow this tool to delete any old file from previous updates.
;   2 -> Allow this tool to delete only old cores that receive a new version.
allow_delete = 1

; minimum_system_free_space_mb: Fee space needed to install files with Downloader
;   This minimum applies solely to the system partition (SD card).
;   Reducing this value is not advised.
minimum_system_free_space_mb = 512

; minimum_external_free_space_mb: Free space needed to install files in external storages
;   This minimum applies to all external storages (USBs & CIFS).
;   Reducing this value is not advised.
minimum_external_free_space_mb = 128

; downloader_timeout: Can be tweaked to increase the timeout time in seconds
;   It is useful to increase this value for users with slow connections.
downloader_timeout = 300

; downloader_retries: Can be tweaked to increase the retries per failed download
;   It is useful to increase this value for users with very unstable connections.
downloader_retries = 3

; verbose: when true, will make Downloader output to display additional debug information
;   This is also necessary to be active to display benchmark information.
verbose = false
```

### Feature Roadmap

- [x] Initial Release
- [x] [Cheats](https://gamehacking.org/mister/) fetching
- [x] First-run optimisations
- [x] Configurable custom download filters
- [x] Storage Priority Resolution for automatically detecting connected drives
- [x] Free space checks
- [ ] Opt-in parameter to bypass strict file checks
- [ ] Fast check for update availability (without triggering an actual update)
- [ ] HTTP cookie support
- [ ] Uninstall database feature
- [ ] Firmware integration

Check the [CHANGELOG](CHANGELOG.md) for more information about past releases.

### PC Launcher (for Windows, Mac, and Linux)

With this different launcher you'll be able to install all MiSTer files without using a MiSTer. This is especially useful if your MiSTer can't access the internet.

Learn how to use the *PC Launcher* [here](docs/pc-launcher.md). 

### Custom Download Filters

With download filters, users will be able to opt-out from installing files that they don't want in their system, like for example, cheats or readme files.

Example:

<p align="center">
  <img src="https://user-images.githubusercontent.com/852246/149844707-fcbe0ce2-d4b2-4f15-96a5-74ec01d8d3de.png" /> 
</p>
<p align="center"><i>This filter will only install console cores, while avoiding all related cheats and documentation files.</i></p>

More information about *Download Filters* [here](docs/download-filters.md).

### Custom Databases

*Custom Databases* give users the ability to download [more file collections](docs/custom-databases.md).

NOTE: If you manually add custom databases, you might want to make sure that you also have a [distribution_mister] section. That way you'll still be downloading the content from [MiSTer Distribution](https://github.com/MiSTer-devel/Distribution_MiSTer) together with the content from the custom database/s that you introduced.

### Custom INI file

You can use a different INI file by renaming the launcher `update.sh` to your preferred name. After renaming the launcher, it will use an INI file with the same name but with the .ini extension. For instance, if you rename the launcher to `/media/fat/Scripts/my_custom_name.sh`, it will use the INI file `/media/fat/my_custom_name.ini` instead of `/media/fat/downloader.ini`.

This flexibility allows for various use cases, such as running a specific database in isolation.

### How to avoid executing remote code altogether

If you're concerned about executing a build that the launcher fetches from the web, you can avoid this by manually installing the latest version of Downloader's build. Just get [this file](https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/dont_download.zip) and save it at `/media/fat/Scripts/.config/downloader/downloader_latest.zip` (remember to rename the file as instructed). You can verify the file's integrity using the provided MD5 checksum [here](https://github.com/MiSTer-devel/Downloader_MiSTer/releases/tag/latest).

If not done manually, the launcher will automatically install that build on its first run. This auto-installation occurs only once and is designed to be secure.

### Supporters+ shout-out!

Alex Frégeau, The Sentinel's Playground Team, and Thomas Williams.

Thank you so much for supporting this project! If you would like to show up here, join us as **Supporter+** on Patreon:

<p align="center">
<a href="https://www.patreon.com/bePatron?u=37499475"><img src="https://slrowland.com/wp-content/uploads/2018/02/patreonsupport.png"></img></a>
</p>

### Powered by
[![PyCharm logo](https://resources.jetbrains.com/storage/products/company/brand/logos/PyCharm.svg)](https://jb.gg/OpenSourceSupport)
