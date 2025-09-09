from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from unstructured.cleaners.core import replace_unicode_quotes, clean, clean_non_ascii_chars, \
    clean_ordered_bullets, group_broken_paragraphs, remove_punctuation
from unstructured.partition.text import partition_text
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from unstructured.documents.elements import Text
from autocorrect import Speller
from functools import partial, lru_cache
from pathlib import Path
from typing import List, Iterator, Optional, Tuple
from tqdm import tqdm
import dtlpy as dl
import tempfile
import logging
import nltk
import time
import os
import psutil
import re
from multiprocessing import cpu_count

logger = logging.getLogger('chunks-logger')


class ChunksExtractor(dl.BaseServiceRunner):

    def __init__(self):
        # Download NLTK models only once
        self._ensure_nltk_models()
        self._optimal_workers = self._calculate_optimal_workers()
        self._spell_checker_cache = {}
    
    @staticmethod
    def _ensure_nltk_models():
        """Ensure NLTK models are downloaded (cached after first download)."""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('punkt', quiet=True)
    
    @staticmethod
    def _calculate_optimal_workers() -> int:
        cpu_cores = psutil.cpu_count(logical=False) or 4
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        if memory_gb > 16:
            optimal = min(32, cpu_cores * 3)
        elif memory_gb > 8:
            optimal = min(24, cpu_cores * 2)
        elif memory_gb > 4:
            optimal = min(16, cpu_cores)
        else:
            optimal = min(8, max(4, cpu_cores // 2))
        
        logger.info(f"Calculated optimal workers for chunking: {optimal}")
        return optimal
    
    @staticmethod
    def _calculate_process_workers() -> int:
        cpu_cores = cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        process_workers = max(2, min(cpu_cores, 12))
        memory_limit = max(2, int(memory_gb // 2))
        optimal = min(process_workers, memory_limit)
        logger.info(f"Calculated process workers for chunking: {optimal}")
        return optimal
    
    @lru_cache(maxsize=2)
    def _get_spell_checker(self, lang: str = 'en') -> Speller:
        """Get cached spell checker instance."""
        return Speller(lang=lang)
    
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_cached_spell_checker(lang: str = 'en') -> Speller:
        """Get globally cached spell checker instance."""
        return Speller(lang=lang)

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

        if not item.mimetype == 'text/plain':
            raise ValueError(
                f"Item id : {item.id} is not txt file. This functions excepts txt only. "
                f"Use other extracting applications from Marketplace to convert text format to txt")

        # Extract text with memory-efficient streaming for large files
        file_size_mb = item.size / (1024 * 1024) if item.size else 0
        
        if file_size_mb > 100:  # For files larger than 100MB, use streaming
            logger.info(f"Large file detected ({file_size_mb:.1f}MB), using streaming approach")
            chunks = self._create_chunks_streaming(item, chunking_strategy, max_chunk_size, chunk_overlap)
        else:
            # For smaller files, use the existing approach
            buffer = item.download(save_locally=False)
            text = buffer.read().decode('utf-8')
            chunks = self.chunking_strategy_optimized(text=text,
                                                     strategy=chunking_strategy,
                                                     chunk_size=max_chunk_size,
                                                     chunk_overlap=chunk_overlap)

        items = self.upload_chunks(chunks=chunks,
                                   item=item,
                                   remote_path_for_chunks=remote_path_for_chunks,
                                   metadata={'system': {'document': item.name},
                                             'user': {'extracted_chunk': True,
                                                      'original_item_id': item.id}}
                                   )

        return items

    def _create_chunks_streaming(self, item: dl.Item, strategy: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Create chunks from large files using streaming to avoid memory issues.
        """
        chunks = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download file locally for streaming
            local_path = item.download(local_path=temp_dir)
            
            # Stream file in chunks to avoid loading entire file into memory
            with open(local_path, 'r', encoding='utf-8', buffering=8192) as f:
                if strategy in ['nltk-sentence', 'nltk-paragraphs']:
                    # For NLTK strategies, we need the full text
                    # Read in manageable chunks and process
                    text_buffer = ""
                    chunk_buffer_size = 10 * 1024 * 1024  # 10MB chunks
                    
                    while True:
                        chunk_data = f.read(chunk_buffer_size)
                        if not chunk_data:
                            break
                        
                        text_buffer += chunk_data
                        
                        # Process when buffer is large enough or at end of file
                        if len(text_buffer) >= chunk_buffer_size * 2 or len(chunk_data) < chunk_buffer_size:
                            buffer_chunks = self.chunking_strategy_optimized(
                                text=text_buffer,
                                strategy=strategy,
                                chunk_size=chunk_size,
                                chunk_overlap=chunk_overlap
                            )
                            chunks.extend(buffer_chunks)
                            
                            # Keep overlap for next iteration
                            if chunk_overlap > 0 and buffer_chunks:
                                text_buffer = buffer_chunks[-1][-chunk_overlap:] if len(buffer_chunks[-1]) > chunk_overlap else ""
                            else:
                                text_buffer = ""
                else:
                    # For fixed-size and recursive strategies, process the entire file
                    text = f.read()
                    chunks = self.chunking_strategy(
                        text=text,
                        strategy=strategy,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
        
        logger.info(f"Created {len(chunks)} chunks using streaming approach")
        return chunks

    @staticmethod
    def upload_chunks(chunks, item, remote_path_for_chunks, metadata):
        """
        Saves each text chunk as a separate file, uploads the files as Dataloop items, and removes local copies.

        This function takes a list of text chunks, saves each chunk to a unique text file, and uploads these files
        to the Dataloop platform in bulk. Each uploaded file is associated with the original item metadata.

        Args:
            chunks (List[str]): A list of text chunks to be saved and uploaded.
            item (dl.Item): The original Dataloop item that the chunks are derived from.
            metadata (dict): Metadata to associate with each uploaded chunk item, including any relevant system tags.
            remote_path_for_chunks (str): Remote path for the created chunks.

        Returns:
            List[dl.Item]: A list of uploaded Dataloop items, each representing a chunk of the original text file.

        Raises:
            dl.PlatformException: If no items were uploaded successfully.
        """

        chunks_paths = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for ind, chunk in enumerate(chunks):
                base_name = item.name
                chunk_filename = f"{os.path.splitext(base_name)[0]}-{ind}.txt"
                chunk_path = os.path.join(temp_dir, chunk_filename)

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
    def chunking_strategy_optimized(text: str, strategy: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        start_time = time.time()
        
        if strategy == 'fixed-size':
            chunks = []
            text_len = len(text)
            
            for i in range(0, text_len, chunk_size - chunk_overlap):
                end_pos = min(i + chunk_size, text_len)
                chunk = text[i:end_pos]
                if chunk.strip():  # Only add non-empty chunks
                    chunks.append(chunk)
                
                if end_pos >= text_len:
                    break
            
        elif strategy == 'recursive':
            # Native recursive chunking with optimized separators
            chunks = ChunksExtractor._recursive_split_optimized(text, chunk_size, chunk_overlap)
            
        elif strategy == 'nltk-sentence':
            # Optimized sentence tokenization
            try:
                chunks = nltk.sent_tokenize(text)
            except Exception:
                # Fallback to regex-based sentence splitting
                chunks = re.split(r'[.!?]+\s+', text)
                chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
            
        elif strategy == 'nltk-paragraphs':
            # Optimized paragraph tokenization
            try:
                chunks = nltk.tokenize.blankline_tokenize(text)
            except Exception:
                # Fallback to regex-based paragraph splitting
                chunks = re.split(r'\n\s*\n', text)
                chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        else:
            # All text as 1 chunk
            chunks = [text] if text.strip() else []
        
        processing_time = time.time() - start_time
        logger.debug(f"OPTIMIZED chunking ({strategy}): {len(chunks)} chunks in {processing_time:.3f}s")
        
        return chunks
    
    @staticmethod
    def _recursive_split_optimized(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Optimized recursive text splitting using native string operations.
        Much faster than langchain's RecursiveCharacterTextSplitter.
        """
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        
        # Optimized separator hierarchy
        separators = ['\n\n', '\n', '. ', '! ', '? ', '; ', ': ', ', ', ' ', '']
        
        def split_text_recursive(text_chunk: str, sep_index: int = 0) -> List[str]:
            if len(text_chunk) <= chunk_size:
                return [text_chunk] if text_chunk.strip() else []
            
            if sep_index >= len(separators):
                # Force split if no separator works
                return [text_chunk[i:i+chunk_size] for i in range(0, len(text_chunk), chunk_size - chunk_overlap)]
            
            separator = separators[sep_index]
            splits = text_chunk.split(separator) if separator else list(text_chunk)
            
            result_chunks = []
            current_chunk = ""
            
            for split in splits:
                test_chunk = current_chunk + (separator if current_chunk else "") + split
                
                if len(test_chunk) <= chunk_size:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        result_chunks.append(current_chunk)
                    
                    if len(split) > chunk_size:
                        # Recursively split large pieces
                        result_chunks.extend(split_text_recursive(split, sep_index + 1))
                        current_chunk = ""
                    else:
                        current_chunk = split
            
            if current_chunk:
                result_chunks.append(current_chunk)
            
            return result_chunks
        
        return split_text_recursive(text)

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

        ###############################################
        # Clean text by using unstructured io library #
        ################################################

        tic = time.time()
        
        # Use optimized worker count instead of hardcoded 32
        max_workers = min(self._optimal_workers, len(items), 16)  # Cap at 16 for stability
        logger.info(f"Processing {len(items)} chunks with {max_workers} workers")
        
        # Process in batches to avoid overwhelming the system
        batch_size = max(10, len(items) // max_workers) if len(items) > 50 else len(items)
        results = []
        
        with tqdm(total=len(items), desc='Processing chunks') as pbar:
            for batch_start in range(0, len(items), batch_size):
                batch_end = min(batch_start + batch_size, len(items))
                batch_items = items[batch_start:batch_end]
                
                # Process current batch
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for item in batch_items:
                        kwargs = {'pbar': pbar,
                                  'item': item,
                                  'to_correct_spelling': to_correct_spelling,
                                  "remote_path_for_clean_chunks": remote_path_for_clean_chunks
                                  }
                        future = executor.submit(self.clean_chunk, **kwargs)
                        futures.append(future)
                    
                    # Collect batch results
                    batch_results = [future.result() for future in futures]
                    results.extend(batch_results)

        logger.info('Using threads took {:.2f}[s]'.format(time.time() - tic))

        return results

    @staticmethod
    def clean_chunk(pbar: tqdm, item: dl.Item, remote_path_for_clean_chunks: str,
                    to_correct_spelling: bool = True) -> dl.Item:
        """
        Cleans a text chunk item using various text preprocessing functions and optionally applies spell-checking.

        This function downloads the text item, applies a series of cleaning functions, optionally performs spell
        correction, and saves the cleaned text as a new chunk file. It then uploads the cleaned chunk back to the
        Dataloop dataset with metadata indicating the processing status.

        Args:
            pbar (tqdm): Progress bar instance to track progress.
            item (dl.Item): The Dataloop text item representing a chunk of the original file.
            to_correct_spelling (bool, optional): Whether to apply spell-checking using autocorrect. Defaults to True.
            remote_path_for_clean_chunks (str) : Remote path for the clean chunks.

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
                    # # Remove alphanumeric bullets from the beginning of text up to three subsection levels.
                    # clean_ordered_bullets,
                    # Groups together paragraphs that are broken up with line breaks
                    group_broken_paragraphs,
                    # Removes ASCII and unicode punctuation from a string.
                    remove_punctuation
                    ]

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, item.name)
            textfile_path = item.download(local_path=file_path, save_locally=True)
            logger.info(f"Downloaded item to temporary path: {textfile_path}")

            # Extract content
            elements = partition_text(filename=textfile_path)
            text = ''
            # Clean content
            for element in elements:
                element = Text(element.text)
                element.apply(*cleaners)
                if element.text.split() != []:  # clean_ordered_bullets fails when splitting returns an empty list
                    # Remove alphanumeric bullets from the beginning of text up to three subsection levels.
                    element.text = clean_ordered_bullets(text=element.text)
                logger.debug("Applied cleaning methods")
                if to_correct_spelling is True:
                    # Use cached spell checker instance
                    spell = ChunksExtractor._get_cached_spell_checker()
                    clean_text = spell(element.text)
                    text += clean_text + ' '
                    logger.debug("Applied autocorrect spelling")
                else:
                    text += element.text + ' '

        # Save
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, f"{Path(item.name).stem}_text.txt")
            with open(temp_file_path, "w", encoding="utf-8") as temp_text_file:
                temp_text_file.write(text)

            logger.info(f"Saved chunk to temporary file at: {temp_file_path}")

            original_id = item.metadata.get('user', dict()).get('original_item_id', None)
            clean_chunk_item = item.dataset.items.upload(local_path=temp_file_path,
                                                         remote_path=remote_path_for_clean_chunks,
                                                         item_metadata={
                                                             'user': {'clean_chunk': True,
                                                                      'original_item_id': original_id,
                                                                      'original_chunk_id': item.id}})
        pbar.update()

        return clean_chunk_item
