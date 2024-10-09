# Priority Storage Requirements

Paths starting with | are paths that might be external. By external I mean, they can live outside the base_path (the SD). They can live in other drives, that have their own .downloader_store.json file and is aggregated to the main one.

Paths starting with | are also called "pext paths" where pext means "P-otentially EXT-ernal".

Pext paths are categorized based on the top folder, which is also called "pext parent", and its first children combined.
The combination is called "pext base" and it has a fixed drive assigned to it. The tree under it is called the "pext children".

  - For example, |games/nes/smb.nes is of category games/nes, this means all the files contained within games/nes will be treated in the same way.
  - Two different categories can live in different drives. For example the pext base |games/nes can live in /media/fat and the pext base |games/snes can live in /media/usb1

### Prefer SD

- When the pext base is not present in any external drives, the pext base will be created in the base_path drive (usually the SD).
- When the pext base is present in one or more external drives, the pext children will be placed in an external drive following the priority drive order (defined in constants.py).
- The pext parent by itself doesn't contain enough information to specify where should be created. You need to check the other derived pext bases.
  - If there is NO pext bases at all, the pext base will be created on the base_path drive (SD).
  - If there are, for each drive that contains the derived base, a pext parent will be created.

### Prefer External

- When there is no external drives, the pext base will be created in the base_path drive (usually the SD).
- When there is one external drives, the pext base will be created in an external drive following the priority drive order (defined in constants.py).

### Off

- No matter what, all the paths are installed on the base_path drive.
