from pathlib import Path
from typing import List
import dtlpy as dl
import tempfile
import logging
import pypdf
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

        if not item.mimetype == 'application/pdf':
            raise ValueError(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        # Download item
        with tempfile.TemporaryDirectory() as temp_dir:
            item_local_path = item.download(local_path=temp_dir)

            new_items_path = self.extract_text_from_pdf(pdf_path=item_local_path)
            if extract_images is True:
                new_images_path = self.extract_images_from_pdf(pdf_path=item_local_path)
                new_items_path.extend(new_images_path)

            new_items = item.dataset.items.upload(local_path=new_items_path,
                                                  remote_path=remote_path_for_extractions,
                                                  item_metadata={
                                                      'user': {'extracted_from_pdf': True,
                                                               'original_item_id': item.id}},
                                                  overwrite=True)

            if new_items is None:
                raise dl.PlatformException(f"No items was uploaded! local paths: {new_items_path}")
            elif isinstance(new_items, dl.Item):
                all_items = [new_items]
            else:
                all_items = [item for item in new_items]

        return all_items

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> List[str]:
        """
        Extracts text from a PDF file and saves it as a single .txt file.

        Args:
            pdf_path (str): The path to the PDF file to be processed.

        Returns:
            list: A list containing the path to the generated .txt file.
        """
        with open(pdf_path, 'rb') as open_file:
            pdf_reader = pypdf.PdfReader(open_file)
            logger.info(f"PDF metadata: {pdf_reader.metadata}")

            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())

            new_item_path = f'{os.path.splitext(pdf_path)[0]}.txt'
            with open(new_item_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(text_parts))

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
                    logger.info("No images found on page", page_index)

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

        return images_paths