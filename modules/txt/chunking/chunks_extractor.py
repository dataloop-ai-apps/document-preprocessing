from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from unstructured.cleaners.core import replace_unicode_quotes, clean, clean_non_ascii_chars, \
    clean_ordered_bullets, group_broken_paragraphs, remove_punctuation
from unstructured.partition.text import partition_text
from concurrent.futures import ThreadPoolExecutor
from unstructured.documents.elements import Text
from autocorrect import Speller
from functools import partial
from typing import List
from tqdm import tqdm
import dtlpy as dl
import logging
import shutil
import nltk
import time
import os

logger = logging.getLogger('chunks-logger')


class ChunksExtractor(dl.BaseServiceRunner):

    def __init__(self):
        nltk.download('averaged_perceptron_tagger')
        nltk.download('punkt')

    def create_chunks(self, item: dl.Item, context: dl.Context) -> List[dl.Item]:
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

        items = self.upload_chunks(local_path=local_path,
                                   chunks=chunks,
                                   item_local_path=item_local_path,
                                   item=item,
                                   remote_path_for_chunks=remote_path_for_chunks,
                                   metadata={'system': {'document': item.name},
                                             'user': {'extracted_chunk': True,
                                                      'original_item_id': item.id}}
                                   )

        shutil.rmtree(local_path, ignore_errors=True)

        return items

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

    def clean_multiple_chunks(self, items: [dl.Item], context: dl.Context) -> List[dl.Item]:
        """
        Preprocesses multiple text chunk items in a Dataloop dataset by cleaning and optionally spell-checking each chunk.

        This function downloads each text item in the provided list, processes the text based on the context settings,
        and saves the cleaned text to new chunk files. Optionally, it performs spell correction if enabled in the context.

        Args:
            item dl.Item]: A Dataloop text item.
            context (dl.Context): Context configuration specifying whether to apply spell-checking.

        Returns:
            List[dl.Item]: A list of cleaned text chunk items.
        """

        node = context.node
        to_correct_spelling = node.metadata['customNodeConfig']['to_correct_spelling']
        remote_path_for_clean_chunks = node.metadata['customNodeConfig']['remote_path_for_clean_chunks']
        # local test
        # to_correct_spelling = False

        # Download path - original items
        local_path = os.path.join(os.getcwd(), 'datasets', items[0].dataset.id, 'items')
        os.makedirs(local_path, exist_ok=True)

        # Saving path - converted text items
        chunk_files_folder = os.path.join(local_path, 'chunk_files')
        os.makedirs(chunk_files_folder, exist_ok=True)

        ###############################################
        # Clean text by using unstructured io library #
        ################################################

        tic = time.time()
        futures = list()
        with (ThreadPoolExecutor(max_workers=32) as executor):
            with tqdm(total=len(items), desc='Processing') as pbar:
                for item in items:
                    kwargs = {'pbar': pbar,
                              'item': item,
                              'local_path': local_path,
                              'chunk_files_folder': chunk_files_folder,
                              'to_correct_spelling': to_correct_spelling,
                              "remote_path_for_clean_chunks": remote_path_for_clean_chunks
                              }
                    future = executor.submit(self.clean_chunk, **kwargs)
                    futures.append(future)
        results = [future.result() for future in futures]

        logger.info('Using threads took {:.2f}[s]'.format(time.time() - tic))

        shutil.rmtree(local_path, ignore_errors=True)

        return results

    @staticmethod
    def clean_chunk(pbar: tqdm, item: dl.Item, local_path: str, chunk_files_folder: str,
                    remote_path_for_clean_chunks: str, to_correct_spelling: bool = True) -> dl.Item:
        """
        Cleans a text chunk item using various text preprocessing functions and optionally applies spell-checking.

        This function downloads the text item, applies a series of cleaning functions, optionally performs spell
        correction, and saves the cleaned text as a new chunk file. It then uploads the cleaned chunk back to the
        Dataloop dataset with metadata indicating the processing status.

        Args:
            pbar (tqdm): Progress bar instance to track progress.
            item (dl.Item): The Dataloop text item representing a chunk of the original file.
            local_path (str): Local path where the item is downloaded.
            chunk_files_folder (str): Path for saving the locally cleaned chunk file.
            to_correct_spelling (bool, optional): Whether to apply spell-checking using autocorrect. Defaults to True.
            remote_path_for_clean_chunks (str)

        Returns:
            dl.Item: The cleaned text chunk item uploaded back to the Dataloop dataset.
        """
        # Create a partial function for cleaner1 with the specified parameters for clean function of unstructured-io
        cleaner1_partial = partial(clean,
                                   extra_whitespace=True,  # Removes extra whitespace from a section of text
                                   dashes=True,  # Removes dashes from a section of text.
                                   bullets=True,  # Removes bullets from the beginning of text.
                                   trailing_punctuation=True,  # Removes trailing punctuation from a section of text.
                                   lowercase=True)  # Lowercase the output

        cleaners = [cleaner1_partial,
                    # Replaces unicode quote characters in strings
                    replace_unicode_quotes,
                    # Removes non-ascii characters from a string.
                    clean_non_ascii_chars,
                    # Remove alphanumeric bullets from the beginning of text up to three subsection levels.
                    clean_ordered_bullets,
                    # Groups together paragraphs that are broken up with line breaks
                    group_broken_paragraphs,
                    # Removes ASCII and unicode punctuation from a string.
                    remove_punctuation
                    ]

        item_local_path = os.path.join(local_path, os.path.dirname(item.filename[1:]))
        textfile_path = item.download(local_path=item_local_path)

        # Extract content
        elements = partition_text(filename=textfile_path)
        text = ''
        # Clean content
        for element in elements:
            element = Text(element.text)
            element.apply(*cleaners)
            logger.info("Applied cleaning methods")
            if to_correct_spelling is True:
                spell = Speller(lang='en')
                clean_text = spell(element.text)
                text += clean_text + ''
                logger.info("Applied autocorrect spelling")
            else:
                text += element.text + ' '

        # Save
        # each chunk as separated text file
        chunkfile_path = os.path.join(chunk_files_folder,
                                      os.path.splitext(item.name)[0] + '-clean' + '.txt')

        with open(chunkfile_path, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(text)
        logger.info(f"Saved chunk to text file in: {chunkfile_path}")

        original_id = item.metadata.get('user', dict()).get('original_item_id', None)
        clean_chunk_item = item.dataset.items.upload(local_path=chunkfile_path,
                                                     remote_path=remote_path_for_clean_chunks,
                                                     item_metadata={
                                                         'user': {'prepossess_chunk': {'clean_chunk': True,
                                                                                       'original_item_id': original_id,
                                                                                       'original_chunk_id': item.id}}})
        pbar.update()

        return clean_chunk_item
