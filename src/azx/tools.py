import inspect

import yaml
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


class LocalTools:
    definitions = []


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
            return {"status": "error", "message": err}

        data = "".join([c.text for c in result.content if c.type == "text"])
        return {"status": "success", "message": data}


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
                name: val if len(val) <= 120 else f"{val[:58]}....{val[-58:]}"
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

    async def add_mcp(self, cmd, args):
        full_cmd = " ".join([cmd] + args)
        if full_cmd in self.mcps.items():
            return
        transport = StdioTransport(command=cmd, args=args)
        mcp = MCPClient(Client(transport))
        await mcp.__aenter__()
        self.mcps[full_cmd] = mcp

    async def del_mcp(self, cmd, args):
        full_cmd = " ".join([cmd] + args)
        mcp = self.mcps.get(full_cmd, None)
        if mcp is None:
            return
        del self.mcps[full_cmd]
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
