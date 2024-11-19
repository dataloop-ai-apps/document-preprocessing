from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from pathlib import Path
from typing import List
import dtlpy as dl
import logging
import shutil
import nltk
import os

logger = logging.getLogger('text-preprocess-logger')
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')


class ChunksExtractor(dl.BaseServiceRunner):

    def create_chunks(self, item: dl.Item, context: dl.Context) -> dl.Item:
        """
        Creates and uploads text chunks from a txt file item based on specified chunking parameters.

        This function extracts text from a .txt file, splits it into smaller chunks using a chosen strategy,
        and uploads each chunk as a new text item. Chunking settings include the method, maximum size, and
        overlap between chunks.

        Args:
            item (dl.Item): The Dataloop item containing the original text file to be chunked.
            context (dl.Context): The Dataloop context providing parameters for chunking, including:
                - `chunking_strategy` (str): The strategy for splitting text.
                - `max_chunk_size` (int): The maximum number of characters per chunk.
                - `chunk_overlap` (int): The number of overlapping characters between consecutive chunks.

        Returns:
            List[dl.Item]: A list of Dataloop items, each representing a chunk of the original text file.
        """
        node = context.node
        chunking_strategy = node.metadata['customNodeConfig']['chunking_strategy']
        max_chunk_size = node.metadata['customNodeConfig']['max_chunk_size']
        chunk_overlap = node.metadata['customNodeConfig']['chunk_overlap']
        remote_path_for_chunks = node.metadata['customNodeConfig']['remote_path_for_chunks']
        # local test
        # chunking_strategy = 'recursive'
        # max_chunk_size = 300
        # chunk_overlap = 20
        # remote_path_for_chunks = '/chunk_files'

        if not item.mimetype == 'text/plain':
            raise ValueError(
                f"Item id : {item.id} is not txt file. This functions excepts txt only. "
                f"Use other extracting applications from Marketplace to convert text format to txt")

        # Download path - original items
        local_path = os.path.join(os.getcwd(), 'datasets', item.dataset.id, os.path.dirname(item.filename[1:]))
        os.makedirs(local_path, exist_ok=True)
        item_local_path = item.download(local_path=local_path)

        # Extract text
        buffer = item.download(save_locally=False)
        text = buffer.read().decode('utf-8')

        chunks = self.chunking_strategy(text=text,
                                        strategy=chunking_strategy,
                                        chunk_size=max_chunk_size,
                                        chunk_overlap=chunk_overlap)

        chunks_items = self.upload_chunks(local_path=local_path,
                                          chunks=chunks,
                                          item_local_path=item_local_path,
                                          item=item,
                                          remote_path_for_chunks=remote_path_for_chunks,
                                          metadata={'system': {'document': item.name},
                                                    'user': {'extracted_chunk': True,
                                                             'original_item_id': item.id}}
                                          )

        shutil.rmtree(local_path)

        return item

    @staticmethod
    def upload_chunks(local_path, chunks, item_local_path, item, remote_path_for_chunks, metadata):
        """
        Saves each text chunk as a separate file, uploads the files as Dataloop items, and removes local copies.

        This function takes a list of text chunks, saves each chunk to a unique text file, and uploads these files
        to the Dataloop platform in bulk. Each uploaded file is associated with the original item metadata.

        Args:
            local_path (str): The directory path where chunk files will be stored locally before upload.
            chunks (List[str]): A list of text chunks to be saved and uploaded.
            item_local_path (str): The local path of the original item, used to generate chunk file names.
            item (dl.Item): The original Dataloop item that the chunks are derived from.
            metadata (dict): Metadata to associate with each uploaded chunk item, including any relevant system tags.
            remote_path_for_chunks (str): Remote path for the created chunks.

        Returns:
            List[dl.Item]: A list of uploaded Dataloop items, each representing a chunk of the original text file.

        Raises:
            dl.PlatformException: If no items were uploaded successfully.
        """

        chunks_files_folder = os.path.join(local_path, 'chunks_files')
        os.makedirs(chunks_files_folder, exist_ok=True)

        chunks_paths = []

        for ind, chunk in enumerate(chunks):
            chunk_path = os.path.basename(item_local_path)
            chunk_path = os.path.join(chunks_files_folder,
                                      os.path.splitext(chunk_path)[0] + '-' + str(ind) + '.txt')

            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(chunk)
            chunks_paths.append(chunk_path)

        # Uploading all chunk items - bulk
        chunks_items = item.dataset.items.upload(local_path=chunks_paths,
                                                 remote_path=remote_path_for_chunks,
                                                 item_metadata=metadata
                                                 )

        # raise if none
        if chunks_items is None:
            raise dl.PlatformException(f"No items was uploaded! local paths: {chunks_paths}")

        elif isinstance(chunks_items, dl.Item):
            chunks_items = [chunks_items]

        else:
            chunks_items = [item for item in chunks_items]

        # Remove local files:
        for file_path in chunks_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                logger.warning(f"{file_path} does not exist, cannot be removed")

        return chunks_items

    @staticmethod
    def chunking_strategy(text: str, strategy: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Splits text into chunks based on the specified strategy and parameters.

        This function chunks text using a chosen method, allowing control over the size and overlap of each chunk.
        Available strategies include fixed-size chunks, recursive splitting, and tokenization by sentence or paragraph.

        Args:
            text (str): The full text string to be split into chunks.
            strategy (str): The chunking method to use. Options are:
                - 'fixed-size': Chunks text to a fixed size.
                - 'recursive': Recursively splits text by characters for best fit.
                - 'nltk-sentence': Uses NLTK to split by sentences.
                - 'nltk-paragraphs': Uses NLTK to split by paragraphs.
                - Any other value will return the text as a single chunk.
            chunk_size (int): Maximum size of each chunk in characters.
            chunk_overlap (int): Maximum overlap in characters between consecutive chunks.

        Returns:
            List[str]: A list of text chunks as strings.
        """

        # Chunking by a fixed size input
        if strategy == 'fixed-size':
            text_splitter = CharacterTextSplitter(
                separator="",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            chunks = text_splitter.create_documents([text])
            chunks = [chunk.page_content for chunk in chunks]

        # Split by a list of characters: ["\n\n", "\n", " ", ""] in order, until the chunks are small enough.
        elif strategy == 'recursive':
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.create_documents([text])
            chunks = [chunk.page_content for chunk in chunks]

        # Each sentence as a chunk
        elif strategy == 'nltk-sentence':
            chunks = nltk.sent_tokenize(text)

        # Each paragraph as a chunk
        elif strategy == 'nltk-paragraphs':
            chunks = nltk.tokenize.blankline_tokenize(text)
        else:
            # All text as 1 chunk
            chunks = [text]

        return chunks
