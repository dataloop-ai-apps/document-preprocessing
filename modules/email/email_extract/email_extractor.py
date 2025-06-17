import email
import email.policy
from pathlib import Path
import dtlpy as dl
import tempfile
import logging
import os
from email.message import EmailMessage

logger = logging.getLogger('email-to-text-logger')


class EmailExtractor(dl.BaseServiceRunner):

    def email_extraction(self, item: dl.Item, context: dl.Context) -> dl.Item:
        """
        Extracts an EML file item and uploads it as a TXT file.

        Args:
            context (dl.Context): Dataloop context to determine extraction parameters.
            item (dl.Item): Dataloop item, EML file.

        Returns:
            dl.Item: New text item containing the extracted content in TXT format.
        """
        node = context.node
        extract_headers = node.metadata['customNodeConfig']['extract_headers']
        extract_attachments = node.metadata['customNodeConfig']['extract_attachments']
        remote_path_for_extractions = node.metadata['customNodeConfig']['remote_path_for_extractions']

        suffix = Path(item.name).suffix.lower()
        if suffix not in {'.eml', '.msg'}:
            raise ValueError("Only .eml and .msg files are supported for extraction.")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the email file
            item_local_path = item.download(local_path=temp_dir, save_locally=True)
            logger.info(f"Downloaded email item to temporary path: {item_local_path}")

            # Extract text content from email
            text_content = self.extract_email_content(
                eml_path=item_local_path,
                extract_headers=extract_headers,
                extract_attachments=extract_attachments
            )

            # Save extracted content to text file
            output_path = os.path.join(temp_dir, f"{Path(item.name).stem}_text.txt")
            with open(output_path, "w", encoding="utf-8") as temp_text_file:
                temp_text_file.write(text_content)
            logger.info(f"Email text saved to temporary file: {output_path}")

            # Upload the text file
            new_item = item.dataset.items.upload(
                local_path=output_path,
                remote_path=remote_path_for_extractions,
                item_metadata={
                    'user': {
                        'extracted_from_email': True,
                        'original_item_id': item.id
                    }
                }
            )

            if new_item is None:
                raise dl.PlatformException(f"No items was uploaded! local paths: {output_path}")

        return new_item

    @staticmethod
    def extract_email_content(eml_path, extract_headers=True, extract_attachments=False) -> str:
        """
        Extracts text content from an EML file, including optional headers and attachment info.

        Args:
            eml_path (str): The local path to the EML file to be processed.
            extract_headers (bool, optional): Whether to include email headers. Default is True.
            extract_attachments (bool, optional): Whether to include attachment information. Default is False.

        Returns:
            str: The extracted email text content.
        """
        full_text = []

        # Parse the email file
        with open(eml_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=email.policy.default)

        # Extract headers if requested
        if extract_headers:
            full_text.append("=== EMAIL HEADERS ===")
            full_text.append(f"From: {msg.get('From', 'Unknown')}")
            full_text.append(f"To: {msg.get('To', 'Unknown')}")
            full_text.append(f"Subject: {msg.get('Subject', 'No Subject')}")
            full_text.append(f"Date: {msg.get('Date', 'Unknown')}")
            if msg.get('Cc'):
                full_text.append(f"Cc: {msg.get('Cc')}")
            if msg.get('Bcc'):
                full_text.append(f"Bcc: {msg.get('Bcc')}")
            full_text.append("")

        # Extract email body content
        full_text.append("=== EMAIL BODY ===")
        body_text = EmailExtractor._extract_body_text(msg)
        if body_text:
            full_text.append(body_text)
        else:
            full_text.append("No text content found in email body.")

        # Extract attachment information if requested
        if extract_attachments:
            attachments = EmailExtractor._extract_attachment_info(msg)
            if attachments:
                full_text.append("")
                full_text.append("=== ATTACHMENTS ===")
                for attachment in attachments:
                    full_text.append(f"- {attachment}")

        return '\n'.join(full_text)

    @staticmethod
    def _extract_body_text(msg):
        """
        Extract text content from email body, handling both plain text and HTML.
        """
        body_parts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        text = part.get_content()
                        if text and text.strip():
                            body_parts.append(text.strip())
                    except Exception as e:
                        logger.warning(f"Error extracting plain text: {e}")

                elif content_type == "text/html":
                    try:
                        html_content = part.get_content()
                        if html_content and html_content.strip():
                            # Basic HTML stripping - remove tags and decode entities
                            import re
                            import html
                            text = re.sub(r'<[^>]+>', '', html_content)
                            text = html.unescape(text)
                            text = re.sub(r'\s+', ' ', text).strip()
                            if text:
                                body_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting HTML text: {e}")
        else:
            # Single part message
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                try:
                    text = msg.get_content()
                    if text and text.strip():
                        body_parts.append(text.strip())
                except Exception as e:
                    logger.warning(f"Error extracting plain text from single part: {e}")

        return '\n\n'.join(body_parts) if body_parts else ""

    @staticmethod
    def _extract_attachment_info(msg):
        """
        Extract information about email attachments.
        """
        attachments = []

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    content_type = part.get_content_type()
                    # Try to get file size if available
                    try:
                        payload = part.get_payload(decode=True)
                        size = len(payload) if payload else 0
                        attachments.append(f"{filename} ({content_type}, {size} bytes)")
                    except Exception:
                        attachments.append(f"{filename} ({content_type})")

        return attachments 