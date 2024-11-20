# PDF Extraction

This app extracts text and optionally images from PDF files and uploads them as text and image files to Dataloop. 
The extracted content includes individual page text and can also include images from each page of the PDF.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `extract images`: A boolean parameter that determines whether images from the PDF should be extracted. Default is `False`.
- `remote path for extractions`: The path where the extracted text and image files will be saved in the Dataloop dataset after processing.

### Methods

#### `pdf_extraction(self, item: dl.Item, context: dl.Context) -> List[dl.Item]`

This method handles the PDF extraction process:

1. Downloads the PDF file from Dataloop.
2. Extracts text content from each page of the PDF and saves it as individual TXT files.
3. Optionally, extracts images from each page and saves them as separate image files.
4. Uploads the extracted content (text and/or images) as new items to Dataloop.

#### `extract_text_from_pdf(pdf_path: str) -> List[str]`

Extracts text content from each page of the PDF file:

- Each page's text is saved as a separate `.txt` file.
- Returns a list of paths to the generated `.txt` files.

#### `extract_images_from_pdf(pdf_path) -> List`

Extracts images from the PDF file:

- Each image on each page is saved as a separate image file (e.g., PNG, JPG).
- Returns a list of paths to the saved image files extracted from the PDF.

