from functools import lru_cache

import whisper

MODEL_NAME = "small"


@lru_cache(maxsize=1)
def get_model():
    """Load the Whisper model once per process; loading is the slow part."""
    return whisper.load_model(MODEL_NAME)


def transcribe_audio_to_text(audio_file_path: str) -> str:
    """Transcribe a local audio file and return the plain text."""
    result = get_model().transcribe(audio_file_path)
    return result["text"]
