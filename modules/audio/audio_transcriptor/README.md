# Audio Transcriptor

This app transcribes audio files and returns the original item with transcription metadata. 
This is a mock implementation for testing pipeline flows.

## Parameters

The following parameters can be controlled via the Dataloop node panel:

- `transcription language`: A string parameter that determines the language for transcription (en, es, fr, de, it, pt, auto). Default is `en`.
- `include timestamps`: A boolean parameter that determines whether to include timestamps in transcription. Default is `False`.
- `confidence threshold`: A number parameter that sets the minimum confidence threshold for transcription. Default is `0.7`.
- `remote path for transcriptions`: The path where transcribed files would be saved in the Dataloop dataset after processing.

### Methods

#### `audio_transcription(self, item: dl.Item, context: dl.Context) -> dl.Item`

This method handles the audio transcription:

1. Validates that the item is an audio file (supports .mp3, .wav, .m4a, .flac, .aac, .ogg, .wma).
2. Retrieves configuration parameters from the node context.
3. Logs transcription information.
4. Adds transcription metadata to the item.
5. Returns the original item (mock implementation).

## Supported File Types

- `.mp3` (MPEG Audio Layer 3)
- `.wav` (Waveform Audio File)
- `.m4a` (MPEG-4 Audio)
- `.flac` (Free Lossless Audio Codec)
- `.aac` (Advanced Audio Coding)
- `.ogg` (Ogg Vorbis)
- `.wma` (Windows Media Audio)

## Transcription Features

- **Mock Transcription**: This is a dummy implementation that passes through the original item
- **Language Support**: Configurable language detection and transcription
- **Timestamp Support**: Optional timestamp inclusion in transcriptions
- **Confidence Filtering**: Configurable confidence threshold for transcription quality
- **Metadata Addition**: Adds transcription metadata to track processing
- **Logging**: Comprehensive logging for debugging and monitoring 