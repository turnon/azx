import os
import re

from openai import OpenAI
from renderer import render
from storage import Store, history


def stream_response(client: OpenAI, messages: list[str]):
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
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
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=os.getenv("AZX_KEY")
    )
    store = Store()

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

            response = stream_response(client, store.conversation)
            store.log("assistant", response)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
