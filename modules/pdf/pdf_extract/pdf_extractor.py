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

logger = logging.getLogger("pdf-to-text-logger")


class PdfExtractor(dl.BaseServiceRunner):

    @staticmethod
    def iter_pdf_text(pdf_path: str, timeout: int = 60) -> Iterable[str]:
        cmd = ["pdftotext", "-enc", "UTF-8", pdf_path, "-"]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
        )
        start = time.time()
        try:
            while True:
                if time.time() - start > timeout:
                    proc.kill()
                    raise Exception(f"PDF extraction timed out after {timeout} seconds")
                chunk = proc.stdout.read(1 << 20)
                if not chunk:
                    break
                yield chunk.decode("utf-8", errors="replace")
        except Exception:
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception as e:
                print(e)
            raise Exception(f"PDF extraction timed out after {timeout} seconds")

    def extract_pdf_text(self, pdf_path: str) -> str:
        return "".join(self.iter_pdf_text(pdf_path))

    def pdf_extraction(self, item: dl.Item, context: dl.Context) -> dl.Item:
        remote_path_for_extractions = context.node.metadata["customNodeConfig"][
            "remote_path_for_extractions"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            item_local_path = item.download(local_path=temp_dir)
            text = self.extract_pdf_text(pdf_path=item_local_path)
            text_file_path = os.path.join(temp_dir, f"{Path(item.name).stem}.txt")
            with open(text_file_path, "w", encoding="utf-8") as temp_text_file:
                temp_text_file.write(text)
            name, ext = os.path.splitext(item.name)
            remote_path = os.path.join(
                remote_path_for_extractions, item.dir.lstrip("/"), f"{name}.txt"
            ).replace("\\", "/")
            new_item = item.dataset.items.upload(
                local_path=text_file_path,
                remote_path=remote_path,
                item_metadata={
                    "user": {"extracted_from_pdf": True, "original_item_id": item.id}
                },
                overwrite=True,
                raise_on_error=True,
            )

        return new_item

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
                    logger.info(
                        f"Found a total of {len(image_list)} images on page {page_index}"
                    )
                else:
                    logger.info(f"No images found on page {page_index}")

                for image_index, img in enumerate(image_list, start=1):
                    # get the cross-reference number of the image object in the PDF (xref - the PDF reader way to locate and access various objects).
                    xref = img[0]

                    base_image = pdf_file.extract_image(xref)
                    image_bytes, image_ext = base_image["image"], base_image["ext"]

                    # save the image
                    image_name = f"{os.path.splitext(pdf_path)[0]}_page_{page_index + 1}.{image_ext}"
                    with open(image_name, "wb") as image_file:
                        image_file.write(image_bytes)
                        images_paths.append(image_name)
                        logger.info(f"Image saved as {image_name}")

        logger.info(
            f"Image extraction completed | pdf_path={pdf_path} images_saved={len(images_paths)}"
        )

        return images_paths


if __name__ == "__main__":
    dl.setenv("dell")
    from collections import namedtuple

    extract_images = False
    remote_path_for_extractions = "/extracted_from_pdfs"

    context = namedtuple("Context", ["node"])
    context.node = namedtuple("Node", ["metadata"])
    context.node.metadata = {
        "customNodeConfig": {
            "extract_images": extract_images,
            "remote_path_for_extractions": remote_path_for_extractions,
        }
    }
    item = dl.items.get(item_id="68cab38515563488b075ede7")
    extractor = PdfExtractor()
    output = extractor.pdf_extraction(item=item, context=context)
    print(output)
