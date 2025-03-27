from pathlib import Path
from typing import List
import dtlpy as dl
import tempfile
import logging
import fitz
import os

logger = logging.getLogger(name=__name__)


class ServiceRunner(dl.BaseServiceRunner):
    """
    This Service contains functions for converting pdf dataloop item to an image dataloop item.
    """

    @staticmethod
    def pdf_item_to_images(item: dl.Item) -> List[dl.Item]:
        """
        Convert pdf dataloop item to an image item.
        :param item: pdf dataloop item.
        :param context: Dataloop context to set if to use replace modality for visualize the item in the platform.
        :return:
        """

        if not item.mimetype == "application/pdf":
            raise dl.PlatformException(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Downloading local path
            item_local_path = item.download(local_path=temp_dir)

            images_paths = ServiceRunner.convert_pdf_to_image(file_path=item_local_path, temp_dir=temp_dir)

            logger.info(f"Total of {len(images_paths)} images were created")
            # Uploading all created items - upload bulk
            img_items = item.dataset.items.upload(
                local_path=images_paths,
                remote_path="/images-files",
                item_metadata={"user": {"pdf_to_image": {"converted_to_image": True, "original_item_id": item.id}}},
            )

        # Uploader returns generator or a single item, or None
        if img_items is None:
            all_items = list()
        elif isinstance(img_items, dl.Item):
            all_items = [img_items]
        else:
            all_items = [item for item in img_items]

        return all_items

    @staticmethod
    def convert_pdf_to_image(file_path: str, temp_dir: str) -> List:
        """
        Convert pdf file to a txt file in the platform. Visualize using modality.
        :param file_path: File local path.
        :param temp_dir: Temporary directory to store images.
        :return: created images paths

        """
        filename = Path(file_path).stem
        # Path to save the generated images
        images_path = os.path.join(temp_dir, "images_files")
        os.makedirs(images_path, exist_ok=True)
        paths = list()
        # The converted images
        pdf_document = fitz.open(file_path)

        # Iterate over each page
        for page_number in range(pdf_document.page_count):
            # Get the page
            image_filename = os.path.join(images_path, f"{filename}-{page_number}.png")
            page = pdf_document.load_page(page_number)

            # Render the page as an image (PNG)
            image = page.get_pixmap()

            # Save the image to a file
            image.save(image_filename)
            paths.append(image_filename)

        # Close the PDF document
        pdf_document.close()

        return paths


if __name__ == "__main__":
    dl.setenv("")
    item = dl.items.get(item_id="")

    s = ServiceRunner()
    s.pdf_item_to_images(item=item)
