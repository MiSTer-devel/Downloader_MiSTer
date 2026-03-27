# Archives

This document extends the [Custom Databases](custom-databases.md) specification with support for compressed archives.

Archives bundle large file collections (MRAs, palettes, cheats) into a single usually compressed download. Instead of fetching thousands of small files individually, Downloader fetches one archive and extracts from it. Currently only the ZIP format is supported.

## The `archives` field

Add an `archives` object at the top level of your database JSON. Each key is a unique archive ID, and each value is an archive descriptor.

The `extract` field determines how files are pulled from the archive. There are two extraction modes:

- **`all`** — Extracts every file into a `target_folder`. Best for collections always installed in full (e.g. palettes, filters).
- **`selective`** — Extracts individual files on demand. Best for large collections where users may only need a subset (e.g. game cheats, BIOS ROMs).

A full archive descriptor has the following fields:

```js
"archives": {
    "nes_palettes": {
        "format": "zip",                              // [Mandatory] Currently only "zip" is valid
        "extract": "all",                              // [Mandatory] "all" or "selective"
        "description": "Extracting NES Palettes",      // [Mandatory] Shown to the user during extraction

        "target_folder": "games/NES/",                 // [Mandatory for extract "all"] Where files are placed
                                                       //   Not used by extract "selective".

        "archive_file": {                              // [Mandatory] The compressed download (same format as file entries in custom-databases.md)
            "hash": "4d2bf07e5d567196d9c666f1816e86e6", //   MD5 hash
            "size": 7316038,                             //   Size in bytes
            "url": "https://example.com/palettes.zip"    //   Download URL
        },

        // [Mandatory] Exactly one of the following two. See "Summaries" below.
        "summary_inline": { ... },
        // OR
        "summary_file": { ... },

        "base_files_url": "https://raw.githubusercontent.com/...", // [Optional] Base URL for per-file fallback downloads
        "path": "pext"                                             // [Optional] Enable external storage (see custom-databases.md)
    }
}
```

## Summaries

Every archive descriptor must include exactly one of `summary_inline` or `summary_file`. Both list the files and folders contained in the `archive_file`.

- When `extract` is `"all"`, the summary is used to track installed files for hash verification and cleanup of removed entries on subsequent runs.
- When `extract` is `"selective"`, the summary determines **which** files will be extracted from the archive, and is also used for tracking.
- Files listed in archive summaries may omit both `url` and the archive `base_files_url`. If no database-level `base_files_url` is available either, Downloader can only install them by extracting from `archive_file`; if extraction or post-extraction validation fails, there is no per-file fallback download.

> **Note:** If both `summary_inline` and `summary_file` are provided, `summary_file` takes priority and `summary_inline` is ignored.

### summary_inline

Embeds the listing directly in the database JSON. Simpler to generate, avoids an extra network request, but increases database size. Best for archives with few files.

The `files` and `folders` entries follow the same format as the top-level [`files` and `folders`](custom-databases.md) fields, with two additional archive-specific fields: `arc_id` and `arc_at`.

```js
"summary_inline": {
    "files": {
        "games/NES/palettes/file.pal": {
            "hash": "aa0d0c1aa2f709a1d704aa9cf56f909a",  // [Mandatory] MD5 hash
            "size": 192,                                   // [Mandatory] Size in bytes
            "arc_id": "nes_palettes",                      // [Mandatory] Must match the archive key
            "arc_at": "palettes/file.pal",                 // [Mandatory] Location within the archive_file
            "tags": []                                     // [Optional]  For download filters (see custom-databases.md)
        }
    },
    "folders": {
        "games/NES/palettes": {
            "arc_id": "nes_palettes"                       // [Mandatory] Must match the archive key
        }
    }
}
```

### summary_file

References an external JSON containing the same `files`/`folders` structure as `summary_inline`. The downloader fetches it separately. Best for archives with many files, where inlining would bloat the database.

```js
"summary_file": {
    "hash": "b5d85d1cd6f92d714ab74a997b97130d",              // [Mandatory] MD5 hash
    "size": 84460,                                             // [Mandatory] Size in bytes
    "url": "https://example.com/nes_palettes_summary.json.zip" // [Mandatory] Download URL (see below)
}
```

The file at the `url` must be a JSON with the same `files`/`folders` structure described in `summary_inline`:

```js
{
    "files": { ... },  // as in summary_inline
    "folders": { ... }  // as in summary_inline
}
```
