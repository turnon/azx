import asyncio
import json
import re
import time
import traceback

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

config = Configure()
args = arguments.parse()


class Chat:
    def __init__(self):
        self.model = config.default_chat_model()
        self.tools = Tools()
        self.session = prompt.session()
        self.store = None

    async def run(self):
        await self._new_client()

        while True:
            try:
                user_input = await self.session.prompt_async()

                # handle command
                user_cmd = user_input.strip().lower()
                if user_cmd in ("/q", "/quit"):
                    break

                if await self._other_command(user_cmd):
                    continue

                # handle chat
                if self.store is None:
                    self.store = Store()
                    self.store.log("system", config.default_chat_prompt())

                self.store.log("user", user_input)

                while True:
                    content, tool_calls, usage = self.client.stream_response(
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
                    self._auto_compact(usage)
                    if not len(calls):
                        break

            except Exception as e:
                render_error(f"Error: {e}\n{traceback.format_exc()}")

    def _auto_compact(self, usage):
        self.store.usage = next(usage, 0).total_tokens
        while self.store.usage > (self.model.get("window", 4096) * 0.9):
            content, tools, usage = self.client.stream_response(
                self.store.compaction(),
                json=True,
            )
            print("<<< taking note ...")
            whole_output = render_md_stream(content)
            for _ in tools:
                pass
            token_used = next(usage, 0).completion_tokens
            print(f"<<< note taken: {token_used}/{self.store.usage}")
            if len(whole_output) == 0:
                time.sleep(1)
                continue
            self.store.usage = token_used
            self.store.note(whole_output)

    async def _new_client(self):
        conn_keys = ["name", "base_url", "model", "api_key"]
        conn_kv = {k: self.model[k] for k in self.model if k in conn_keys}
        self.client = Client(**(conn_kv | {"tools": await self.tools.specs()}))

    async def _other_command(self, user_cmd):
        if match := re.match(r"^(?:/c|/client)$", user_cmd):
            render_md_full(f"clients:\n{config.models()}")
            return True

        if match := re.match(r"^(?:/c|/client) (.+)$", user_cmd):
            name = match.group(1)
            client2_cfg = config.find_model(name)
            if client2_cfg:
                self.model = client2_cfg
                await self._new_client()
                print(f"Switched to client: {client2_cfg['name']}")
            else:
                print(f"Client '{name}' not found in config")
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

        if match := re.match(r"^(?:/t|/tool)\+ (.+)$", user_cmd):
            await self.tools.add_mcp(match.group(1))
            await self._new_client()
            return True

        if match := re.match(r"^(?:/t|/tool)\- (.+)$", user_cmd):
            await self.tools.del_mcp(match.group(1))
            await self._new_client()
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
