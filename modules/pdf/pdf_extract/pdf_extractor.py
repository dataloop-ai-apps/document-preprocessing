from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Tuple, Optional
import dtlpy as dl
import tempfile
import logging
import pypdf
import fitz
import os
import gc
import psutil
import mmap
from multiprocessing import cpu_count
import time

logger = logging.getLogger('pdf-to-text-logger')


class PdfExtractor(dl.BaseServiceRunner):
    
    def __init__(self):
        super().__init__()
        self._optimal_workers = self._calculate_optimal_workers()
    
    @staticmethod
    def _calculate_optimal_workers() -> int:
        cpu_cores = psutil.cpu_count(logical=False) or 4
        memory_gb = psutil.virtual_memory().total / (1024**3)
        cpu_workers = max(2, min(cpu_cores, 32))
        memory_workers = max(2, int(memory_gb // 1))
        optimal = min(cpu_workers, memory_workers)
        logger.info(f"Calculated optimal workers: {optimal}")
        return optimal
    
    @staticmethod
    def _calculate_process_workers() -> int:
        cpu_cores = cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        process_workers = max(2, min(cpu_cores // 2, 8))
        memory_limit = max(2, int(memory_gb // 4))
        optimal = min(process_workers, memory_limit)
        logger.info(f"Calculated process workers: {optimal}")
        return optimal

    def pdf_extraction(self, item: dl.Item, context: dl.Context) -> List[dl.Item]:
        """
        The extracting text from pdf item and uploading it as a text file.

        :param item: Dataloop item, pdf file
        :return: Text Dataloop item
        """
        node = context.node
        extract_images = node.metadata['customNodeConfig']['extract_images']
        remote_path_for_extractions = node.metadata['customNodeConfig']['remote_path_for_extractions']

        if not item.mimetype == 'application/pdf':
            raise ValueError(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        # Download item
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                item_local_path = item.download(local_path=temp_dir)
                
                new_items_path = self.extract_text_from_pdf_optimized(
                    pdf_path=item_local_path, 
                    max_workers=self._optimal_workers
                )
                
                if extract_images is True:
                    new_images_path = self.extract_images_from_pdf(
                        pdf_path=item_local_path,
                        max_workers=self._optimal_workers
                    )
                    new_items_path.extend(new_images_path)
                
                # Upload all items
                new_items = item.dataset.items.upload(
                    local_path=new_items_path,
                    remote_path=remote_path_for_extractions,
                    item_metadata={
                        'user': {
                            'extracted_from_pdf': True,
                            'original_item_id': item.id
                        }
                    },
                    overwrite=True
                )
                
                if new_items is None:
                    raise dl.PlatformException(f"No items was uploaded! local paths: {new_items_path}")
                elif isinstance(new_items, dl.Item):
                    all_items = [new_items]
                else:
                    all_items = [item for item in new_items]
                    
            except Exception as e:
                logger.error(f"Error processing PDF {item.id}: {str(e)}")
                raise
            finally:
                # Force garbage collection to free memory
                gc.collect()
        
        return all_items

    @staticmethod
    def extract_text_from_pdf_optimized(pdf_path: str, max_workers: int = 4) -> List[str]:
        text_files = []
        start_time = time.time()
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                try:
                    with mmap.mmap(pdf_file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                        pdf_reader = pypdf.PdfReader(mmapped_file)
                        logger.info(f"Using memory-mapped I/O")
                except (OSError, ValueError):
                    pdf_reader = pypdf.PdfReader(pdf_file)
                    logger.info(f"Using standard I/O")
                
                total_pages = len(pdf_reader.pages)
                logger.info(f"Processing {total_pages} pages with {max_workers} workers (OPTIMIZED)")
                
                # Adaptive batch sizing with more aggressive settings
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
                
                if total_pages <= 20:
                    batch_size = total_pages  # Small PDFs: process all at once
                elif available_memory_gb > 8:
                    batch_size = min(100, max(20, total_pages // 2))  # Large memory: much bigger batches
                elif available_memory_gb > 4:
                    batch_size = min(50, max(10, total_pages // 4))   # Medium memory: bigger batches
                else:
                    batch_size = min(25, max(5, total_pages // 8))    # Limited memory: moderate batches
                
                logger.info(f"Using aggressive batch size: {batch_size} (Available memory: {available_memory_gb:.1f}GB)")
                
                def process_page_optimized(page_num: int) -> Tuple[int, str, Optional[str]]:
                    """Optimized page processing with immediate cleanup."""
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        
                        # Immediate cleanup to free memory
                        del page
                        
                        return page_num, page_text, None
                    except Exception as e:
                        return page_num, "", str(e)
                
                # Process pages in optimized batches with ProcessPoolExecutor for CPU-bound work
                processed_pages = 0
                
                # Use ProcessPoolExecutor for true parallelism (not limited by GIL)
                with ProcessPoolExecutor(max_workers=min(max_workers, 8)) as process_executor:
                    for batch_start in range(0, total_pages, batch_size):
                        batch_end = min(batch_start + batch_size, total_pages)
                        batch_pages = list(range(batch_start, batch_end))
                        
                        # Submit batch to process pool
                        futures = {process_executor.submit(process_page_optimized, page_num): page_num 
                                 for page_num in batch_pages}
                        
                        # Collect results with timeout handling
                        batch_results = []
                        for future in as_completed(futures, timeout=300):  # 5 minute timeout per page
                            try:
                                page_num, page_text, error = future.result()
                                
                                if error:
                                    logger.warning(f"Skipping page {page_num + 1} due to error: {error}")
                                    continue
                                    
                                batch_results.append((page_num, page_text))
                            except Exception as e:
                                logger.error(f"Failed to process page: {str(e)}")
                        
                        # Sort results by page number to maintain order
                        batch_results.sort(key=lambda x: x[0])
                        
                        # Batch write operations for better I/O performance
                        batch_files = []
                        for page_num, page_text in batch_results:
                            new_item_path = f'{os.path.splitext(pdf_path)[0]}_page_{page_num + 1}.txt'
                            batch_files.append((new_item_path, page_text))
                        
                        # Write all files in batch
                        for file_path, content in batch_files:
                            try:
                                with open(file_path, 'w', encoding='utf-8', buffering=8192) as f:
                                    f.write(content)
                                text_files.append(file_path)
                                processed_pages += 1
                            except IOError as e:
                                logger.error(f"Failed to write {file_path}: {str(e)}")
                        
                        # Log progress and cleanup
                        logger.info(f"Processed batch {batch_start//batch_size + 1}: {processed_pages}/{total_pages} pages")
                        gc.collect()
                
                processing_time = time.time() - start_time
                logger.info(f"OPTIMIZED: Successfully extracted text from {len(text_files)} pages in {processing_time:.2f}s")
                logger.info(f"OPTIMIZED: Throughput: {len(text_files)/processing_time:.2f} pages/second")
                
        except Exception as e:
            logger.error(f"Failed to process PDF with optimization: {str(e)}")
            # Fallback to original method
            logger.info("Falling back to original extraction method")
            return PdfExtractor.extract_text_from_pdf(pdf_path, max_workers)
        
        return text_files

    @staticmethod
    def extract_text_from_pdf(pdf_path: str, max_workers: int = 4) -> List[str]:
        """
        Extracts text from a PDF file and saves each page as a separate .txt file.
        Optimized for performance and memory efficiency with adaptive batching.

        Args:
            pdf_path (str): The path to the PDF file to be processed.
            max_workers (int): Maximum number of threads for concurrent processing.

        Returns:
            list: A list of paths to the generated .txt files, each corresponding to a page in the PDF.
        """
        text_files = []
        
        # Use context manager to ensure file is closed properly
        with open(pdf_path, 'rb') as pdf_file:
            try:
                pdf_reader = pypdf.PdfReader(pdf_file)
                logger.info(f"PDF metadata: {pdf_reader.metadata}")
                
                total_pages = len(pdf_reader.pages)
                logger.info(f"Processing {total_pages} pages from PDF with {max_workers} workers")
                
                # Adaptive batch sizing based on total pages and available memory
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
                
                if total_pages <= 50:
                    batch_size = total_pages  # Small PDFs: process all at once
                elif available_memory_gb > 4:
                    batch_size = min(50, max(10, total_pages // 4))  # Large memory: bigger batches
                else:
                    batch_size = min(20, max(5, total_pages // 8))   # Limited memory: smaller batches
                
                logger.info(f"Using adaptive batch size: {batch_size} (Available memory: {available_memory_gb:.1f}GB)")
                
                def process_page(page_num: int) -> Tuple[int, str, str]:
                    """Process a single page and return its content."""
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        
                        # Free page object memory
                        del page
                        
                        return page_num, page_text, None
                    except Exception as e:
                        logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                        return page_num, "", str(e)
                
                # Process pages in optimized batches
                processed_pages = 0
                
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    batch_pages = list(range(batch_start, batch_end))
                    
                    # Process current batch concurrently
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit batch processing tasks
                        futures = {executor.submit(process_page, page_num): page_num 
                                 for page_num in batch_pages}
                        
                        # Collect results as they complete
                        batch_results = []
                        for future in as_completed(futures):
                            page_num, page_text, error = future.result()
                            
                            if error:
                                logger.warning(f"Skipping page {page_num + 1} due to error: {error}")
                                continue
                                
                            batch_results.append((page_num, page_text))
                        
                        # Sort results by page number to maintain order
                        batch_results.sort(key=lambda x: x[0])
                        
                        # Write all batch results to files
                        for page_num, page_text in batch_results:
                            new_item_path = f'{os.path.splitext(pdf_path)[0]}_page_{page_num + 1}.txt'
                            try:
                                with open(new_item_path, 'w', encoding='utf-8') as f:
                                    f.write(page_text)
                                text_files.append(new_item_path)
                                processed_pages += 1
                            except IOError as e:
                                logger.error(f"Failed to write page {page_num + 1}: {str(e)}")
                    
                    # Log progress and cleanup after each batch
                    logger.info(f"Processed batch {batch_start//batch_size + 1}: {processed_pages}/{total_pages} pages")
                    gc.collect()
                
                logger.info(f"Successfully extracted text from {len(text_files)} pages")
                
            except Exception as e:
                logger.error(f"Failed to process PDF: {str(e)}")
                raise
        
        return text_files

    @staticmethod
    def extract_images_from_pdf(pdf_path: str, max_workers: int = 4) -> List[str]:
        """
        Extracts images from a PDF file and saves them as separate image files.
        Optimized for performance and memory efficiency.

        Args:
            pdf_path (str): The path to the PDF file to extract images from.
            max_workers (int): Maximum number of threads for concurrent processing.

        Returns:
            list: A list of paths to the saved image files extracted from the PDF.
        """
        images_paths = []
        
        # Use context manager to ensure PDF is closed properly
        with fitz.open(pdf_path) as pdf_file:
            try:
                total_pages = len(pdf_file)
                logger.info(f"Extracting images from {total_pages} pages")
                
                def process_page_images(page_index: int) -> List[str]:
                    """Process images from a single page."""
                    page_images = []
                    
                    try:
                        # Load page with limited memory usage
                        page = pdf_file.load_page(page_index)
                        image_list = page.get_images(full=True)
                        
                        if image_list:
                            logger.info(f"Found {len(image_list)} images on page {page_index + 1}")
                        
                        for image_index, img in enumerate(image_list, start=1):
                            try:
                                # Get the cross-reference number of the image
                                xref = img[0]
                                
                                # Extract image with error handling
                                base_image = pdf_file.extract_image(xref)
                                if not base_image:
                                    logger.warning(f"Could not extract image {image_index} from page {page_index + 1}")
                                    continue
                                
                                image_bytes = base_image.get("image")
                                image_ext = base_image.get("ext", "png")
                                
                                if not image_bytes:
                                    logger.warning(f"Empty image data for image {image_index} on page {page_index + 1}")
                                    continue
                                
                                # Save the image
                                image_name = f'{os.path.splitext(pdf_path)[0]}_page_{page_index + 1}_img_{image_index}.{image_ext}'
                                
                                with open(image_name, "wb") as image_file:
                                    image_file.write(image_bytes)
                                
                                page_images.append(image_name)
                                logger.debug(f"Saved image: {image_name}")
                                
                                # Free memory immediately
                                del image_bytes
                                del base_image
                                
                            except Exception as e:
                                logger.error(f"Failed to extract image {image_index} from page {page_index + 1}: {str(e)}")
                        
                        # Clean up page object
                        del page
                        gc.collect()
                        
                    except Exception as e:
                        logger.error(f"Failed to process page {page_index + 1} for images: {str(e)}")
                    
                    return page_images
                
                # Process pages concurrently
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all page processing tasks
                    futures = {executor.submit(process_page_images, i): i 
                              for i in range(total_pages)}
                    
                    # Collect results as they complete
                    for future in as_completed(futures):
                        page_index = futures[future]
                        try:
                            page_images = future.result()
                            images_paths.extend(page_images)
                            
                            if (page_index + 1) % 10 == 0:
                                logger.info(f"Processed images from {page_index + 1}/{total_pages} pages")
                                
                        except Exception as e:
                            logger.error(f"Failed to get results for page {page_index + 1}: {str(e)}")
                
                logger.info(f"Successfully extracted {len(images_paths)} images")
                
            except Exception as e:
                logger.error(f"Failed to extract images from PDF: {str(e)}")
                raise
            finally:
                # Force garbage collection
                gc.collect()
        
        return images_paths