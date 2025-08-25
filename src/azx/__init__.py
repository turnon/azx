import json
import re
import traceback

from . import prompt
from . import arguments
from .agents import Client
from .configure import Configure
from .renderer import render_md_full, render_md_stream, render_user_input
from .storage import Store, history

config = Configure()
args = arguments.parse()


class Chat:
    def __init__(self):
        self.client = Client(**config.default_chat_model())
        self.session = prompt.session()
        self.store = None

    def run(self):
        while True:
            try:
                user_input = self.session.prompt()

                # handle command
                user_cmd = user_input.strip().lower()
                if user_cmd in ("/q", "/quit"):
                    break

                if self._other_command(user_cmd):
                    continue

                # handle chat
                if self.store is None:
                    self.store = Store()
                    self.store.log("system", config.default_chat_prompt())

                self.store.log("user", user_input)
                chunked_content, _ = self.client.stream_response(self.store.conversation)
                whole_output = render_md_stream(chunked_content)
                self.store.log("assistant", whole_output)
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()

    def _other_command(self, user_cmd):
        if match := re.match(r"^(?:/c|/client)$", user_cmd):
            render_md_full(f"clients:\n{config.models()}")
            return True

        if match := re.match(r"^(?:/c|/client) (.+)$", user_cmd):
            name = match.group(1)
            client2_cfg = config.find_model(name)
            if client2_cfg:
                self.client = Client(**client2_cfg)
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
                render_method = (
                    render_md_stream
                    if msg["role"] == "assistant"
                    else render_user_input
                )
                render_method(msg["content"])
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
    client = Client(**config.default_cli_ocr_model())

    try:
        result = client.ocr(args.files[0])
        if args.md:
            js = json.loads(result)
            return render_md_full(f"{js['abs']}\n\n{js['full']}")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


def main():
    if args.ocr:
        if not args.files:
            print("Error: --ocr-md or --ocr-json requires a file path argument")
            return
        return ocr()

    Chat().run()


if __name__ == "__main__":
    main()
