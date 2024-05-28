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
import time
import nltk
import os

nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')
logger = logging.getLogger('text-preprocess-logger')


class PreprocessorRunner(dl.BaseServiceRunner):
    """
    This Service contains preprocessing functions for chunk text files to clean text files.
    The service allow preprocessing the text files to create a clean dataset and prepare the data for using
    embedding models.
    """

    @staticmethod
    def preprocess_text(items: [dl.Item], context: dl.Context) -> List[dl.Item]:
        """
        The main function for the preprocessing process of a Dataloop item, text file contain a chunk of the original
        text file (pdf in this case).
        :param items: a list of Dataloop items, text file
        :param context: Dataloop context to set whether to spell the text using autocorrect
        :return: A list of clean chunk items.
        """
        node = context.node
        to_spell = node.metadata['customNodeConfig']['to_spell']

        # Download path - original items
        local_path = os.path.join(os.getcwd(), 'datasets', items[0].dataset.id, 'text_files')
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
                              'to_spell': to_spell
                              }
                    future = executor.submit(PreprocessorRunner.clean_chunk, **kwargs)
                    futures.append(future)
        results = [future.result() for future in futures]

        logger.info('Using threads took {:.2f}[s]'.format(time.time() - tic))

        return results

    @staticmethod
    def clean_chunk(pbar: tqdm, item: dl.Item, local_path: str, chunk_files_folder: str,
                    to_spell: bool = True) -> dl.Item:
        """
        Clean chunk using all undistracted io cleaning functions.
        :param pbar: Progress bar.
        :param item: Dataloop item, text file.
        :param local_path: Path to item locally.
        :param chunk_files_folder: Path for saving locally the clean chunk file.
        :param to_spell: Whether to spell the text using autocorrect.
        :return: Clean chunk item
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
            if to_spell is True:
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
                                                     remote_path='/unstructured_io_text_files',
                                                     # TODO: add another cleaning library
                                                     item_metadata={
                                                         'user': {'prepossess_chunk': {'clean_chunk': True,
                                                                                       'original_item_id': original_id,
                                                                                       'original_chunk_id': item.id}}})
        pbar.update()

        # Remove local files
        os.remove(textfile_path)
        os.remove(chunkfile_path)

        return clean_chunk_item
