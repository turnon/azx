import re
import sys
import traceback
from pathlib import Path

import yaml

import prompt
from agents import Client
from renderer import render
from storage import Store, history


class CLI:
    def __init__(self):
        config_path = Path.home() / ".azx" / "config.yaml"
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.client = Client(**self.config["keys"][0])

        self.store = Store()
        self.store.log("system", self.config.get("prompt", None))

        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
            if content:
                self.store.log("user", content)
                sys.stdin = open("/dev/tty")

        self.session = prompt.session()

    def run(self):
        while True:
            try:
                user_input = self.session.prompt()

                # handle command
                user_cmd = user_input.lower()
                if user_cmd in ("/q", "/quit"):
                    break

                if self._other_command(user_cmd):
                    continue

                # handle chat
                self.store.log("user", user_input)
                chunked_content, _ = self.client.stream_response(self.store.conversation)
                whole_output = render(chunked_content)
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
                        "/h /hist /history",
                        "/n /new",
                        "/r /resume",
                        "/s /sum /summary",
                        "/q /quit",
                    ]
                ]
            )
            render([manual])
            return True

        if match := re.match(r"^(?:/c|/client) (.+)$", user_cmd):
            name = match.group(1)
            client2_cfg = next(
                (k for k in self.config["keys"] if k["name"] == name), None
            )
            if client2_cfg:
                self.client = Client(**client2_cfg)
                print(f"Switched to client: {name}")
            else:
                print(f"Client '{name}' not found in config")
            return True

        if user_cmd in ("/h", "/hist", "/history"):
            render([history()])
            return True

        if user_cmd in ("/n", "/new"):
            self.store = Store()
            self.store.log("system", self.config.get("prompt", None))
            return True

        if match := re.match(r"^(?:/r|/resume) (\d{4}_\d{4}_\d{6})$", user_cmd):
            self.store = Store()
            self.store.resume(match.group(1))
            return True

        if user_cmd in ("/s", "/sum", "/summary"):
            talk = self.store.conversation.copy()
            talk.append(
                {
                    "role": "user",
                    "content": "Summarize all talk above briefly, use single language, which is the primary language involved, with words or phrases, in one line. Your answer could contain verb/object/attribute/adverbial/complement, but no subject. Just give me the answer, no thought is need",
                }
            )
            sum = "".join(list(self.client.stream_response(talk)))
            self.store.summary(sum)
            render([sum])
            return True

        return False


def main():
    CLI().run()


if __name__ == "__main__":
    main()
