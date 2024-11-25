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
        # node = context.node
        # extract_images = node.metadata['customNodeConfig']['extract_images']
        # remote_path_for_extractions = node.metadata['customNodeConfig']['remote_path_for_extractions']
        # Local test
        extract_images = True
        remote_path_for_extractions = '/extracted_from_pdfs'

        if not item.mimetype == 'application/pdf':
            raise ValueError(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        # Download item
        item_local_path = item.download(local_path=os.getcwd())

        item_metadata = {'user': {'extracted_from_pdf': True,
                                  'original_item_id': item.id}}

        new_items = self.extract_text_from_pdf(pdf_path=item_local_path,
                                               remote_path_for_extractions=remote_path_for_extractions,
                                               item_metadata=item_metadata)
        if extract_images is True:
            new_images_items = self.extract_images_from_pdf(pdf_path=item_local_path,
                                                            remote_path_for_extractions=remote_path_for_extractions,
                                                            item_metadata=item_metadata
                                                            )
            new_items.extend(new_images_items)

        os.remove(item_local_path)

        return new_items

    @staticmethod
    def extract_text_from_pdf(pdf_path: str, remote_path_for_extractions: str, item_metadata: dict) -> List[dl.Item]:
        """
        Extracts text from a PDF file and saves each page as a separate .txt file.

        Args:
            pdf_path (str): The path to the PDF file to be processed.
            remote_path_for_extractions (str) : remote path to upload.
            item_metadata (dict): item's metadata.


        Returns:
            list: A list of new items.
        """
        open_file = open(pdf_path, 'rb')
        pdf_reader = pypdf.PdfReader(open_file)
        logger.info(f"PDF metadata: {pdf_reader.metadata}")

        total_pages = len(pdf_reader.pages)
        text_files = []

        # Loop through each page and save text to individual .txt files
        with tempfile.TemporaryDirectory() as temp_dir:
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()

                # Define the output path for each page's text
                new_item_path = os.path.join(temp_dir, f"{Path(item.name).stem}_page_{page_num + 1}.txt")
                with open(new_item_path, 'w', encoding='utf-8') as f:
                    f.write(page_text)

                # Add the file path to the list of text files
                text_files.append(new_item_path)

            open_file.close()

            new_items = item.dataset.items.upload(local_path=text_files,
                                                  remote_path=remote_path_for_extractions,
                                                  item_metadata=item_metadata)

            if new_items is None:
                raise dl.PlatformException(f"No items was uploaded!")
            elif isinstance(new_items, dl.Item):
                all_items = [new_items]
            else:
                all_items = [item for item in new_items]

        return all_items

    @staticmethod
    def extract_images_from_pdf(pdf_path: str, remote_path_for_extractions: str, item_metadata: dict) -> List[dl.Item]:
        """
        Extracts images from a PDF file and saves them as separate image files.

        Args:
            pdf_path (str): The path to the PDF file to extract images from.
            remote_path_for_extractions (str) : remote path to upload.
            item_metadata (dict): item's metadata.

        Returns:
            list: A list of items extracted from the PDF.
        """
        pdf_file = fitz.open(pdf_path)
        images_paths = list()
        # iterate over PDF pages
        with tempfile.TemporaryDirectory() as temp_dir:
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
                    image_name = os.path.join(temp_dir, f"{Path(pdf_path).stem}_page_{page_index + 1}.{image_ext}")
                    # image_name = f'{os.path.splitext(pdf_path)[0]}_page_{page_index + 1}.{image_ext}'
                    with open(image_name, "wb") as image_file:
                        image_file.write(image_bytes)
                        images_paths.append(image_name)
                        logger.info(f"Image saved as {image_name}")

            new_items = item.dataset.items.upload(local_path=images_paths,
                                                  remote_path=remote_path_for_extractions,
                                                  item_metadata=item_metadata)

            if new_items is None:
                logger.warning(f"No images items was uploaded!")
            elif isinstance(new_items, dl.Item):
                all_items = [new_items]
            else:
                all_items = [item for item in new_items]

        return all_items


if __name__ == '__main__':
    dl.setenv('rc')
    item = dl.items.get(None, "673472b4e9e82b7bc45034ef")
    s = PdfExtractor()
    items = s.pdf_extraction(item=item, context=dl.Context())
