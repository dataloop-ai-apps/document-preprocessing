from pathlib import Path
import dtlpy as dl
import tempfile
import logging
import os

logger = logging.getLogger('audio-transcriptor-logger')


class AudioTranscriptor(dl.BaseServiceRunner):

    def audio_transcription(self, item: dl.Item, context: dl.Context) -> dl.Item:
        """
        Transcribes audio files and returns the original item.
        This is a mock implementation that simply passes through the item.

        Args:
            context (dl.Context): Dataloop context to determine transcription parameters.
            item (dl.Item): Dataloop item, audio file.

        Returns:
            dl.Item: The original item (mock implementation).
        """
        node = context.node
        language = node.metadata['customNodeConfig']['language']
        include_timestamps = node.metadata['customNodeConfig']['include_timestamps']
        confidence_threshold = node.metadata['customNodeConfig']['confidence_threshold']
        remote_path_for_transcriptions = node.metadata['customNodeConfig']['remote_path_for_transcriptions']

        # Check if the item is an audio file
        suffix = Path(item.name).suffix.lower()
        audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma'}
        
        if suffix not in audio_extensions:
            logger.warning(f"Item {item.id} may not be an audio file. Extension: {suffix}")

        logger.info(f"Transcribing audio item: {item.name}")
        logger.info(f"Language: {language}")
        logger.info(f"Include timestamps: {include_timestamps}")
        logger.info(f"Confidence threshold: {confidence_threshold}")
        logger.info(f"Remote path: {remote_path_for_transcriptions}")

        # Mock transcription - in a real implementation, this would transcribe the audio
        # For now, we just return the original item with metadata
        logger.info(f"Mock transcription completed for item: {item.id}")
        
        # Add metadata to indicate transcription
        item.metadata['user'] = item.metadata.get('user', {})
        item.metadata['user']['transcribed'] = True
        item.metadata['user']['transcription_language'] = language
        item.metadata['user']['timestamps_included'] = include_timestamps
        item.metadata['user']['confidence_threshold'] = confidence_threshold
        item.update()

        return item 