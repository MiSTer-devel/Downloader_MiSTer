# MiSTer Downloader

This tool installs and **updates all the cores** and other extra files for your *MiSTer*. It also updates the menu core, the MiSTer firmware and the Linux system. The source for all downloads is the [MiSTer Distribution](https://github.com/MiSTer-devel/Distribution_MiSTer) repository.

The **MiSTer Downloader** is a substitute for the [MiSTer Updater](https://github.com/MiSTer-devel/Updater_script_MiSTer), and is meant to offer a more safe and robust experience, while being much faster.

As a drawback, the **Downloader** is not backwards compatible with the old INI files that were configured for the [MiSTer Updater](https://github.com/MiSTer-devel/Updater_script_MiSTer). In fact, as of today, this tool doesn't implement many fine-grained features that allow you to customize the updating process in depth. In case you value these features, consider to keep using the [MiSTer Updater](https://github.com/MiSTer-devel/Updater_script_MiSTer) as usual. Both tools will coexist in the near future.

### Setup and Usage

Download this [ZIP file](https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/MiSTer_Downloader.zip) and extract `downloader.sh` to your `/Scripts` folder on your primary SD card (create that folder if it doesn't exist). You only need to perform this operation once, since this tool self-updates itself.

To use it, on your MiSTer main menu, go to the *Scripts* screen, and select `downloader`.

### Options

You may create a `downloader.ini` file to tweak some parameters.

Here you can see the default parameters and the options that you may change:

```ini
[MiSTer]
; base_path is where most files will be installed
;   Useful for setups with USB storage, for example: '/media/usb0/'
base_path = '/media/fat/'

; base_system_path is where system files such as 'MiSTer' and 'menu.rbf' will be installed.
;   Warning: It is recommended to NOT change this setting regardless of your setup.
base_system_path = '/media/fat/'

; allow_delete options:
;   0 -> Don't allow this tool to delete anything at all.
;   1 -> Allow this tool to delete any old file from previous updates.
;   2 -> Allow this tool to delete only old cores that receive a new version.
allow_delete = 1

; allow_reboot options:
;   0 -> Don't allow this tool to ever reboot automatically.
;   1 -> Allow this tool to reboot the system after any system file has been updated.
;   2 -> Allow this tool to reboot the system only after Linux has been updated.
allow_reboot = 1

; update_linux options:
;   true -> Updates Linux when there is a new update (very recommended).
;   false -> Doesn't update Linux.
update_linux = true

; parallel_update options:
;   true -> Tries to more than one file simultaneously.
;   false -> Will only download one file at a time.
parallel_update = true

; downloader_timeout: Can be tweaked to increase the timeout time in seconds
;   It is useful to increase this value for users with slow connections.
downloader_timeout = 300

; downloader_retries: Can be tweaked to increase the retries per failed download
;   It is useful to increase this value for users with very unstable connections.
downloader_retries = 3
```

### Roadmap

- [x] Initial Release
- [ ] [Cheats](https://gamehacking.org/mister/) fetching
- [ ] First-run optimisations
- [ ] Configurable custom download filters
- [ ] Handle duplicated `games` folders through symlinks (*GBA* <-> *GBA2P*, and *GAMEBOY* <-> *GAMEBOY2P*)
- [ ] Integration with *MiSTer* binary
