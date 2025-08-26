import base64
import json
import os
from itertools import tee
from pathlib import Path

from openai import OpenAI
import requests

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

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_wiki",
            "description": "Search on wikipedia to get synonyms or similar terms. Should be used before query_wiki",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "keyword to search wikipedia, would be a single word",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_wiki",
            "description": "Query on wikipedia with specific title. Can be used after search_wiki",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "wikipedia title",
                    },
                },
                "required": ["title"],
            },
        },
    },
]

def search_wiki(keyword):
    url = "https://en.wikipedia.org/w/api.php"
    params = {"action": "opensearch", "format": "json", "search": keyword, "limit": 10}
    headers = {"User-Agent": "MyApp/1.0 (your.email@example.com)"}
    response = requests.get(url, params=params, headers=headers)
    return json.dumps({"candidates": response.json()[1]})


def query_wiki(title):
    result = ""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",
        "explaintext": True,
    }
    headers = {"User-Agent": "MyApp/1.0 (your.email@example.com)"}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    pages = data["query"]["pages"]
    for page in pages.values():
        if "extract" in page:
            result += page["extract"]
            result += "\n\n"

    return result


class ToolCalls:
    def __init__(self, stream):
        self.stream = stream
        self.consumed = False
        self.buffer = None

    def __len__(self) -> int:
        return len(self._consume())

    def __iter__(self):
        for id, name, args in self._func_args():
            params = json.loads(args)
            compact_args = json.dumps(params)
            if name == "search_wiki":
                yield (id, name, compact_args, search_wiki(**params))
            if name == "query_wiki":
                yield (id, name, compact_args, query_wiki(**params))

    def __str__(self) -> str:
        self._consume()
        return ";".join([f"{name}({args})" for _, name, args in self._func_args()])

    def _func_args(self):
        for fn_call in self._consume().values():
            yield (fn_call["id"], fn_call["fn"]["name"], fn_call["fn"]["args"])

    def _consume(self):
        if self.buffer is not None:
            return self.buffer

        buffer = {}
        for tool in self.stream:
            for t in tool:
                index = t.index
                if index not in buffer:
                    buffer[index] = {
                        "id": t.id,
                        "fn": {"name": t.function.name, "args": ""},
                    }
                if t.function.arguments:
                    buffer[index]["fn"]["args"] += t.function.arguments

        self.buffer = buffer
        return self.buffer


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
            tools=tools,
            stream=True,
        )

        stream1, stream2 = tee(stream)

        content = (
            chunk.choices[0].delta.content
            for chunk in stream1
            if chunk.choices and chunk.choices[0].delta.content
        )

        tool_calls = ToolCalls(
            (
                chunk.choices[0].delta.tool_calls
                for chunk in stream2
                if chunk.choices and chunk.choices[0].delta.tool_calls
            )
        )

        return content, tool_calls

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
