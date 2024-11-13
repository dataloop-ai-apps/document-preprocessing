# Chunks Cleaner and Extractor Apps

This repository contains two apps designed to preprocess and manage text data in Dataloop.

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


