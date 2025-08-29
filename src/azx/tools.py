import json
import tempfile

import requests
from markitdown import MarkItDown

definitions = [
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
            "description": "Read data from a local file",
            "parameters": {
                "type": "object",
                "properties": {
                    "uri": {
                        "type": "string",
                        "description": "path to a local file",
                    },
                },
                "required": ["uri"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_data",
            "description": "Write data to local file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "path to a local file",
                    },
                    "data": {
                        "type": "string",
                        "description": "data to write",
                    },
                },
                "required": ["path"],
            },
        },
    },
]


def read_data(uri) -> dict:
    try:
        content = MarkItDown().convert(uri).text_content
        return {"status": "success", "data": content, "err": None, "proceed": None}
    except Exception as e:
        return {"status": "error", "data": None, "err": str(e), "proceed": None}


def write_data(path, data) -> dict:
    try:
        with open(path, "w") as f:
            f.write(data)
        # lines = sum(1 for c in data if c == "\n")
        # result = f"Successfully wrote {lines} line{'s' if lines > 1 else ''}"
        return {"status": "success", "data": None, "err": None, "proceed": None}
    except Exception as e:
        # result = f"Failed to write because: {e}"
        return {"status": "error", "data": None, "err": str(e), "proceed": None}


def search_wiki(keyword) -> dict:
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

    return {
        "status": "success",
        "data": "\n\n---\n\n".join(md_pages),
        "err": None,
        "proceed": None,
    }


class Call:
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
        return json.dumps(self.fn(**self.params))


class Calls:
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
                yield Call(id, search_wiki, params)
            if name == "read_data":
                yield Call(id, read_data, params)
            if name == "write_data":
                yield Call(id, write_data, params)

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
