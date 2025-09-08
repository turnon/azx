import inspect
import os
import re
import shutil

import yaml
from markitdown import MarkItDown
from fastmcp import Client


class LocalTools:
    definitions = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read data from a local file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "path to a local file",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
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
        {
            "type": "function",
            "function": {
                "name": "remove_file",
                "description": "Remove a local file, after user approval",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "path to a local file to remove",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_dir",
                "description": "Create a local directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "path to a local directory to create",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_dir",
                "description": "Read directory structure like tree command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "path to a local directory to read",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_dir",
                "description": "Remove a local directory, after user approval",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "path to a local directory to remove",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_files",
                "description": "Search for a pattern in a file using regular expressions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "path to a local file or directory to search in",
                        },
                        "regexp": {
                            "type": "string",
                            "description": "regular expression pattern to search for",
                        },
                    },
                    "required": ["path", "regexp"],
                },
            },
        },
    ]

    @staticmethod
    def read_file(path) -> dict:
        try:
            content = MarkItDown().convert(path).text_content
            return {"status": "success", "data": content, "err": None, "proceed": None}
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}

    @staticmethod
    def write_file(path, data) -> dict:
        try:
            with open(path, "w") as f:
                f.write(data)
            return {"status": "success", "data": None, "err": None, "proceed": None}
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}

    @staticmethod
    def remove_file(path) -> dict:
        try:
            os.remove(path)
            return {"status": "success", "data": None, "err": None, "proceed": None}
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}

    @staticmethod
    def create_dir(path) -> dict:
        try:
            os.makedirs(path, exist_ok=True)
            return {"status": "success", "data": None, "err": None, "proceed": None}
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}

    @staticmethod
    def read_dir(path) -> dict:
        try:
            tree_output = []

            def generate_tree(directory, prefix=""):
                try:
                    items = sorted(os.listdir(directory))
                    items = [item for item in items if not item.startswith(".")]
                except PermissionError:
                    tree_output.append(f"{prefix}[Permission Denied]")
                    return

                for i, item in enumerate(items):
                    item_path = os.path.join(directory, item)
                    is_last = i == len(items) - 1

                    if is_last:
                        tree_output.append(f"{prefix}└── {item}")
                        new_prefix = prefix + "    "
                    else:
                        tree_output.append(f"{prefix}├── {item}")
                        new_prefix = prefix + "│   "

                    if os.path.isdir(item_path):
                        generate_tree(item_path, new_prefix)

            if not os.path.exists(path):
                return {
                    "status": "error",
                    "data": None,
                    "err": "Directory does not exist",
                    "proceed": None,
                }

            if not os.path.isdir(path):
                return {
                    "status": "error",
                    "data": None,
                    "err": "Path is not a directory",
                    "proceed": None,
                }

            tree_output.append(os.path.basename(os.path.abspath(path)) or path)
            generate_tree(path)

            return {
                "status": "success",
                "data": "\n".join(tree_output),
                "err": None,
                "proceed": None,
            }
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}

    @staticmethod
    def remove_dir(path) -> dict:
        try:
            shutil.rmtree(path)
            return {"status": "success", "data": None, "err": None, "proceed": None}
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}

    @staticmethod
    def grep_files(path, regexp) -> dict:
        def get_files(path):
            if os.path.isfile(path):
                yield path
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        yield os.path.join(root, file)

        def grep_file(path, pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.search(line):
                            yield f"{file_path}:{line_num}: {line.rstrip()}"
            except (UnicodeDecodeError, PermissionError):
                pass

        try:
            pattern = re.compile(regexp)
            matched_lines = []

            for file_path in get_files(path):
                for line in grep_file(file_path, pattern):
                    matched_lines.append(line)

            return {
                "status": "success",
                "data": "\n".join(matched_lines) if matched_lines else "",
                "err": None,
                "proceed": None,
            }
        except Exception as e:
            return {"status": "error", "data": None, "err": str(e), "proceed": None}


class MCPClient:
    def __init__(self, mcp: Client):
        self.client = mcp
        self.specs = None

    async def __aenter__(self):
        await self.client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self):
        if self.specs is None:
            tools = await self.client.list_tools()
            self.specs = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    },
                }
                for t in tools
            ]
        return self.specs

    async def call_tool(self, name, params):
        result = await self.client.call_tool(name, params, raise_on_error=False)
        if result.is_error:
            err = result.content[0].text
            return {"status": "error", "data": None, "err": err, "proceed": None}

        data = "".join([c.text for c in result.content if c.type == "text"])
        return {"status": "success", "data": data, "err": None, "proceed": None}


class Call:
    def __init__(self, id, fn, params):
        self.id = id
        self.fn = fn
        self.params = params

    def params_str(self) -> str:
        def stringified_value():
            for name, val in self.params.items():
                yield name, str(val)

        return str(
            {
                name: val if len(val) <= 60 else f"{val[:28]}....{val[-28:]}"
                for name, val in stringified_value()
            }
        )


class Calls:
    def __init__(self, stream):
        self.stream = stream
        self.consumed = False
        self.buffer = None

    def __len__(self) -> int:
        return len(self._consume())

    def __iter__(self):
        for id, name, args in self._func_args():
            params = None
            try:
                params = yaml.load(args, yaml.CLoader)
            except Exception as e:
                print(args)
                raise e
            yield Call(id, name, params)

    def __str__(self) -> str:
        self._consume()
        return ";".join([f"{name}({args})" for _, name, args in self._func_args()])

    def _func_args(self):
        for fn_call in self._consume().values():
            yield (fn_call["id"], fn_call["fn"]["name"], fn_call["fn"]["args"])

    def _consume(self):
        if self.buffer is None:
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


class Tools:
    def __init__(self):
        self.mcps: dict[str, MCPClient] = {}

    async def add_mcp(self, transport):
        if transport in self.mcps.items():
            return
        mcp = MCPClient(Client(transport))
        await mcp.__aenter__()
        self.mcps[transport] = mcp

    async def del_mcp(self, transport):
        mcp = self.mcps.get(transport, None)
        if mcp is None:
            return
        del self.mcps[transport]
        await mcp.__aexit__(None, None, None)

    async def specs(self) -> list:
        defs = [] + LocalTools.definitions
        for _, mcp in self.mcps.items():
            defs += await mcp.list_tools()
        return defs

    async def execute(self, call: Call) -> dict:
        for _, mcp in self.mcps.items():
            for mcp_tool in await mcp.list_tools():
                if mcp_tool["function"]["name"] == call.fn:
                    return await mcp.call_tool(call.fn, call.params)

        method = getattr(LocalTools, call.fn)
        valid_params = inspect.signature(method).parameters.keys()
        filtered_params = {k: v for k, v in call.params.items() if k in valid_params}
        return method(**filtered_params)
