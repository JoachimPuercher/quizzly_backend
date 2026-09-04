import whisper


def transcribe_audio_to_text(audio_file_path: str):
    """Transcribe a local audio file with Whisper."""
    model = whisper.load_model("small")
    result = model.transcribe(audio_file_path)
    return result
