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

## Exit codes

- `0`: every selected database was uninstalled successfully.
- `1`: uninstall failed and no single recovery-specific exit code applies.
- `22`: uninstall was refused because external content could not be verified. Reconnect
  all drives or run a full update to refresh legacy metadata; use `--force` only when
  accepting potentially orphaned external content.
- `23`: an external drive disconnected during removal. Reconnect it before retrying.
- Other non-zero values retain their existing Downloader-wide meanings.
