# Priority Storage Requirements

Paths starting with | are paths that might be external. By external I mean, they can live outside the base_path (the SD). They can live in other drives, that have their own .downloader_store.json file and is aggregated to the main one.

Paths starting with | are also called "pext paths" where pext means "P-otentially EXT-ernal".

Pext paths are categorized based on the top folder, which is also called "pext parent", and its first children,also called "pext subfolder", combined.
The combination is called "pext base" and it has a fixed drive assigned to it. The tree under it is called the "pext children".

  - For example, |games/nes/smb.nes is of category games/nes, this means all the files contained within games/nes will be treated in the same way.
  - Two different categories can live in different drives. For example the pext base |games/nes can live in /media/fat and the pext base |games/snes can live in /media/usb1

### Prefer SD

- When the pext base is not present in any external drives, the pext base will be created in the base_path drive (usually the SD).
- When the pext base is present in one or more external drives, the pext children will be placed in an external drive following the priority drive order (defined in constants.py).
- The pext parent by itself doesn't contain enough information to specify where should be created. You need to check the other derived pext bases.
  - If there is NO pext bases at all, the pext base will be created on the base_path drive (SD).
  - If there are, for each drive that contains the derived base, a pext parent will be created.


##### Corner cases
- When a folder is about to be distributed in a DB, a user might be aware of it and create a pext subfolder in his external storage. That way it's gonna be picked by the Prefer SD config and the new files will end up in the external storage. This DB update could have a problem and be rolled back, but while it was live, the user would have installed it, updating his store. Later, when the folder is missing in the DB because of the rollback, the user might update again. We don't want to remove the "pext subfolder" he created from his external storage because otherwise he would have to create it again, anticipating a new version of the DB with the folder back. Thus, we don't want to remove "pext subfolders" or "pext bases" altogether in external devices, unless the users remove them manually. The store needs to track the pext parent so that they can be removed if the user remove the pext subfolder manually. This is not applicable to the non-pext paths, or pext paths that end up in the standard drive. In that case, we want to remove the subfolder and even the whole "pext base" if the DB indicates so.
- When a DB with pext paths ends up in store, but the pext is resolved to the main drive (SD usually), we are losing information. This information is recovered from the DB that contains these pext paths again. But if they get removed in the DB, the information is totally lost. Since the pext paths that end up in the standard drive behave same as non-pext paths, this could be fine. But this might be a problem in some particular scenarios that I haven't figured out yet. 

### Prefer External

- When there is no external drives, the pext base will be created in the base_path drive (usually the SD).
- When there is one external drives, the pext base will be created in an external drive following the priority drive order (defined in constants.py).

### Off

- No matter what, all the paths are installed on the base_path drive.
