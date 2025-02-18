# Dataloop Documents Preprocessing Applications 📄✨

Welcome to the Documents Preprocessing Applications repository for the [Dataloop platform](https://dataloop.ai/)! 🎉 Here, you'll find a suite of powerful tools designed to transform and manage your document files with ease. Whether you're extracting content, chunking text, or sanitizing presentations, our applications are here to streamline your workflow and enhance your data processing capabilities. Explore more in the [Dataloop Marketplace](https://dataloop.ai/platform/marketplace/) to find additional resources and tools. Let's dive in and explore the magic of document preprocessing! 🚀

## Features 🌟

- **Content Extraction**: Effortlessly extract text from various file formats.
- **Text Chunking**: Break down text into manageable chunks with customizable settings.

# Installations 🛠️

All apps can be found in the `Marketplace` under the `Applications` tab. Get started today and unlock the full potential of your document data! 📈

<details>
<summary>Doc Extract Documentation</summary>

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



</details>

<details>
<summary>Pdf Extract Documentation</summary>

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


</details>

<details>
<summary>Pdf To Image Documentation</summary>

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



</details>

<details>
<summary>Ppt Sanitization Documentation</summary>

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

</details>

<details>
<summary>Chunking Documentation</summary>

# Chunks Cleaner and Extractor Apps

This service contains two apps designed to preprocess and manage text data in Dataloop.

## Chunks Cleaner

The **Chunks Cleaner** app cleans text chunks by removing unnecessary elements such as extra spaces, non-ASCII characters, punctuation, and more. Optionally, it can correct spelling errors using the `autocorrect` library.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `to_correct_spelling`: A boolean parameter that determines whether to use autocorrect library for correct spelling.

### Usage
1. Download text chunks from Dataloop.
2. Clean the chunks by removing unwanted text elements.
3. Optionally, apply spell-checking.
4. Upload the cleaned chunks back to Dataloop.

# Chunks Extractor

The **Chunks Extractor** app splits a `.txt` file into smaller chunks based on defined parameters. It supports various chunking strategies such as fixed-size chunks or sentence-based chunking using NLTK.


## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `chunking_strategy`: Defines the strategy for chunking the text. This can be set to different methods like fixed-size chunks or sentence-based chunking using NLTK.
- `max_chunk_size`: The maximum size (in characters) allowed for each chunk.
- `chunk_overlap`: The number of overlapping characters between consecutive chunks.
- `remote_path_for_chunks`: Specifies the remote path where the generated chunks will be stored.


## Usage

1. Download a `.txt` file from Dataloop.
2. Split the file into smaller chunks.
3. Upload the chunks back to Dataloop.

## Acknowledgments 
This application makes use of the following open-source projects: 
1. [Unstructured IO](https://github.com/Unstructured-IO/unstructured) Copyright 2022 Unstructured Technologies, Inc
-->Licensed under the Apache License 2.0. You can find a copy of the license [here](https://github.com/Unstructured-IO/unstructured/blob/main/LICENSE).
2. [LangChain](https://github.com/langchain-ai/langchain)  Copyright (c) LangChain, Inc.
--> Licensed under the MIT License. You can find a copy of the license [here](https://github.com/langchain-ai/langchain/blob/main/LICENSE). 

We greatly appreciate the efforts of the open-source community!


</details>

<details>
<summary>Contextual Chunks Documentation</summary>

# Contextual Chunks Generator Apps

This app handles the creation of contextual chunks of text items.
It generates prompts from a chunk item, to send to a generate model and processes the responses from a model as the
chunk's context to improve search retrieval of chunks within a RAG process. The service is built using Dataloop's sdk and offers
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


</details>

## Dataloop Manifest (DPK) Explanation 📜

This section provides an explanation of the [Word to Txt manifest](modules/doc/doc_extract/dataloop.json), which can be used as an example for a *pipeline node* application.

### Dataloop Applications
Dataloop Applications are extensions that integrate seamlessly into the Dataloop ecosystem, providing custom panels, SDK features, and components to enhance your workflow. For more information, visit the [Dataloop Applications Introduction](https://developers.dataloop.ai/tutorials/applications/introduction/chapter).

### DPK (Dataloop Package Kit)
The DPK is a comprehensive package that includes everything needed for your application to function within the Dataloop platform. It contains modules, panels, source code, tests, and the `dataloop.json` manifest, which acts as the application's blueprint.

The Dataloop Manifest (DPK) provides metadata and configuration details for deploying and managing applications on the Dataloop platform. Here's an explanation of the key components in the manifest:

- **Name**: The identifier for the application package.
- **Display Name**: A user-friendly name for the application.
- **Version**: The version of the application package.
- **Scope**: Defines the visibility of the application (e.g., public or private).
- **Description**: A brief description of the application and its purpose.
- **Provider**: The entity or framework providing the application.
- **Deployed By**: The organization or platform deploying the application.
- **License**: The licensing terms under which the application is distributed.
- **Category**: The category or type of application (e.g., Application, Dataset).
- **Application Type**: The type of application (e.g., Pipeline Node).
- **Media Type**: The type of media the application is designed to process (e.g., Text).

### Codebase
- **Type**: The type of code repository (e.g., git).
- **Git Tag**: The specific tag or commit in the repository that corresponds to this version of the application.
- **Git URL**: The URL of the git repository containing the application's code.

All codebase information can be removed if you are publishing local code.

### Components
#### Compute Configurations
Defines the computational resources and settings required to run the application, including pod type, concurrency, and autoscaling settings. Here is an example of one configuration, but more than one can be defined:

- **Name**: doc-to-txt-v2
  - **Pod Type**: The type of pod used for deployment (e.g., regular-xs, gpu-t4).
  - **Concurrency**: The number of concurrent executions allowed.
  - **Runner Image**: The Docker image used to run the application.
  - **Autoscaler Type**: The type of autoscaler used (e.g., rabbitmq).
  - **Min Replicas**: The minimum number of pod replicas.
  - **Max Replicas**: The maximum number of pod replicas.
  - **Queue Length**: The length of the queue for processing tasks.

#### Modules
- **Name**: doc_to_txt_v2
  - **Entry Point**: The main script or module to execute.
  - **Class Name**: The class within the entry point that implements the application logic.
  - **Compute Config**: The compute configuration associated with this module.
  - **Description**: A description of the module's functionality.

#### Pipeline Nodes
- **Name**: doc_to_txt
  - **Display Name**: Word to Txt
  - **Description**: Converting Word to Txt items
  - **Scope**: project
  - **Categories**: text-utils
  - **Configuration**:
    This section defines the inputs to the node. The 'Node Name' is always required for identification, while other fields are case-specific and can be edited as needed. In this example, there are two additional fields:
    - **Node Name**: The name of the node, used for identification.
    - **Remote Path for Extractions**: The path where extracted files will be stored.
    - **Extract Tables**: A boolean indicating whether to extract tables from documents.

## Contributions 🤝

Help us improve! We welcome any contributions and suggestions to this repository.
Feel free to open an issue for bug reports or feature requests.
