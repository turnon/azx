import re
import sys
from pathlib import Path


import yaml
from openai import OpenAI
from renderer import render
from storage import Store, history


class Client:
    def __init__(self, name: str, base_url: str, model: str, api_key: str):
        self.name = name
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def stream_response(self, messages: list[str]):
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )

        chunked_content = (
            chunk.choices[0].delta.content
            for chunk in stream
            if chunk.choices[0].delta.content
        )

        full_response = render(chunked_content)
        return full_response


def main():
    config_path = Path.home() / ".azx" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    first_key = config["keys"][0]
    client = Client(
        name=first_key["name"],
        base_url=first_key["base_url"],
        model=first_key["model"],
        api_key=first_key["api_key"],
    )

    store = Store()

    if not sys.stdin.isatty():
        content = sys.stdin.read().strip()
        if content:
            store.log("user", content)
            sys.stdin = open("/dev/tty")

    while True:
        try:
            user_input = input(">>> ")
            user_cmd = user_input.lower()
            if user_cmd in ("\q", "\quit"):
                break
            elif user_cmd in ("\h", "\hist", "\history"):
                render([history()])
                continue
            elif match := re.match(r"^(?:\\r|\\resume) (\d{4}_\d{4}_\d{6})$", user_cmd):
                store.resume(match.group(1))
                continue

            store.log("user", user_input)

            response = client.stream_response(store.conversation)
            store.log("assistant", response)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
