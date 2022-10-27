# MiSTer Downloader PC Launcher (for Windows, Mac, and Linux)

This launcher is meant to install MiSTer files without using a MiSTer. This is especially useful if your MiSTer is not connected to the internet.

The launcher will install all MiSTer files within the same folder where the launcher itself is placed.

Typically, you would place it in the root of your MiSTer SD card, so that you can do the following updating process:
- Eject the SD from MiSTer and insert it into your PC.
- Use the PC to **run the launcher**.
- After completion, eject the SD card from the PC to put it back on MiSTer.
- Turn on your MiSTer.
- Enjoy your new updates.

## Get the launcher

Download this [ZIP file](https://github.com/theypsilon/Update_All_MiSTer/releases/latest/download/update_all.zip) and extract the file `downloader_pc_launcher.py` to the location where you'll want to install all the files. For example, to the root folder of your MiSTer SD card.

## How to run the launcher on Windows?

First, you need to install Python version 3.9 or higher. The easiest way to do it is through the Microsoft Store. Just click on this [link](https://www.microsoft.com/store/productId/9PJPW5LDXLZ5), press the button to get it, and that's all.

Now that the Python installation is completed, you should see that the downloader_pc_launcher.py file has the Python icon. Then just double-click on it, and a window will open with Downloader running in it.

### Troubleshooting

* **Microsoft Store showed an error when I attempted to install Python**

Just reboot your computer and try again later. The classic windows fix also works here.

* **Double-clicking on the file doesn't execute it, but it opens something else**

This happens most probably because you have another program assigned to this file format. The solution is to open the context menu of the launcher file with the mouse right-click. Then navigate to the "Open with" entry, and select Python over there.

* **It runs but shows an error about the Python binary not being found**

You didn't install Python through the Microsoft Store, right? When you use alternative ways to install Python, you need to make sure that the installed programs are getting included in the system path.

* **I have Python installed but I don't know which version I have**

Open the command prompt, and type `python3 --version` to find out.

## How to run the launcher on Linux or Mac?

1. Make sure you have installed Python version 3.9 or higher.
2. Open the terminal, and in the same folder where you have placed the launcher execute the following command: 
```sh
python3 downloader_pc_launcher.py
```

## Incompatibilities

The PC Launcher is not compatible with `downloader.ini` files that have custom `base_path` or `storage_priority` fields. These fields are only meant to be used within MiSTer and don't make sense outside it, so the program will not proceed when it detects them.