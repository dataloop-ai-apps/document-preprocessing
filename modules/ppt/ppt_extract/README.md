# PPT Extraction

This app extracts text from PowerPoint (PPT/PPTX) files and uploads it as text files to Dataloop. 
The extracted content includes text from individual slides and can optionally include speaker notes and table content.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `extract speaker notes`: A boolean parameter that determines whether speaker notes from the PowerPoint slides should be extracted. Default is `False`.
- `extract tables`: A boolean parameter that determines whether text from tables in the PowerPoint slides should be extracted. Default is `False`.
- `remote path for extractions`: The path where the extracted text files will be saved in the Dataloop dataset after processing.

### Methods

#### `ppt_extraction(self, item: dl.Item, context: dl.Context) -> List[dl.Item]`

This method handles the PowerPoint extraction process:

1. Downloads the PPT/PPTX file from Dataloop.
2. Extracts text content from each slide of the presentation and saves it as individual TXT files.
3. Optionally, extracts speaker notes and table content from each slide.
4. Uploads the extracted content as new text items to Dataloop.

#### `extract_text_from_ppt(ppt_path: str, extract_notes: bool = False, extract_tables: bool = False) -> List[str]`

Extracts text content from each slide of the PowerPoint file:

- Each slide's text is saved as a separate `.txt` file.
- Optionally includes speaker notes and table content if specified.
- Returns a list of paths to the generated `.txt` files.

#### `_extract_table_text(table) -> str`

Extracts text from PowerPoint tables:

- Each table row's content is joined by tabs.
- Rows are separated by newlines.
- Returns formatted table text as a string.

## Supported File Types

- `.ppt` (PowerPoint 97-2003 format)
- `.pptx` (PowerPoint 2007+ format)

## Text Extraction Features

- **Slide Content**: Extracts text from all text shapes on each slide
- **Speaker Notes**: Optionally extracts presenter notes associated with each slide
- **Tables**: Optionally extracts and formats text content from tables within slides
- **Structured Output**: Each slide is saved as a separate text file for easy processing 