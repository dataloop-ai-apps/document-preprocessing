# DOC Extraction

This app extracts content from DOC/DOCX files and uploads it as a TXT file. The extracted content includes paragraphs
and optionally tables. The service is designed to be used within a Dataloop environment and allows for customizing the
extraction process, including whether to extract tables from the document.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `extract tables`: A boolean parameter that determines whether tables in the DOCX file should be extracted. Default
  is `True`.
- `remote path for extractions`: The path where the extracted TXT files will be saved in Dataloop dataset after
  processing.

### Methods

#### `doc_extraction(self, item: dl.Item, context: dl.Context) -> dl.Item`

This method handles the extraction process:

1. Downloads the DOC or DOCX file from Dataloop.
2. Converts `.doc` files to `.docx` if needed.
3. Extracts the text content from the DOCX file, including tables if specified.
4. Uploads the extracted content as a new TXT item to Dataloop.

#### `extract_content(docx_path, local_path, extract_tables=True)`

Extracts text from a DOCX file, optionally including tables:

- Paragraphs are extracted as text.
- Tables are extracted with each row's content joined by tabs.


