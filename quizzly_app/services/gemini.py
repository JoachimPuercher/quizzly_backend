from typing import List

from google import genai
from pydantic import BaseModel, Field


class Question(BaseModel):
    """Schema of one generated multiple choice question."""

    question_title: str = Field(description="The question itself.")
    question_options: List[str] = Field(
        min_length=4,
        max_length=4,
        description="Exactly four possible answers as plain strings.",
    )
    answer: str = Field(
        description=(
            "The correct answer. Must be exactly one of the four strings "
            "in question_options, character for character."
        )
    )


class Quiz(BaseModel):
    """Schema the model has to fill when generating a quiz."""

    title: str = Field(description="The name of the quiz.")
    description: str = Field(description="A short summary of what the quiz is about.")
    questions: List[Question] = Field(
        min_length=10,
        max_length=10,
        description="Exactly ten questions.",
    )


def create_quiz(file_input: str) -> Quiz:
    """Turn a video transcript into a quiz with ten multiple choice questions."""
    client = genai.Client()

    prompt = f"""Create a quiz with exactly 10 questions from the following text.
    The quiz needs a title and a short description. Every question has exactly four
    possible answers. One of them is correct, the other three are wrong but related to
    the topic of the text, so that the choice is not obvious. Vary the position of the
    correct answer between the questions, so it is not always in the same place in the
    list. The answer field has to repeat the correct option exactly as it appears in
    question_options.

    {file_input}"""

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": Quiz.model_json_schema(),
        },
    )

    return Quiz.model_validate_json(interaction.output_text)
