from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import dtlpy as dl
import tempfile
import logging
import pypdf
import fitz
import os
import gc

logger = logging.getLogger('pdf-to-text-logger')


class PdfExtractor(dl.BaseServiceRunner):

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
                
                # Extract text from PDF with optimized memory management
                new_items_path = self.extract_text_from_pdf(pdf_path=item_local_path)
                
                if extract_images is True:
                    # Extract images with optimized memory management
                    new_images_path = self.extract_images_from_pdf(pdf_path=item_local_path)
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
    def extract_text_from_pdf(pdf_path: str, max_workers: int = 4) -> List[str]:
        """
        Extracts text from a PDF file and saves each page as a separate .txt file.
        Optimized for performance and memory efficiency.

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
                logger.info(f"Processing {total_pages} pages from PDF")
                
                # Process pages in batches to optimize memory usage
                batch_size = min(10, total_pages)  # Process up to 10 pages at a time
                
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
                
                # Process pages concurrently with thread pool
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all page processing tasks
                    futures = []
                    for page_num in range(total_pages):
                        future = executor.submit(process_page, page_num)
                        futures.append(future)
                        
                        # Process in batches to control memory
                        if len(futures) >= batch_size or page_num == total_pages - 1:
                            # Wait for batch to complete
                            for future in as_completed(futures):
                                page_num, page_text, error = future.result()
                                
                                if error:
                                    logger.warning(f"Skipping page {page_num + 1} due to error: {error}")
                                    continue
                                
                                # Write text to file
                                new_item_path = f'{os.path.splitext(pdf_path)[0]}_page_{page_num + 1}.txt'
                                try:
                                    with open(new_item_path, 'w', encoding='utf-8') as f:
                                        f.write(page_text)
                                    text_files.append(new_item_path)
                                    
                                    if (page_num + 1) % 10 == 0:
                                        logger.info(f"Processed {page_num + 1}/{total_pages} pages")
                                except IOError as e:
                                    logger.error(f"Failed to write page {page_num + 1}: {str(e)}")
                            
                            # Clear futures list for next batch
                            futures.clear()
                            
                            # Force garbage collection after each batch
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