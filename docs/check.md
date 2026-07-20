# Checking for Updates

Use `--check` to check configured databases for available updates without installing,
removing, or changing any downloaded content:

```bash
update.sh --check
```

The short form is `-c`:

```bash
update.sh -c
```

To check only specific databases, list their IDs after the option:

```bash
update.sh --check DB_ID [DB_ID ...]
```

Database IDs are matched case-insensitively, and duplicates are ignored. If any supplied
ID is not configured, the entire check is rejected without checking the other IDs.

The final status is one of:

- `UP_TO_DATE` — all checked databases are current.
- `UPDATE_AVAILABLE` — at least one checked database has an update.
- `FAILED` — a database or local-state check failed.

Both `UP_TO_DATE` and `UPDATE_AVAILABLE` exit successfully with code `0`. Failures exit
with code `1`, while invalid database IDs exit with code `10`.
