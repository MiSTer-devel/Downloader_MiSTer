# Drop-in Database Files

Drop-in database files extend `downloader.ini` by letting you add new databases in separate files, without editing the main configuration. Just copy a file to your SD card and the downloader picks it up automatically.

This is useful for database maintainers who want to distribute a ready-to-use file that users can just copy to their SD card.

# How It Works

The downloader looks for additional INI files in two places:

1. **Files named `downloader_*.ini`** next to `downloader.ini`
2. **Files inside the `downloader/` folder** next to `downloader.ini`

Both locations are checked automatically on every run. Files are loaded in alphabetical order, with `downloader/` files processed before `downloader_*.ini` files.

**Important:** Drop-in files can only contain database sections. The `[MiSTer]` section (global settings) is not allowed. It must remain in the main `downloader.ini`.

For example, to add a `wallpapers_db` database, create `/media/fat/downloader_wallpapers_db.ini` (or `/media/fat/downloader/wallpapers_db.ini`).

# File Format

Drop-in files use the exact same format as database sections in `downloader.ini`.

```ini
[database_id]
db_url = https://url.to/db.json.zip
```

Since it's the same format, you can also add other supported database options like `filter`, and the `database_id` must match the `db_id` inside the JSON file it points to. See [Custom Databases](custom-databases.md) for more details.

## One Database per File

It is recommended to have one database per file, and to name the file after the database ID. For example, a database with ID `wallpapers_db` should go in `downloader_wallpapers_db.ini` (or `downloader/wallpapers_db.ini`).

Multiple databases in a single file are supported, but keeping one per file makes it easier to add or remove databases independently.

# Rules and Restrictions

### Global settings are not allowed

Drop-in files cannot contain a `[MiSTer]` section.

### No duplicate database IDs

If a database ID already exists in `downloader.ini` or in an earlier drop-in file (alphabetical order), the duplicate is skipped with a warning. The first occurrence always wins.

### Hidden files are ignored

Files starting with `.` (like `.backup.ini`) are skipped.

# For Database Maintainers

If you maintain a custom database, you can distribute a drop-in file so your users don't have to manually edit their `downloader.ini`. Just provide a single `.ini` file with instructions to copy it to either:

- `/media/fat/` with a `downloader_` prefix (simpler for users)
- `/media/fat/downloader/` (recommended for organized setups)
