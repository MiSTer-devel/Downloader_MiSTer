Starts after reading the config.

- START: FetchFileJob2 [db] -> ValidateFileJob2 [db] -> OpenDbJob -> ProcessDbJob -> (1, 2, 3)
- 1: ProcessDbJob -> ProcessIndexJob -> (6)
- 2: ProcessDbJob -> ProcessZipJob -> (4, 5)
- 3: ProcessDbJob -> FetchFileJob2 [zip index] -> ValidateFileJob2 [zip index] -> OpenZipIndexJob -> ProcessZipJob -> (4, 5)
- 4: ProcessZipJob -> FetchFileJob2 [zip contents] -> ValidateFileJob2 [zip contents] -> OpenZipContentsJob -> END
- 5: ProcessZipJob -> ProcessIndexJob -> (6)
- 6: ProcessIndexJob -> FetchFileJob2 [file] -> ValidateFileJob2 [file] -> END
