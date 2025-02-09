Starts after reading the config.

- START: FetchFileJob [db] -> ValidateFileJob [db] -> OpenDbJob -> ProcessDbJob -> (1, 2, 3)
- 1: ProcessDbJob -> ProcessIndexJob -> (6)
- 2: ProcessDbJob -> ProcessZipJob -> (4, 5)
- 3: ProcessDbJob -> FetchFileJob [zip index] -> ValidateFileJob [zip index] -> OpenZipIndexJob -> ProcessZipJob -> (4, 5)
- 4: ProcessZipJob -> FetchFileJob [zip contents] -> ValidateFileJob [zip contents] -> OpenZipContentsJob -> END
- 5: ProcessZipJob -> ProcessIndexJob -> (6)
- 6: ProcessIndexJob -> FetchFileJob [file] -> ValidateFileJob [file] -> END
