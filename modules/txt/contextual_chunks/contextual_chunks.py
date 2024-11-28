from pathlib import Path
import dtlpy as dl
import tempfile
import logging
import os

logger = logging.getLogger('contextual-chunks')


class ServiceRunner(dl.BaseServiceRunner):

    def chunk_to_prompt(self, item: dl.Item, context: dl.Context) -> dl.Item:
        """
        Creates Contextual prompt item from a txt chunk item.

        :param item: Chunk item
        :param context: The Dataloop context providing parameters for chunking, including:
                - `remote_path` (str): The remote path for uploading the prompt chunk.
        """

        node = context.node
        remote_path = node.metadata['customNodeConfig']['remote_path']

        if not item.mimetype == 'text/plain':
            raise ValueError(f"Item id : {item.id} is not a txt file! This functions excepts txt only.")

        # Download item
        buffer = item.download(save_locally=False)
        chunk_text = buffer.read().decode('utf-8')

        original_item_id = item.metadata.get('user', {}).get('original_item_id')

        if original_item_id is None:
            raise dl.exceptions.NotFound(
                f"Item {item.id} is missing the 'original_item_id' in its metadata. Please add "
                f"'metadata.user.original_item_id' with the ID of the item from which this chunk was created.")

        buffer = dl.items.get(item_id=original_item_id).download(save_locally=False)
        original_text = buffer.read().decode('utf-8')

        p_item = self.contextual_prompt(original_text=original_text,
                                        chunk_text=chunk_text,
                                        prompt_item_name=item.name)

        prompt_item = item.dataset.items.upload(p_item, remote_path=remote_path,
                                                item_metadata={'user': {'txt_chunk_id': item.id,
                                                                        'original_item_id': original_item_id}})

        return prompt_item

    @staticmethod
    def contextual_prompt(original_text: str, chunk_text: str, prompt_item_name: str):
        prompt_text = f"""<document> 
                        {original_text} 
                        </document> 
                        Here is the chunk we want to situate within the whole document. 
                        <chunk> 
                        {chunk_text} 
                        </chunk> 
                        Please give a short succinct context to situate this chunk within the overall document for the 
                        purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        prompt_item = dl.PromptItem(name=prompt_item_name)
        prompt = dl.Prompt(key='1')
        prompt.add_element(mimetype=dl.PromptType.TEXT, value=prompt_text)

        prompt_item.prompts.append(prompt)

        return prompt_item

    def add_response_to_chunk(self, item: dl.Item, model: dl.Model, context: dl.Context) -> dl.Item:
        """
        Creates Contextual prompt item from a txt chunk item.

        :param item: Prompt item.
        :param item: Model entity generated the response.
        :param context: The Dataloop context providing parameters for chunking, including:
                - `remote_path` (str): The remote path for uploading the prompt chunk.
                - `overwrite_chunk` (bool): Whether to create a new chunk item or overwrite the original chunk.
        """

        node = context.node
        remote_path = node.metadata['customNodeConfig']['remote_path']
        overwrite_chunk = node.metadata['customNodeConfig']['overwrite_chunk']

        prompt_item = dl.PromptItem.from_item(item)
        messages = prompt_item.to_messages(model_name=model.name)
        assistant_response = [message.get("content", [{}])[0].get("text", "") for message in messages if
                              message.get("role") == 'assistant']

        if len(assistant_response) < 1:
            raise dl.exceptions.NotFound(f"Item id {item.id} has no annotations by Model {model.id}")

        context = assistant_response[0]
        logger.info(
            f"Found {len(assistant_response)} Assistance responses. Taking the first one, and considers it as the "
            f"context for the chunk.")

        original_item_id = item.metadata.get('user', {}).get('original_item_id')
        if original_item_id is None:
            raise dl.exceptions.NotFound(
                f"Item {item.id} is missing the 'original_item_id' in its metadata. Please add "
                f"'metadata.user.original_item_id' with the ID of the item from which this chunk was created.")

        original_item = dl.items.get(item_id=original_item_id)
        buffer = original_item.download(save_locally=False)
        chunk_text = buffer.read().decode('utf-8')
        prompt_text = f"{context} \n {chunk_text}"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, f"{Path(item.name).stem}.txt")

            # Write to the temporary file
            with open(temp_file, "w", encoding="utf-8") as temp_text_file:
                temp_text_file.write(prompt_text)

            # Upload the file
            if overwrite_chunk is True:
                original_item.dataset.items.upload(
                    local_path=temp_file,
                    remote_name=original_item.name,
                    overwrite=True
                )
            else:
                remote_name = f"{Path(original_item.name).stem}_contextual.txt"
                original_item.dataset.items.upload(
                    local_path=temp_file,
                    remote_path=remote_path,
                    remote_name=remote_name,
                    item_metadata={
                        'user': {
                            'original_item_id': original_item_id,
                            'chunk_id': item.id
                        }
                    }
                )

        return item
