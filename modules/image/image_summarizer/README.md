# Image Summarizer

This app analyzes and summarizes images and returns the original item with analysis metadata. 
This is a mock implementation for testing pipeline flows.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `analysis type`: A string parameter that determines the type of image analysis (general, object_detection, scene_analysis, text_extraction, facial_recognition). Default is `general`.
- `include text extraction (OCR)`: A boolean parameter that determines whether to extract text from images using OCR. Default is `False`.
- `summary language`: A string parameter that determines the language for image summaries (en, es, fr, de, it, pt, auto). Default is `en`.
- `confidence threshold`: A number parameter that sets the minimum confidence threshold for image analysis. Default is `0.8`.
- `remote path for summaries`: The path where image summaries would be saved in the Dataloop dataset after processing.

### Methods

#### `image_summarization(self, item: dl.Item, context: dl.Context) -> dl.Item`

This method handles the image analysis and summarization:

1. Validates that the item is an image file (supports common image formats).
2. Retrieves configuration parameters from the node context.
3. Logs analysis information.
4. Adds analysis metadata to the item.
5. Returns the original item (mock implementation).

## Supported File Types

- `.jpg` / `.jpeg` (JPEG)
- `.png` (Portable Network Graphics)
- `.gif` (Graphics Interchange Format)
- `.bmp` (Bitmap)
- `.tiff` / `.tif` (Tagged Image File Format)
- `.webp` (WebP)
- `.svg` (Scalable Vector Graphics)

## Analysis Features

- **Mock Analysis**: This is a dummy implementation that passes through the original item
- **Multiple Analysis Types**: Configurable analysis modes including object detection, scene analysis, and more
- **OCR Support**: Optional text extraction from images
- **Multi-language Support**: Configurable language for image summaries
- **Confidence Filtering**: Configurable confidence threshold for analysis quality
- **Metadata Addition**: Adds analysis metadata to track processing
- **Logging**: Comprehensive logging for debugging and monitoring 