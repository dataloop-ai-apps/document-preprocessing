from pathlib import Path
from typing import List
import dtlpy as dl
import logging
import shutil
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
        # Local test
        # extract_images = False
        # remote_path_for_extractions = '/extracted_from_pdfs'

        suffix = Path(item.name).suffix
        if not suffix == '.pdf':
            raise dl.PlatformException(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        # Download item
        local_path = os.path.join(os.getcwd(), 'datasets', item.dataset.id, 'items', os.path.dirname(item.filename[1:]))
        os.makedirs(local_path, exist_ok=True)
        item_local_path = item.download(local_path=local_path)

        new_items_path = self.extract_text_from_pdf(pdf_path=item_local_path)
        if extract_images is True:
            new_images_path = self.extract_images_from_pdf(pdf_path=item_local_path)
            new_items_path.extend(new_images_path)

        new_items = item.dataset.items.upload(local_path=new_items_path,
                                              remote_path=remote_path_for_extractions,
                                              item_metadata={
                                                  'user': {'extracted_from_pdf': True,
                                                           'original_item_id': item.id}})

        if new_items is None:
            raise dl.PlatformException(f"No items was uploaded! local paths: {new_items_path}")
        elif isinstance(new_items, dl.Item):
            all_items = [new_items]
        else:
            all_items = [item for item in new_items]

        shutil.rmtree(local_path)

        return all_items

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> List[str]:
        """
        Extracts text from a PDF file and saves each page as a separate .txt file.

        Args:
            pdf_path (str): The path to the PDF file to be processed.

        Returns:
            list: A list of paths to the generated .txt files, each corresponding to a page in the PDF.
        """
        open_file = open(pdf_path, 'rb')
        pdf_reader = pypdf.PdfReader(open_file)
        logger.info(f"PDF metadata: {pdf_reader.metadata}")

        total_pages = len(pdf_reader.pages)
        text_files = []

        # Loop through each page and save text to individual .txt files
        for page_num in range(total_pages):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()

            # Define the output path for each page's text
            new_item_path = f'{os.path.splitext(pdf_path)[0]}_page_{page_num + 1}.txt'
            with open(new_item_path, 'w', encoding='utf-8') as f:
                f.write(page_text)

            # Add the file path to the list of text files
            text_files.append(new_item_path)

        open_file.close()
        return text_files

    @staticmethod
    def extract_images_from_pdf(pdf_path) -> List:
        """
        Extracts images from a PDF file and saves them as separate image files.

        Args:
            pdf_path (str): The path to the PDF file to extract images from.

        Returns:
            list: A list of paths to the saved image files extracted from the PDF.
        """
        pdf_file = fitz.open(pdf_path)
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


if __name__ == '__main__':
    import dtlpy as dl

    dl.setenv('prod')
    item = dl.items.get(item_id="")
    s = PdfExtractor()
    s.pdf_extraction(item=item, context=dl.Context())
