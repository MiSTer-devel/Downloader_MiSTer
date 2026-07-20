# Uninstalling Databases

To remove one or more databases without contacting the network, run the launcher from a
shell:

```bash
update.sh --uninstall DB_ID [DB_ID ...]
```

Downloader removes the files and empty folders recorded in its local store, while keeping
paths that another installed database still owns. It then removes the database sections
from `downloader.ini` and any drop-in files.

If an external drive cannot be verified, the database is refused and the output explains
whether to reconnect the drive or run a full update once to refresh legacy metadata.

To skip this verification, add `--force`:

```bash
update.sh --uninstall DB_ID --force
```

The warning reports only how many external fragments could not be verified, or that the
amount is unknown, because an absent drive's names, paths, and sizes are unavailable.
Content on a truly absent drive is left orphaned.

If a drive disconnects while files are being removed, reconnect it and retry with
`--force`. Successfully removed files are already gone, and the remaining store records
are retried.
