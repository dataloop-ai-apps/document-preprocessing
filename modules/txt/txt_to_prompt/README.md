# Text to Prompt

## Overview

This application converts text items (`.txt`) into prompt items (`PromptItem`) for use with model inference in Dataloop pipelines. It reads the content of a text file, wraps it as a user message in a `PromptItem`, and uploads the result to the dataset.

An optional system prompt can be configured to prepend instructions or context to each prompt item.

## Usage

### Pipeline Node Configuration

| Parameter | Description | Default |
| --------------------------------- | --------------------------------------------------------- | ------------------- |
| **Node Name** | Display name of the pipeline node | `Text-to-Prompt` |
| **Prompt Items Output Directory** | Remote path where prompt items are uploaded | `/prompt_items_dir` |
| **System Prompt** | Optional system-level instruction prepended to the prompt | *(empty)* |
| **Metadata Keys to Extract** | Dot-notation paths of metadata fields to extract from the source item (e.g. `user.frame_indices`, `origin_video_name`) | `[]` |
| **Add Metadata to Prompt Text** | When `true`, extracted metadata is added as text inside the prompt content. When `false`, it is stored as metadata on the prompt item. | `false` |

### Input / Output

| I/O | Type | Description |
| ------ | ------ | ------------------------ |
| Input | `Item` | A `.txt` text item |
| Output | `Item` | The uploaded prompt item |

### Metadata Handling

The node always sets `metadata.user.source_item_id` on the prompt item with the ID of the source text item.

Additional metadata can be propagated using the **Metadata Keys to Extract** configuration. The **Add Metadata to Prompt Text** boolean controls where extracted metadata ends up:

- **`false` (default)** — extracted metadata is stored on the prompt item's metadata, preserving the original nested structure. This is useful when downstream pipeline nodes need to read these fields programmatically.

- **`true`** — extracted metadata is serialized as JSON and prepended to the prompt text content. The prompt body will look like:
  ```
  Metadata:
  { ... }

  Content:
  <original text content>
  ```
  This is useful when the metadata should be visible to the model during inference.
