import re
import traceback
from pathlib import Path

import yaml

from . import prompt
from .agents import Client
from .renderer import render_md_stream, render_user_input
from .storage import Store, history


class CLI:
    def __init__(self):
        config_path = Path.home() / ".azx" / "config.yaml"
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.client = Client(**self.config["keys"][0])
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

                if self.store is None:
                    self.store = Store()
                    self.store.log("system", self.config.get("prompt", None))

                # handle chat
                self.store.log("user", user_input)
                chunked_content, _ = self.client.stream_response(self.store.conversation)
                whole_output = render_md_stream(chunked_content)
                self.store.log("assistant", whole_output)
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()

    def _other_command(self, user_cmd):
        if user_cmd in ("/?", "/help"):
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
                ]
            )
            render_md_stream([manual])
            return True

        if match := re.match(r"^(?:/c|/client)$", user_cmd):
            render_md_stream(
                "\n".join(
                    [f"{i + 1}. {k['name']}" for i, k in enumerate(self.config["keys"])]
                )
            )
            return True

        if match := re.match(r"^(?:/c|/client) (.+)$", user_cmd):
            name = match.group(1)
            client2_cfg = next(
                (
                    k
                    for i, k in enumerate(self.config["keys"])
                    if k["name"] == name or str(i + 1) == name
                ),
                None,
            )
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
            render_md_stream([history()])
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

        return False


def main():
    CLI().run()


if __name__ == "__main__":
    main()
