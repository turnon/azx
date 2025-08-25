import base64
import os
from itertools import tee
from pathlib import Path

from openai import OpenAI

_mime_types = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
}

_ocr_prompt = """
Extract content from image.

Your answer should be a json, containing abstract and full text in such struct: `{"abstract": "xxxx", "full": "xxxx"}`.

The full text should be in markdown syntax. It may has lists, tables, code.

If something looks like list in full text, represent it with legal markdown list syntax.
""".strip()


class Client:
    def __init__(self, name: str, base_url: str, model: str, api_key: str):
        self.name = name
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def stream_response(self, messages: list[dict]):
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )

        stream1, stream2 = tee(stream)

        return (
            (
                chunk.choices[0].delta.content
                for chunk in stream1
                if chunk.choices and chunk.choices[0].delta.content
            ),
            (
                chunk.choices[0].delta.tool_calls
                for chunk in stream2
                if chunk.choices[0].delta.tool_calls
            ),
        )

    def ocr(self, uri, prompt=_ocr_prompt) -> str:
        if os.path.exists(uri):
            with open(uri, "rb") as image_file:
                base64_data = base64.b64encode(image_file.read()).decode("utf-8")
                mime_type = _mime_types.get(Path(uri).suffix.lower(), "image/jpeg")
                uri = f"data:{mime_type};base64,{base64_data}"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": uri},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content
