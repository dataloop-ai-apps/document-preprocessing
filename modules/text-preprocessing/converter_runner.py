from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from pathlib import Path
from typing import List
import dtlpy as dl
import logging
import pypdf
import nltk
import os

nltk.download('punkt')
logger = logging.getLogger('pdf-to-text-logger')


class ConvertorRunner(dl.BaseServiceRunner):
    """
    This Service contains extracting functions for pdf files to create clean text files.
    The service allow converting pdf Dataloop items to Text items and create chunks by maximum size.
    """

    @staticmethod
    def pdf_item_to_text(item: dl.Item, context: dl.Context) -> List[dl.Item]:
        """
        The main function for extracting pdf item and saving text files for each chunk.

        :param context: Dataloop context to set the method to chunk by,  maximum size of each chunk and
        maximum overlap between two chunks.
        :param item: Dataloop item, pdf file
        :return: New text items paths (list)
        """
        # node = context.node
        # chunking_strategy = node.metadata['customNodeConfig']['chunking_strategy']
        # max_chunk_size = node.metadata['customNodeConfig']['max_chunk_size']
        # chunk_overlap = node.metadata['customNodeConfig']['chunk_overlap']
        chunking_strategy = 'nltk-paragraphs'
        max_chunk_size = 300
        chunk_overlap = 20

        suffix = Path(item.name).suffix
        if not suffix == '.pdf':
            raise dl.PlatformException(f"Item id : {item.id} is not a PDF file! This functions excepts pdf only")

        # Download path - original items
        local_path = os.path.join(os.getcwd(), 'datasets', item.dataset.id, 'pdf_files',
                                  os.path.dirname(item.filename[1:]))
        os.makedirs(local_path, exist_ok=True)
        item_local_path = item.download(local_path=local_path)

        text = ConvertorRunner.extract_text_from_pdf(
            pdf_path=item_local_path)

        chunks = ConvertorRunner.chunking_strategy(text=text,
                                                   strategy=chunking_strategy,
                                                   chunk_size=max_chunk_size,
                                                   chunk_overlap=chunk_overlap)

        # Save: each chunk as separated text file
        # Saving path - converted text items
        text_files_folder = os.path.join(local_path, 'text_files')
        os.makedirs(text_files_folder, exist_ok=True)

        text_files_paths = []
        for ind, chunk in enumerate(chunks):
            textfile_path = os.path.basename(item_local_path)
            textfile_path = os.path.join(text_files_folder,
                                         os.path.splitext(textfile_path)[0] + '-' + str(ind) + '.txt')

            with open(textfile_path, 'w', encoding='utf-8') as f:
                f.write(chunk)
            text_files_paths.append(textfile_path)

        # Uploading all created items - bulk
        crafted_items = item.dataset.items.upload(local_path=text_files_paths,
                                                  remote_path='/text_files',
                                                  item_metadata={'user': {'pdf_to_text': {'converted_to_text': True,
                                                                                          'original_item_id': item.id}}}
                                                  )

        # TODO: RAISE IF NONE
        if crafted_items is None:
            crafted_items = []
        elif isinstance(crafted_items, dl.Item):
            crafted_items = [crafted_items]
        else:
            crafted_items = [item for item in crafted_items]

        # Remove local files:
        for file_path in text_files_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"{file_path} removed")
            else:
                print(f"{file_path} does not exist")

        # os.remove(item_local_path) # TODO:

        return crafted_items

    @staticmethod
    def chunking_strategy(text: str, strategy: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Chunk text by strategy.
        :param text: text as a string.
        :param strategy: method to chunk by.
        :param chunk_size: maximum size of each chunk.
        :param chunk_overlap: maximum overlap between two chunks.
        :return: A list of string chunks.
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

    @staticmethod
    def extract_text_from_pdf(pdf_path) -> str:
        """
        Extract Text as a string from a pdf file path.
        :param pdf_path: The file path directory
        :return: string of the extracted text
        """
        open_file = open(pdf_path, 'rb')
        ind_manifesto = pypdf.PdfReader(open_file)
        logger.info(f"Pdf metadate: {ind_manifesto.metadata}")

        total_pages = len(ind_manifesto.pages)
        text = ''
        # Extract Text
        for page_num in range(total_pages):
            page = ind_manifesto.pages[page_num]
            page_text = page.extract_text()

            text += page_text + ' '
        return text
