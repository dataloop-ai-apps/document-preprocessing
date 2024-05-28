from pathlib import Path
from typing import List
import dtlpy as dl
import logging
import fitz
import os

logger = logging.getLogger(name=__name__)


class ServiceRunner(dl.BaseServiceRunner):
    """
    This Service contains functions for converting pdf dataloop item to an image dataloop item.
    """

    @staticmethod
    def pdf_item_to_images(item: dl.Item, context: dl.Context) -> List[dl.Item]:
        """
        Convert pdf dataloop item to an image item.
        :param item: pdf dataloop item.
        :param context: Dataloop context to set if to use replace modality for visualize the item in the platform.
        :return:
        """
        node = context.node
        apply_modality = node.metadata['customNodeConfig']['apply_modality']

        suffix = Path(item.name).suffix
        if not suffix == '.pdf':
            raise dl.PlatformException(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        # Downloading local path
        local_path = os.path.join(os.getcwd(), 'datasets', item.dataset.id)
        item_local_path = os.path.join(local_path, os.path.dirname(item.filename[1:]))
        item_local_path = item.download(local_path=item_local_path)

        images_paths = ServiceRunner.convert_pdf_to_image(file_path=item_local_path)

        logger.info(f"Total of {len(images_paths)} images were created")
        # Uploading all created items - upload bulk
        img_items = item.dataset.items.upload(local_path=images_paths,
                                              remote_path='/images-files',
                                              item_metadata={
                                                  'user': {'pdf_to_image': {'converted_to_image': True,
                                                                            'original_item_id': item.id}}}
                                              )

        # Uploader returns generator or a single item, or None
        if img_items is None:
            first_item = None
            apply_modality = False
            logger.info("Uploading items resulted in None. Skipping, as apply modality is true.")
        elif not isinstance(img_items, dl.Item):
            first_item = next((item for item in img_items if item.name.endswith('0.png')))
        else:
            first_item = img_items

        if apply_modality is True:
            # if the pdf contain more than 1 page, only the first image will serve as preview modality.
            ServiceRunner.apply_modality(item=item, ref_item=first_item)

        # Remove local files:
        for file_path in images_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"{file_path} removed")
            else:
                print(f"{file_path} does not exist")

        os.remove(item_local_path)

        return img_items

    @staticmethod
    def convert_pdf_to_image(file_path: str) -> List:
        """
        Convert pdf file to a txt file in the platform. Visualize using modality.
        :param file_path: File local path.
        :return: created images paths

        """
        filename = Path(file_path).stem
        # Path to save the generated images
        images_path = os.path.join(os.path.dirname(file_path), 'images_files')
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

    @staticmethod
    def apply_modality(item: dl.Item, ref_item: dl.Item):
        """
        Apply to replace modality in the platform
        :param item: dataloop pdf item
        :param ref_item: dataloop image item
        """
        item.modalities.create(modality_type='replace',
                               name='reference-viewer',
                               mimetype=ref_item.mimetype,
                               ref=ref_item.id)
        item.update(system_metadata=True)  # TODO : IS IT NEEDED?


if __name__ == '__main__':
    dl.setenv('rc')
    project = dl.projects.get(project_name="text-project")
    dataset = project.datasets.get(dataset_name="mortgage-dataset")
    item = dataset.items.get(item_id='65f9984b6861c61ce19447d9')

    # dl.setenv('prod')
    # project = dl.projects.get(project_name='text-project')
    # dataset = project.datasets.get(dataset_name='mortgage-data')
    # item = dataset.items.get(item_id='660e92f3aadac605ee7713db')

    s = ServiceRunner()
    s.pdf_item_to_images(item=item, context=dl.Context())
