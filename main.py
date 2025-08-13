import re
import sys
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
            if user_cmd in ("\q", "\quit"):
                break
            elif user_cmd in ("\h", "\hist", "\history"):
                render([history()])
                continue
            elif match := re.match(r"^(?:\\r|\\resume) (\d{4}_\d{4}_\d{6})$", user_cmd):
                store.resume(match.group(1))
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

            # handle chat
            store.log("user", user_input)
            chunked_output = client.stream_response(store.conversation)
            whole_output = render(chunked_output)
            store.log("assistant", whole_output)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
