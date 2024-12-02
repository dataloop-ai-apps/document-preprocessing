# Contextual Chunks Generator Apps

This service handles the createin of contextual chunks of text items.
It generates prompts from a chunk item, to send to a generate model and processes the responses from a model as the
chunk's context
to improve search retrieval of chunks within a RAG process. The service is built using Dataloop's sdk and offers
functionalities for creating and uploading contextual chunks and their responses.

## Features

### 1. `Chunk_to_prompt`

This method creates a prompt item from a text chunk item.

- **Parameters**:
    - `item`: A Dataloop item representing a chunk of text.
    - `context`: The Dataloop context providing parameters for chunking, including:
        - `remote_path` (str): The remote path for uploading the prompt chunk.

### 2. `contextual_prompt`:

This method generates a prompt item containing the original document and chunk text.

- **Parameters**:
    - `original_text`: The original document text.
    - `chunk_text`: The chunk text that needs to be contextualized.
    - `prompt_item_name`: The name of the prompt item.

### 3. `add_response_to_chunk`:

This method adds the model's response to the chunk item, either by overwriting the chunk or creating a new chunk.
The model's response considered as the context of the chunk.

- **Parameters**:
    - `item`: The prompt item to which the response will be added.
    - `model`: The model that generated the response (the context).
    - `context`: The Dataloop context with configuration parameters, such as:
        - `remote_path` (str): The remote path for uploading the updated chunk.
        - `overwrite_chunk` (bool): Whether to overwrite the original chunk or create a new one.

## Key Concepts

### Contextual Prompt Creation

The core function of this service is to contextualize a chunk of text within a larger document. This is achieved by
combining the chunk with its corresponding original document and framing it within a structured prompt. The prompt asks
the model to provide a succinct context for the chunk, enhancing its relevance during search retrieval.

