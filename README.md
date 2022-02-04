# MiSTer Downloader

This tool installs and **updates all the cores** and other extra files for your *MiSTer*. It also updates the menu core, the MiSTer firmware and the Linux system. The source for all downloads is the [MiSTer Distribution](https://github.com/MiSTer-devel/Distribution_MiSTer) repository.

The **MiSTer Downloader** is a substitute for the [MiSTer Updater](https://github.com/MiSTer-devel/Updater_script_MiSTer), and is meant to offer a more safe and robust experience, while being much faster.

As a drawback, the **Downloader** is not backwards compatible with the old INI files that were configured for the [MiSTer Updater](https://github.com/MiSTer-devel/Updater_script_MiSTer). In fact, as of today, this tool doesn't implement many fine-grained features that allow you to customize the updating process in depth. In case you value these features, consider to keep using the [MiSTer Updater](https://github.com/MiSTer-devel/Updater_script_MiSTer) as usual. Both tools will coexist in the near future.

### Setup and Usage

Download this [ZIP file](https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/MiSTer_Downloader.zip) and extract `downloader.sh` to your `/Scripts` folder on your primary SD card (create that folder if it doesn't exist). You only need to perform this operation once, since this tool self-updates itself.

To use it, on your MiSTer main menu, go to the *Scripts* screen, and select `downloader`.

### Options

You may create a `/media/fat/downloader.ini` file to tweak some parameters.

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
- [x] [Cheats](https://gamehacking.org/mister/) fetching
- [x] First-run optimisations
- [x] Configurable custom download filters
- [ ] Games folders resolution auto-detecting connected drives
- [ ] Integration with *MiSTer* binary

Check the [CHANGELOG](CHANGELOG.md) for more information about past releases.

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

### Supporters+ shout-out!

Antonio Villena, Hard Rich, Matt Hargett, and MiSTerFPGA.co.uk

Thank you so much for supporting this project! If you would like to show up here, join us as **Supporter+** on Patreon:

<a href="https://www.patreon.com/bePatron?u=37499475"><img src="https://camo.githubusercontent.com/2b7105015397da52617ce6775a339b0b99d689d6f644c2ce911c5d472362bcbd/68747470733a2f2f63352e70617472656f6e2e636f6d2f65787465726e616c2f6c6f676f2f6265636f6d655f615f706174726f6e5f627574746f6e2e706e67"></img></a>
