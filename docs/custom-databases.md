# Custom Databases

This feature allows users to download more files than the ones present at the official [MiSTer Distribution repository](https://github.com/MiSTer-devel/Distribution_MiSTer).

To use a custom DB to the Downloader, you only need to add a new section at the bottom of `/media/fat/downloader.ini` which should read like this:
```ini
[your_section_id]
db_url = 'https://url_to_db.json.zip'
```

Where `your_section_id` should be replaced with the unique ID of the database you are adding (see the `db_id` field from the json for more details).

On the other hand, database maintainers need to hang on that URL specified by the property `db_url`, a collection of links following this json format:
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
     * [Optional] Databases can specify default options, like default filters, default url_safe_characters, etc... 
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

The json file can be contained in a ZIP file. In that case, provide the URL of that file, which should end with the extension `*.json.zip`.

### Important note about the Database ID

It's very important to **NOT** change your database ID once you have published a collection for it. That ID is used by the downloader to track changes in files, and by changing it users could end up with duplicated files in the future, since name changes won't be detected. Also, you will bloat the local database of a user if you change this ID frequently, which would lead to a waste of space in the SD and to longer run times of the Downloader.

Once you published a collection with a given database ID, please stick to it whenever you update that collection.

### Restrictions

1. The files and folders dictionary keys must be relative paths. They can not contain `..` nor be empty strings. They also can't point to common system folders, such as 'linux' or 'saves'. And finally, they can't be any system file such as: 'MiSTer', 'menu.rbf', 'MiSTer.ini' 

2. Only fields documented here should be used.

### Default Options

_NOTE:_ First, I would like to remind you that the **global options** and their default values are documented [here](https://github.com/MiSTer-devel/Downloader_MiSTer#options).

Databases can redefine the default option values that will apply to them. If they do so, these new default values will overshadow the global default values shown in that page linked above. You may refer to these definitions as "**database-scoped default options**" as opposed to "**global default options**".

The options whose default values can be redefined as **database-scoped default options** are:
- parallel_update
- update_linux
- downloader_size_mb_limit
- downloader_process_limit
- downloader_timeout
- downloader_retries

Since we are talking about default options, I'd like to remind that the default option values are only considered when users don't modify that value for that given option in the `downloader.ini` file.

This is an example of how you would define **database-scoped default options** in the database file. In this case, only the default value of the option "_parallel_update_" will be changed:
```js
    "default_options": {
        /**
        * [Optional] Parallel Update (boolean). Should files be downloaded in parallel?
         *           If missing, the global default value will be used.
        */
        "parallel_update": false
    },
```

Additionally, users can define option values affecting only a specific database. They will do it like this:

```ini
[your_section_id]
db_url = 'https://url_to_db.json.zip'
parallel_update = true
```

These option definitions are known as **database-scoped options**.

Continuing the previous example, a user with that section in their `downloader.ini` file will make sure that he will always download files in parallel for that database, regardless of what the `default_options` field defines in the respective database file.
