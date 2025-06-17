# Process Attachments

This app processes various types of attachments and returns the original item with processing metadata. 
This is a mock implementation for testing pipeline flows.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `save original`: A boolean parameter that determines whether to save the original file. Default is `True`.
- `processing mode`: A string parameter that determines the processing mode (extract, convert, analyze). Default is `extract`.
- `remote path for processed files`: The path where processed files would be saved in the Dataloop dataset after processing.

### Methods

#### `process_attachments(self, item: dl.Item, context: dl.Context) -> dl.Item`

This method handles the attachment processing:

1. Retrieves configuration parameters from the node context.
2. Logs processing information.
3. Adds processing metadata to the item.
4. Returns the original item (mock implementation).

## Supported File Types

- All file types (mock implementation)

## Processing Features

- **Mock Processing**: This is a dummy implementation that passes through the original item
- **Metadata Addition**: Adds processing metadata to track that the item was processed
- **Configurable Parameters**: Supports various processing modes and options
- **Logging**: Comprehensive logging for debugging and monitoring 