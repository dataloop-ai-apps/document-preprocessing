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

logger = logging.getLogger('text-preprocess-logger')
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')


class ChunksCleaner(dl.BaseServiceRunner):

    def clean_multiple_chunks(self, item: dl.Item, context: dl.Context) -> dl.Item:
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
        # local test
        # to_correct_spelling = False

        # Filter all chunks extracted from item
        filters = dl.Filters(field='metadata.user.extracted_chunk', values=True)
        filters.add(field='metadata.user.original_item_id', values=item.id)
        items = item.dataset.items.list(filters=filters).items

        # Download path - original items
        local_path = os.path.join(os.getcwd(), 'datasets', item.dataset.id, 'items')
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
                              'to_correct_spelling': to_correct_spelling
                              }
                    future = executor.submit(self.clean_chunk, **kwargs)
                    futures.append(future)
        results = [future.result() for future in futures]

        logger.info('Using threads took {:.2f}[s]'.format(time.time() - tic))

        shutil.rmtree(local_path)

        return item

    @staticmethod
    def clean_chunk(pbar: tqdm, item: dl.Item, local_path: str, chunk_files_folder: str,
                    to_correct_spelling: bool = True) -> dl.Item:
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
                                                     remote_path='/clean_chunks_files',
                                                     item_metadata={
                                                         'user': {'prepossess_chunk': {'clean_chunk': True,
                                                                                       'original_item_id': original_id,
                                                                                       'original_chunk_id': item.id}}})
        pbar.update()

        return clean_chunk_item
