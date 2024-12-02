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

