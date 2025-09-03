import asyncio
import json
import re
import traceback

from contextlib import AsyncExitStack

from . import prompt
from . import arguments
from .agents import Client
from .configure import Configure
from .renderer import (
    render_error,
    render_md_full,
    render_md_stream,
    render_tool_call,
    render_user_input,
)
from .storage import Store, history
from .tools import Calls, Tools

from fastmcp import Client as MCPClient

config = Configure()
args = arguments.parse()


class Chat:
    def __init__(self):
        self.model = config.default_chat_model()
        self.mcps = []
        self.session = prompt.session()
        self.store = None

    async def run(self):
        while True:
            async with AsyncExitStack() as stack:
                mcp_clients = await asyncio.gather(
                    *[stack.enter_async_context(MCPClient(mcp)) for mcp in self.mcps]
                )
                if await self._run(mcp_clients):
                    return
                continue

    async def _run(self, mcp_clients):
        self.tools = Tools()
        for mcp in mcp_clients:
            self.tools.add_mcp(mcp)
        self.client = Client(**(self.model | {"tools": await self.tools.specs()}))

        while True:
            try:
                user_input = await self.session.prompt_async()

                # handle command
                user_cmd = user_input.strip().lower()
                if user_cmd in ("/q", "/quit"):
                    return True

                if self._change_env(user_cmd):
                    return False

                if self._other_command(user_cmd):
                    continue

                # handle chat
                if self.store is None:
                    self.store = Store()
                    self.store.log("system", config.default_chat_prompt())

                self.store.log("user", user_input)

                while True:
                    content, tool_calls = self.client.stream_response(
                        self.store.conversation
                    )
                    whole_output = render_md_stream(content)
                    self.store.log("assistant", whole_output)
                    calls = Calls(tool_calls)
                    for call in calls:
                        render_tool_call(f"{call.fn}({call.params_str()})")
                        self.store.tool(
                            call.id,
                            call.fn,
                            call.params_str(),
                            await self.tools.execute(call),
                        )
                    if not len(calls):
                        break

            except Exception as e:
                render_error(f"Error: {e}\n{traceback.format_exc()}")

    def _change_env(self, user_cmd):
        if match := re.match(r"^(?:/c|/client) (.+)$", user_cmd):
            name = match.group(1)
            client2_cfg = config.find_model(name)
            if client2_cfg:
                self.model = client2_cfg
                print(f"Switched to client: {client2_cfg['name']}")
            else:
                print(f"Client '{name}' not found in config")
            return True

        if match := re.match(r"^(?:/t|/tool)\+ (.+)$", user_cmd):
            self.mcps = list({i for i in (self.mcps + [match.group(1)])})
            return True

        if match := re.match(r"^(?:/t|/tool)\- (.+)$", user_cmd):
            self.mcps.remove(match.group(1))
            return True

        return False

    def _other_command(self, user_cmd):
        if match := re.match(r"^(?:/c|/client)$", user_cmd):
            render_md_full(f"clients:\n{config.models()}")
            return True

        if user_cmd in ("/n", "/new"):
            self.store = None
            return True

        if match := re.match(r"^(?:/r|/resume)$", user_cmd):
            render_md_full(f"history:\n{history()}")
            return True

        if match := re.match(r"^(?:/r|/resume) (.+)$", user_cmd):
            started_at = (
                history().split("\n")[int(match.group(1)) - 1].split(" ")[1].strip("*")
            )
            self.store = Store()
            self.store.resume(started_at)
            for msg in self.store.conversation:
                if msg["role"] == "user":
                    render_user_input(msg["content"])
                elif msg["role"] == "assistant":
                    render_md_stream(msg["content"])
                    for fn in msg.get("tool_calls", []):
                        render_tool_call(
                            f"{fn['function']['name']}({fn['function']['arguments']})"
                        )
            return True

        if user_cmd in ("/s", "/sum", "/summary"):
            talk = self.store.conversation.copy()
            talk.append(
                {
                    "role": "user",
                    "content": "Summarize all talk above briefly, use single language, which is the primary language involved, with words or phrases, in one line. Your answer could contain verb/object/attribute/adverbial/complement, but no subject. Just give me the answer, no thought is need",
                }
            )
            chunked_sum, _ = self.client.stream_response(talk)
            sum = "".join(list(chunked_sum))
            self.store.summary(sum)
            render_md_stream([sum])
            return True

        if user_cmd in ("/?", "/help") or re.match(r"^/[a-zA-Z0-9]+$", user_cmd):
            manual = "\n".join(
                [
                    f"- {cmd}"
                    for cmd in [
                        "/? /help",
                        "/c /client",
                        "/n /new",
                        "/r /resume",
                        "/s /sum /summary",
                        "/q /quit",
                    ]
                ],
            )
            render_md_full(f"commands:\n{manual}")
            return True

        return False


def ocr():
    model_cfg = (
        config.find_model(args.model) if args.model else config.default_cli_ocr_model()
    )
    client = Client(**model_cfg)
    result = None

    try:
        result = client.ocr(args.files[0])
    except Exception as e:
        print(f"Fail to OCR: {e}")
        traceback.print_exc()

    try:
        js = json.loads(result)
        print(f"{js['abstract']}\n\n{js['full']}")
    except Exception as e:
        print(f"Fail to parse as json: {e}\n\n{result}")
        traceback.print_exc()


def main():
    if args.models:
        return render_md_full(f"clients:\n{config.models()}")

    if args.ocr:
        if not args.files:
            print("Error: --ocr-md or --ocr-json requires a file path argument")
            return
        return ocr()

    asyncio.run(Chat().run())


if __name__ == "__main__":
    main()
