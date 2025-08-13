import re
import sys
import traceback
from pathlib import Path

import yaml

import prompt
from agents import Client
from renderer import render
from storage import Store, history


def main():
    config_path = Path.home() / ".azx" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    client_cfg = config["keys"][0]
    client = Client(**client_cfg)

    store = Store()

    sys_prompt = config.get("prompt", None)
    if sys_prompt:
        store.log("system", sys_prompt)

    if not sys.stdin.isatty():
        content = sys.stdin.read().strip()
        if content:
            store.log("user", content)
            sys.stdin = open("/dev/tty")

    session = prompt.session()

    while True:
        try:
            user_input = session.prompt()

            # handle command
            user_cmd = user_input.lower()
            if user_cmd in ("\?", "\help"):
                manual = "\n".join(
                    [
                        f"- {cmd}"
                        for cmd in [
                            "\? \help",
                            "\c \client",
                            "\h \hist \history",
                            "\\r \\resume",
                            "\s \sum \summary",
                            "\q \quit",
                        ]
                    ]
                )
                render([manual])
                continue
            elif match := re.match(r"^(?:\\c|\\client) (.+)$", user_cmd):
                name = match.group(1)
                client2_cfg = next(
                    (k for k in config["keys"] if k["name"] == name), None
                )
                if client2_cfg:
                    client = Client(**client2_cfg)
                    print(f"Switched to client: {name}")
                else:
                    print(f"Client '{name}' not found in config")
                continue
            elif user_cmd in ("\h", "\hist", "\history"):
                render([history()])
                continue
            elif match := re.match(r"^(?:\\r|\\resume) (\d{4}_\d{4}_\d{6})$", user_cmd):
                store.resume(match.group(1))
                continue
            elif user_cmd in ("\s", "\sum", "\summary"):
                talk = store.conversation.copy()
                talk.append(
                    {
                        "role": "user",
                        "content": "Summarize all talk above briefly, use single language, which is the primary language involved, with words or phrases, in one line. Your answer could contain verb/object/attribute/adverbial/complement, but no subject. Just give me the answer, no thought is need",
                    }
                )
                sum = "".join(list(client.stream_response(talk)))
                store.summary(sum)
                render([sum])
                continue
            elif user_cmd in ("\q", "\quit"):
                break

            # handle chat
            store.log("user", user_input)
            chunked_output = client.stream_response(store.conversation)
            whole_output = render(chunked_output)
            store.log("assistant", whole_output)
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
