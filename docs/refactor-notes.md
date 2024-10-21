# Refactor Notes

- The actual removal of files could happen right after index processing if the index processing ends up with a barrier that waits for files to be downloaded.
- When we store the zip_index in the store, should it contain pext paths or not?
  - This zip index, is gonna be the source of next runs if there_is_a_recent_store_index is False
  - By now, this information can be deduced from zip_description path and target_folder_path but this does not work if there are mixed "pext" and non-pext paths.