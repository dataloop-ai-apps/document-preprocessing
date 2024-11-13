# PPT Sanitization

This service sanitizes PowerPoint presentations by removing sensitive information and visual identity elements. 
It processes the slides to replace company names, personal names, locations, currency symbols, and other sensitive 
content with placeholders. Additionally, it identifies visual elements like logos and replaces them with black images. 
The cleaned PowerPoint presentation is then uploaded as a new item in Dataloop.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `element`: Specifies the type of content to sanitize in the PowerPoint presentation. Options are:
  - `text`: Sanitizes textual content.
  - `image`: Sanitizes image content, particularly logos and visual identity elements.

### Methods

#### `clean_images(shape, new_slide)`

This method processes image shapes in the slide:

1. Identifies logos or visual identity elements using GPT-based classification.
2. If a logo is detected, it replaces it with a black image.
3. Otherwise, the image is retained and added to the new slide.

#### `clean_text(shape, new_slide)`

This method processes text shapes in the slide:

1. Uses GPT-based classification to sanitize the text, replacing sensitive information such as company names, locations, currencies, and personal names.
2. Retains the formatting (font, size, color) of the original text.

#### `sanitize(item: dl.Item, element: str) -> dl.Item`

This method sanitizes the content of a PowerPoint presentation:

1. Downloads the PowerPoint presentation from Dataloop.
2. Creates a new presentation with sanitized content.
3. Iterates through all slides and processes each shape based on the specified element (`text` or `image`).
4. Uploads the sanitized presentation as a new item to Dataloop.

#### `sanitize_text(item: dl.Item) -> dl.Item`

This method sanitizes the textual content of a PowerPoint presentation by calling `sanitize` with the `text` element.

#### `sanitize_visual_identity(item: dl.Item) -> dl.Item`

This method sanitizes the visual identity elements (such as logos) in a PowerPoint presentation by calling `sanitize` with the `image` element.
