# Linux & Main Update Corruption Repro Test

This test is trying to verify that a corrupted MiSTer binary file is not being produced in your MiSTer (aka "black screen problem").

Such corruptions have happened in the past when Linux & Main updates were performed via updaters in a non-deterministic way and with a very low incidence.

This test is trying to prove that nowadays this file corruption doesn't happen anymore with the downloader.

### How to Run

Prerequiste: Bash >= 4.0 + common unix utilities

1. Connect via SSH to your MiSTer, and add the line `/media/fat/repro.sh` to the end of your `/media/fat/linux/user-startup.sh` file.
2. Download this repository and cd to it.
3. Put your MiSTer ip in the file `mister.ip`
4. If you changed your MiSTer root password, put it in the file `mister.pw`, otherwise skip this step.
5. Run the following command: `./src/test/exploratory/linux_and_main_update_corruption/test_corruption.sh` . Its output will display what is going on in your MiSTer. You may reconnect later on by running this script again.
6. Reboot your MiSTer

After that, your MiSTer should reboot automatically every few minutes, showing correct video input via HDMI/VGA (no black screen).

This test never stops. In order to deactivate it, remove the line `/media/fat/repro.sh` from your `/media/fat/linux/user-startup.sh` file.

### Test Result

After running it for some hours, check if you have the file `/media/fat/failed_repro.log` in your MiSTer.

If you have it, it means you could reproduce the bug and it would be valuable if you share that `/media/fat/failed_repro.log` file. When you report this, please share also your SD card model.

If after an arbitrary long time no such file has showed up, that means that your MiSTer succesffully updates without any file corruption.

Please report this result and the number of hours that you have waited.
