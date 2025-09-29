from pathlib import Path
from typing import List, Iterable
import dtlpy as dl
import tempfile
import logging
import subprocess
import time
import tqdm
import fitz
import os

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

        logger.info(
            f"Starting PDF extraction | item_id={item.id} name={item.name} mimetype={item.mimetype} dir={item.dir}"
        )
        if not item.mimetype == 'application/pdf':
            logger.error(
                f"Item is not a PDF | item_id={item.id} mimetype={item.mimetype}"
            )
            raise ValueError(
                f"Item id : {item.id} is not a PDF file! This functions excepts pdf only"
            )

        # Download item
        with tempfile.TemporaryDirectory() as temp_dir:
            item_local_path = item.download(local_path=temp_dir)
            logger.info(f"Downloaded item | item_id={item.id} local_path={item_local_path}")

            try:
                new_items_path = self.extract_text_from_pdf(pdf_path=item_local_path)
                logger.info(
                    f"Extracted text | item_id={item.id} text_file={new_items_path}"
                )
            except Exception:
                logger.exception(f"Failed extracting text | item_id={item.id} path={item_local_path}")
                raise

            if extract_images is True:
                try:
                    new_images_path = self.extract_images_from_pdf(pdf_path=item_local_path)
                    new_items_path.extend(new_images_path)
                    logger.info(
                        f"Extracted images | item_id={item.id} images_saved={len(new_images_path)}"
                    )
                except Exception:
                    logger.exception(f"Failed extracting images | item_id={item.id} path={item_local_path}")
                    raise

            name, ext = os.path.splitext(item.name)
            remote_name = f"{name}.txt"
            remote_path = os.path.join(remote_path_for_extractions, item.dir.lstrip('/')).replace('\\', '/')
            logger.info(
                f"Uploading extracted files | item_id={item.id} count={len(new_items_path)} remote_path={remote_path}"
            )
            new_items = item.dataset.items.upload(
                local_path=new_items_path,
                remote_path=remote_path,
                item_metadata={
                    "user": {"extracted_from_pdf": True, "original_item_id": item.id}
                },
                overwrite=True,
                raise_on_error=True,
            )

            if new_items is None:
                logger.error(f"Upload returned None | item_id={item.id} local_paths={new_items_path}")
                raise dl.PlatformException(f"No items was uploaded! local paths: {new_items_path}")
            elif isinstance(new_items, dl.Item):
                all_items = [new_items]
            else:
                all_items = [item for item in new_items]

            try:
                uploaded_names = [it.name for it in all_items]
            except Exception:
                uploaded_names = ["<unknown>"]
            logger.info(
                f"Upload completed | item_id={item.id} uploaded_count={len(all_items)} remote_path={remote_path} names={uploaded_names}"
            )

        return all_items

    @staticmethod
    def iter_pdf_text(pdf_path: str, timeout: int = 60) -> Iterable[str]:
        """Extract text from PDF using pdftotext with timeout protection"""
        cmd = ["pdftotext", "-enc", "UTF-8", pdf_path, "-"]
        
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
        except FileNotFoundError:
            raise Exception("pdftotext command not found. Install poppler-utils.")
        
        start = time.time()
        try:
            assert proc.stdout is not None
            while True:
                if time.time() - start > timeout:
                    proc.kill()
                    raise Exception(f"PDF extraction timed out after {timeout} seconds")
                
                chunk = proc.stdout.read(1 << 20)
                if not chunk:
                    break
                yield chunk.decode("utf-8", errors="replace")
                
        except Exception as e:
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception as kill_error:
                logger.error(f"Error killing process: {kill_error}")
            raise Exception(f"PDF extraction failed: {str(e)}")

    def extract_pdf_text_with_pdftotext(self, pdf_path: str, timeout: int = 60) -> str:
        """Extract complete PDF text using pdftotext with timeout"""
        logger.info(f"Extracting text with pdftotext | timeout={timeout}s")
        return "".join(self.iter_pdf_text(pdf_path, timeout=timeout))

    @staticmethod
    def extract_text_from_pdf(pdf_path: str, timeout: int = 300) -> List[str]:
        """
        Extracts text from a PDF file and saves it as a single .txt file.
        Uses pdftotext for better text extraction quality.

        Args:
            pdf_path (str): The path to the PDF file to be processed.
            timeout (int): Timeout in seconds for the extraction process

        Returns:
            list: A list containing the path to the generated .txt file.
        """
        logger.info(f"Begin text extraction | pdf_path={pdf_path} timeout={timeout}s")
        
        try:
            # Use pdftotext for extraction with timeout
            extractor = PdfExtractor()
            text_content = extractor.extract_pdf_text_with_pdftotext(pdf_path, timeout=timeout)
            
            new_item_path = f'{os.path.splitext(pdf_path)[0]}.txt'
            
            with open(new_item_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            logger.info(f"Text file written | path={new_item_path} characters={len(text_content)}")
            
        except Exception:
            logger.exception(f"Error during text extraction | pdf_path={pdf_path}")
            raise

        return [new_item_path]

    @staticmethod
    def extract_images_from_pdf(pdf_path) -> List:
        """
        Extracts images from a PDF file and saves them as separate image files.

        Args:
            pdf_path (str): The path to the PDF file to extract images from.

        Returns:
            list: A list of paths to the saved image files extracted from the PDF.
        """
        logger.info(f"Begin image extraction | pdf_path={pdf_path}")
        # Use context manager to ensure PDF document is properly closed
        with fitz.open(pdf_path) as pdf_file:
            images_paths = list()
            # iterate over PDF pages
            for page_index in range(len(pdf_file)):

                page = pdf_file.load_page(page_index)  # load the page
                image_list = page.get_images(full=True)  # get images on the page

                if image_list:
                    logger.info(f"Found a total of {len(image_list)} images on page {page_index}")
                else:
                    logger.info(f"No images found on page {page_index}")

                for image_index, img in enumerate(image_list, start=1):
                    # get the cross-reference number of the image object in the PDF (xref - the PDF reader way to locate and access various objects).
                    xref = img[0]

                    base_image = pdf_file.extract_image(xref)
                    image_bytes, image_ext = base_image["image"], base_image["ext"]

                    # save the image
                    image_name = f'{os.path.splitext(pdf_path)[0]}_page_{page_index + 1}.{image_ext}'
                    with open(image_name, "wb") as image_file:
                        image_file.write(image_bytes)
                        images_paths.append(image_name)
                        logger.info(f"Image saved as {image_name}")

        logger.info(f"Image extraction completed | pdf_path={pdf_path} images_saved={len(images_paths)}")

        return images_paths


if __name__ == "__main__":
    dl.setenv('dell')
    from collections import namedtuple
    extract_images = False
    remote_path_for_extractions = "/extracted_from_pdfs"

   
    context = namedtuple('Context', ['node'])
    context.node = namedtuple('Node', ['metadata'])
    context.node.metadata = {"customNodeConfig": {"extract_images": extract_images, "remote_path_for_extractions": remote_path_for_extractions}}
    item = dl.items.get(item_id="68cab38515563488b075ede7")
    extractor = PdfExtractor()
    output = extractor.pdf_extraction(item=item, context=context)
    print(output)
