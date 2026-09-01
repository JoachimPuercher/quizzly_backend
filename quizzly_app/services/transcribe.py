import whisper

def transcribe_audio_to_text(audio_file_path:str):
    model = whisper.load_model("turbo")
    result = model.transcribe(audio_file_path)
    print (f"R", result)
    print (f"RT", result["text"])