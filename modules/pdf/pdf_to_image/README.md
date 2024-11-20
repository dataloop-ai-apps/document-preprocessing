# PDF to Image Conversion

This service converts PDF files from Dataloop items into image files and uploads them as new image items.
It processes each page of the PDF, converts it to an image, and can also apply a modality to visualize the image in
Dataloop.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `apply_modality`: A boolean parameter that determines whether to replace the modality of the original PDF item with
  the newly created image item.

### Methods

#### `pdf_item_to_images(item: dl.Item, context: dl.Context) -> List[dl.Item]`

This method handles the conversion process:

1. Verifies that the provided item is a PDF.
2. Downloads the PDF item locally from Dataloop.
3. Converts each page of the PDF to an image (PNG format).
4. Uploads the generated images to Dataloop as new image items.
5. Optionally applies a modality to the first image item to visualize it in place of the original PDF.
6. Deletes the local temporary files after processing.

#### `convert_pdf_to_image(file_path: str) -> List`

This method converts a PDF file into images:

- Iterates over each page in the PDF and generates a corresponding PNG image.
- Saves each image in a local directory and returns the paths to the generated image files.

#### `apply_modality(item: dl.Item, ref_item: dl.Item)`

This method applies a modality to replace the PDF item with the image item for visualization:

- The first image generated from the PDF is used as the reference item for the modality.


