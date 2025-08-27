import base64
import json
import os
import tempfile
from itertools import tee
from pathlib import Path

import requests
from markitdown import MarkItDown
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

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_wiki",
            "description": "Search on wikipedia to get detail info",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "keyword to search wikipedia",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_data",
            "description": "Read data from local file path",
            "parameters": {
                "type": "object",
                "properties": {
                    "uri": {
                        "type": "string",
                        "description": "local file path",
                    },
                },
                "required": ["uri"],
            },
        },
    },
]


def read_data(uri) -> str:
    return MarkItDown().convert(uri).text_content


def search_wiki(keyword) -> str:
    md_pages = []
    md = MarkItDown()
    url = "https://en.wikipedia.org/w/api.php"
    headers = {"User-Agent": "MyApp/1.0 (your.email@example.com)"}

    keyword_params = {
        "action": "opensearch",
        "format": "json",
        "search": keyword,
        "limit": 10,
    }
    keyword_resp = requests.get(url, params=keyword_params, headers=headers)

    for syn in keyword_resp.json()[1]:
        title_args = {
            "action": "query",
            "format": "json",
            "titles": syn,
            "prop": "extracts",
        }
        title_resp = requests.get(url, params=title_args, headers=headers)
        data = title_resp.json()
        pages = data["query"]["pages"]
        for page in pages.values():
            if "extract" in page:
                text = f"# {syn}\n\n"
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as temp_file:
                    temp_file.write(page["extract"])
                    temp_file_path = temp_file.name
                md.convert(temp_file_path).text_content
                text += md.convert(temp_file_path).text_content
                md_pages.append(text)

    return "\n\n---\n\n".join(md_pages)


class ToolCall:
    def __init__(self, id, fn, params):
        self.id = id
        self.fn = fn
        self.params = params

    def fn_str(self) -> str:
        return self.fn.__name__

    def params_str(self) -> str:
        return str(
            {
                name: val if len(val) <= 9 else f"{val[:3]}...{val[-3:]}"
                for name, val in self.params.items()
            }
        )

    def exec(self) -> str:
        return self.fn(**self.params)


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
            if name == "search_wiki":
                yield ToolCall(id, search_wiki, params)
            if name == "read_data":
                yield ToolCall(id, read_data, params)

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
