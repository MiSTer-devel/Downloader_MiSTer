# Custom Databases

To add a custom DB to the Downloader, you need to add a new section at the bottom of `/media/fat/downloader.ini` which should read like this:
```ini
[your_section_id]
db_url = 'https://url_to_db.json.zip'
```

Where `your_section_id` should be replaced with the unique ID of the database you are adding (see the `db_id` field from the json for more details).

Here is the format of the json DB file:
```js
{
    /**
     * [Mandatory] It should match the corresponding section_id defined in the INI file (string)
     *  Important: This ID must identify unequivocally your collection in the whole MiSTer ecosystem.
     */
    "db_id": "Your database ID",


    /**
     * [Mandatory] UNIX Epoch Time taken during the generation of this file (number)
     *  Important: The system setting up this value should have the timezone configured correctly.
     *
     * Relevant utilities
     *  · date +%s
     *  · https://www.unixtimestamp.com/
     */
    "timestamp": 1636133398,
  
  
    /**
     * [Mandatory] Can be empty, the common initial part of all your URLs in this DB (string)
     */
    "base_files_url": "https://raw.githubusercontent.com/theypsilon/Downloader_MiSTer/",
  
  
    /**
     * [Mandatory] Can be empty
     */
    "db_files": [
        // TO BE DOCUMENTED
    ],
  
  
    /**
     * [Mandatory] Can be empty
     */
    "default_options": {
        // TO BE DOCUMENTED
    },
  
  
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
             * [Optional] Download source (string). If missing, it will be calculated with:
             *            (base_files_url + the key of the file)
             */
            "url": "https://url_to_db/path/of/file1.rbf",
          
          
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
        }
    },
  
  
    /**
     * [Mandatory] Folders to be created
     */
    "folders": {
        /**
          * The keys of the dictionary are the parent folders of the files you want to create.
          */
        "folder/path1/": {
            // TO BE DOCUMENTED
        },
      
      
        /**
          * ... Same for other folders ...
          */
        "folder/path_n/": {}
    }


    /**
     * [Mandatory] Can be empty. Zips are only meant to be used for downloading very big
     *             quantities of files more efficiently. For most collections, like the
     *             ones with less than 1000 files, the "zips" field should just be empty.
     */
    "zips": {
        // Go to the section 'Zip Format' from this document for all the details.
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

### Zip Formats (Optional)

If you would like to use ZIPs for optimizing the downloader process, usually because your collection includes a very big amount of files (1000+), you may declare ZIPs in your database.

##### Expanding the zips field in the json DB file

For that you would have to expand the `zips` field from your json DB file, with the following information:
```js
    /**
      * ... Other fields previously documented ...
      */


    "zips": {
        /**
          * The keys of the dictionary are the Zip IDs. Zip IDs must be unique within its
          * collection, but can clash with other IDs in other collections without issue.
          */
        "first_zip_id": {
            /**
             * [Mandatory] Can be empty (string)
             *             Same as the outer field "base_files_url" but for current zip context
             */
            "base_files_url": "https://raw.githubusercontent.com/theypsilon/Downloader_MiSTer/",


            /**
             * [Mandatory] List of top level elements inzide the zip (list[string])
             */
            "contents": ["FolderA"],


            /**
             * [Mandatory] Path from where the content file must be unzipped (string)
             */
            "path": "ZipTarget",


            /**
             * [Mandatory] Contains metadata for the content file
             */
            "contents_file": {
                /**
                * [Mandatory] MD5 Hash of the file (string)
                */
                "hash": "bb0d0c1aa2f709a1d704aa9cf56f909a",
            
            
                /**
                * [Mandatory] Size in bytes of the file (number)
                */
                "size": 2323,
            
            
                /**
                * [Mandatory] URL for downloading the content file (string)
                * Note: The file format itself will be documented
                *       in the section: Zip Additional Formats
                */
                "url": "https://url_to_first_zip_id_content.zip",
            }


            /**
             * [Mandatory] Contains metadata for the summary file
             */
            "summary_file": {
                /**
                * [Mandatory] MD5 Hash of the file (string)
                */
                "hash": "bb0d0c1aa2f709a1d704aa9cf56f909a",
            
            
                /**
                * [Mandatory] Size in bytes of the file (number)
                */
                "size": 2323,
            
            
                /**
                * [Mandatory] URL for downloading the summary file (string)
                * Note: The file format itself will be documented
                *       in the section: Zip Additional Formats
                */
                "url": "https://url_to_first_zip_id_summary.json.zip",
            },


            /**
             * [Mandatory] Amount of files contained in the summary (number)
             */
            "files_count": 124,


            /**
             * [Mandatory] Amount of folders contained in the summary (number)
             */
            "folders_count": 34,


            /**
             * [Mandatory] Sum of all file sizes contained in the summary (number)
             */
            "raw_files_size": 343434,
        },


        /**
         * ... Same for other zip definitions ...
         */
        "second_zip_id": {
            "base_files_url": "https://base_files_url",
            "contents": ["SecondFolder"],
            "path": "./",
            "contents_file": {
                "hash": "4d2bf07e5d567196d9c666f1816e86e6",
                "size": 7316038,
                "url": "https://contents_file"
            },
            "summary_file": {
                "hash": "b5d85d1cd6f92d714ab74a997b97130d",
                "size": 84460,
                "url": "https://summary_file"
            }
            "files_count": 1858,
            "folders_count": 0,
            "raw_files_size": 6995290,
        }
    },


    /**
      * ... Other fields previously documented ...
      */
```

Additionally, you would have to prepare two extra files for each declared zip_id:
- The content file
- The summary file

##### The content file

This is the actual ZIP file containing all you would like to distribute within it. It must be a standard zip, containing files or folders. It will be unzipped as-is, within the folder specify by the field `path` in its respective zip_id section.

##### The summary file

This is a json file. It could be zipped or not. In case it's zipped, the URL should end with the extension `*.json.zip`.

This is the format of the zip summary json file:

```js
{
    /**
     * [Mandatory] Files to be downloaded
     * Note: The format of this object is similar but NOT IDENTICAL to the homologous field
     *       of the database json object shown above.
     */
    "files": {
        /**
          * The keys of the dictionary are the paths of the files you want to download.
          * Paths should also be unique in the system.
          */
        "path/of/file_1.rbf": {
            /**
             * [Mandatory] Zip ID pointing to this summary file (string)
             */
            "zip_id": "first_zip_id",


            /**
             * [Mandatory] MD5 Hash of the file (string)
             */
            "hash": "bb0d0c1aa2f709a1d704aa9cf56f909a",
          
          
            /**
             * [Mandatory] Size in bytes of the file (number)
             */
            "size": 2323,
          
          
            /**
             * [Optional] Download source (string). If missing, it will be calculated with:
             *            (base_files_url + the key of the file)
             */
            "url": "https://url_to_db/path/of/file1.rbf",
          
          
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
            "zip_id": "first_zip_id",
            "hash": "a4e99951f5033590e583afd1a66cb650",
            "size": 34234,
        }
    },


    /**
     * [Mandatory] Folders to be created
     * Note: The format of this object is similar but NOT IDENTICAL to the homologous field
     *       of the database json object shown above.
     */
    "folders": {
        /**
          * The keys of the dictionary are the parent folders of the files you want to create.
          */
        "folder/path1/": {
            /**
             * [Mandatory] Zip ID pointing to this summary file (string)
             */
            "zip_id": "first_zip_id",
        },
      
      
        /**
          * ... Same for other folders ...
          */
        "folder/path_n/": {"zip_id": "first_zip_id"}
    }
}
```
