# Custom Databases

This feature allows users to add additional update sources not present in the official [MiSTer Distribution repository](https://github.com/MiSTer-devel/Distribution_MiSTer).

New repositories can be added to the bottom of `/media/fat/downloader.ini`:
```ini
[*custom_db_id*]
db_url = 'https://url_to_db.json.zip'
```
The `db_url` entry points to a JSON file that a maintainer has published. The `*custom_db_id*` entry must match the `db_id` of the JSON file.

The format of the aforementioned JSON file should be as follow:
```js
{
    /**
     * [Mandatory] It should match the corresponding section_id defined in the INI file (string)
     *  Important: This ID must identify unequivocally your collection in the whole MiSTer ecosystem.
     */
    "db_id": "Your database ID",


    /**
     * [Mandatory] UNIX Epoch Time taken during the generation of this file (number)
     *
     * Relevant utilities
     *  · date +%s
     *  · https://www.unixtimestamp.com/
     */
    "timestamp": 1636133398,
        
  
    /**
     * [Mandatory] Files to be downloaded
     */
    "files": {
        /**
          * The keys of the dictionary are the paths of the files you want to download.
          * Paths should be unique in the system in order to avoid conflicts. In other
          * words, different collections should never share same paths.
          */
        "path/of/file_1.rbf": {
            /**
            * [Mandatory] MD5 Hash of the file (string)
            */
            "hash": "bb0d0c1aa2f709a1d704aa9cf56f909a",
          
          
            /**
            * [Mandatory] Size in bytes of the file (number)
            */
            "size": 2323,
          
          
            /**
            * [Mandatory if the top level field `base_files_url` is missing]
            * [Optional otherwise]
            *            Download source (string).
            *            If this field is missing, it will be calculated with (`base_files_url` + the key of the file).
            *            Or it will error if `base_files_url` is also missing.
            */
            "url": "https://url_to_db/path/of/file1.rbf",

            /**
             * [Optional] List of tags or tag indexes associated with current file (list of strings OR list of numbers)
             *            The download filters feature uses this to match this file.
             *            Default value: empty list.
             */
            "tags": [],
          
            /**
            * [Optional] If there is a file already present in the path, should it be overwritten? (boolean)
            *            Default value: true
            */
            "overwrite": true,
          
          
            /**
            * [Optional] Should reboot after installing this file? (boolean).
            *            Default value: false
            */
            "reboot": false,
        },
      
      
        /**
          * ... Same for other files ...
          */
        "path/of/file_n.rbf": {
            "hash": "a4e99951f5033590e583afd1a66cb650",
            "size": 34234,
        },
    },
  
  
    /**
     * [Mandatory] Folders to be created
     */
    "folders": {
        /**
          * The keys of the dictionary are the parent folders of the files you want to create.
          */
        "folder/path1/": {
            /**
             * [Optional] List of tags or tag indexes associated with current folder (list of strings OR list of numbers)
             *            The download filters feature uses this to match this folder.
             *            Default value: empty list.
             */
            "tags": [],
        },
      
      
        /**
          * ... Same for other folders ...
          */
        "folder/path_n/": {}
    },
    
    //
    // Following fields are optional and may be omitted. Database maintainers may achieve most use cases with the
    // fields documented above. Feel free to stop reading the following documentation.
    //
    
    /**
     * [Optional] The common initial part of all your URLs in this DB (string). It allows saving space in the database
     *            file, if the initial part of the URL is redundant accross the entire database.
     */
    "base_files_url": "https://raw.githubusercontent.com/theypsilon/Downloader_MiSTer/",

    /**
     * [Optional] Defines a key-value map that links between tags and tag indexes. Tags are used by download filters.
     *            They allow matching the files containing the tags specified by the filter terms.
     *            Tag indexes are more efficient to use than whole tags, thus this dictionary allows better performance.
     */
    "tag_dictionary": {
        /**
          * The keys of the dictionary are the filter tags. They are matched against the terms introduced in the filters.
          *     They must be strings. But transformed into lowercase letters and stripped of `_` and `-` characters.
          *     Matching will happen regardless of the transformation. For example, term 'Some-Tag' matches key 'sometag'.
          * The values of the dictionary are the term indexes. They must be integers.
          * 
          * Examples:
          */
        "sometag": 0,
        "othertag": 1
    }
  
  
    /**
     * [Optional] Local databases to import before fecthing the online databases.
     *            During the local import, nothing is fetched. Only the local store is updated if the files
     *            from the local databases matches with the files on the filesystem.
     *            These loccal databases will be imported just once, then the file will be removed.
     */
    "db_files": [],
        
    /**
     * [Optional] Databases can specify default options, like default filters, default downloader_timeout, etc... 
     */
    "default_options": {
        // Documented in the "Default Options" section of this page.
    },
  
  
    /**
     * [Optional] Databases can use ZIPs to download and install a big amount of files more efficiently.
     */
    "zips": {
        // TO BE DOCUMENTED
    },
}
```

A maintainer can compress their JSON file inside of a ZIP archive. If they choose to do so, the file must extension be: `*.json.zip`

### Database IDs ["db_id"]

Once a database has been published it's very important that it's ID is **NEVER** changed and persists through any modifications of the JSON file. The ID is used by the downloader to track changes and maintain it's database on the local system. Without the correct ID: duplicate files can appear and clean-up operations will not run.

### Restrictions

1. The files and folders must use relative paths. They may not contain: `..` or empty strings, or point to any common system folders ['/linux' or '/saves'] or system files ['MiSTer', 'menu.rbf', 'MiSTer.ini']. 

2. Only fields documented here should be used.

### External Paths

Files and folders paths can be defined as *potentially external* paths. That way, thanks to the **Storage Priority Resolution** feature, files can be installed on external storage, thus saving space on the main SD card.

For a path to be considered as potentially external, it must be prepended with the symbol `|`.

Example paths: `|games/PSX/tomb_raider.chd`, `|docs/AO486/Manual.pdf`

In practice, downloader will install both files at `games/PSX/tomb_raider.chd` and `docs/AO486/Manual.pdf`, but these relative paths can be located on external storages if the circumstances specified on the `storage_priority` [documentation](../README.md#options) occur.

### Default Options

Options for a repository can be defined in `/media/fat/downloader.ini` following the `db_url` entry. Here is an example that sets "_filter_" option for the *custom_db_id* repository:
```ini
[*custom_db_id*]
db_url = 'https://url_to_db.json.zip'
filter = arcade
```
The following options can be defined:
- filter
- update_linux
- downloader_size_mb_limit
- downloader_process_limit
- downloader_timeout
- downloader_retries
- base_path

Using the same list: maintainers can also set new default options [for any users haven't set themselves] that will only apply to their repository; think of these as **database-scoped defaults**.

Here is an example that sets the **database-scoped default** for the "_filter_" option:
```js
    "default_options": {
        /**
        * [Optional] Parallel Update (boolean). Should files be downloaded in parallel?
         *           If missing, the global default value will be used.
        */
        "filter": "arcade"
    },
```

Any option not set by a user or a maintainer will continue to use it's [global value](https://github.com/MiSTer-devel/Downloader_MiSTer#options).
