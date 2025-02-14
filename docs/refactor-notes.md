# Refactor Notes

- The actual removal of files could happen right after index processing if the index processing ends up with a barrier that waits for files to be downloaded.
- When we store the zip_index in the store, should it contain pext paths or not?
  - This zip index, is gonna be the source of next runs if there_is_a_recent_store_index is False
  - By now, this information can be deduced from zip_description path and target_folder_path but this does not work if there are mixed "pext" and non-pext paths.
- Need to do a store change after the refactor: Cheats has currently zip_id cheats_folder_snes, it should not have zip_id at all, same with Games, which has zip_id nes_palettes and should not have zip_id either. Furthermore, Cheats or Games should be expected to be identical within the zip summary folders and within the db folders. So we might want to be checking db.folders when processing the zips. That should allow a logic simplification when processing pext parents & pext subfolders, since we now need to infere store information based on its children and that should no longer be necessary.