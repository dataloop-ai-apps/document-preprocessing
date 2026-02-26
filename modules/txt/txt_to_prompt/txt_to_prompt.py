import json
import logging
import os

import dtlpy as dl

logger = logging.getLogger('document-preprocessing.txt-to-prompt')

DEFAULT_OUTPUT_DIR = '/prompt_items_dir'
DEFAULT_SYSTEM_PROMPT = ''


class ServiceRunner(dl.BaseServiceRunner):

    def run(self, item: dl.Item, context: dl.Context) -> dl.Item:
        """
        Receives a text item, reads its content, wraps it in a PromptItem,
        and uploads the prompt item to the same dataset.

        Args:
            item (dl.Item): A text (.txt) item.
            context (dl.Context): Pipeline context containing node configuration.

        Returns:
            dl.Item: The newly uploaded prompt item.
        """
        logger.info(f"Processing text item: {item.id} ({item.name})")

        if item.mimetype != 'text/plain':
            raise ValueError(
                f"Item {item.id} is not a txt file. This function accepts txt only. "
                f"Use other extracting applications from Marketplace to convert to txt first."
            )

        node_config = context.node.metadata.get('customNodeConfig', {})
        output_dir = node_config.get('output_dir', DEFAULT_OUTPUT_DIR)
        system_prompt = node_config.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
        metadata_keys = node_config.get('metadata_keys_to_extract', [])
        add_metadata_to_prompt = node_config.get('add_metadata_to_prompt', False)

        buffer = item.download(save_locally=False)
        text_content = buffer.read().decode('utf-8')
        logger.info(f"Read text content ({len(text_content)} chars) from item {item.id}")

        extracted_metadata = self._extract_metadata(item, metadata_keys)

        base_name = os.path.splitext(item.name)[0]
        prompt_item_name = f"{base_name}.json"

        prompt_item = dl.PromptItem(name=prompt_item_name)
        prompt = dl.Prompt(key='1')

        if system_prompt:
            prompt.add_element(mimetype=dl.PromptType.TEXT, value=system_prompt, role='system')

        if add_metadata_to_prompt and extracted_metadata:
            metadata_text = json.dumps(extracted_metadata, ensure_ascii=False, indent=2)
            user_text = f"Metadata:\n{metadata_text}\n\nContent:\n{text_content}"
        else:
            user_text = text_content

        prompt.add_element(mimetype=dl.PromptType.TEXT, value=user_text)
        prompt_item.prompts.append(prompt)

        item_metadata = {'user': {'source_item_id': item.id}}
        if not add_metadata_to_prompt and extracted_metadata:
            for key, value in extracted_metadata.items():
                if isinstance(value, dict) and key in item_metadata:
                    item_metadata[key].update(value)
                else:
                    item_metadata[key] = value

        uploaded_item = item.dataset.items.upload(
            prompt_item,
            remote_path=output_dir,
            item_metadata=item_metadata,
            overwrite=True,
        )
        logger.info(f"Uploaded prompt item: {uploaded_item.id} ({uploaded_item.name})")

        return uploaded_item

    @staticmethod
    def _extract_metadata(item: dl.Item, metadata_keys: list) -> dict:
        """
        Extract metadata values from item using dot-notation key paths.

        Returns a nested dict mirroring the original structure.
        """
        extracted = {}
        for key_path in metadata_keys:
            parts = key_path.split('.')
            value = item.metadata
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is not None:
                target = extracted
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = value
                logger.info(f"Extracted metadata '{key_path}'")
        return extracted
