import os

from openai import OpenAI
from renderer import render


def stream_response(client: OpenAI, messages: list[str]):
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=messages,
        stream=True,
    )
    full_response = render(stream)
    return full_response


def main():
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=os.getenv("CLASSMATE_KEY")
    )
    conversation = []

    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ("exit", "quit"):
                break

            conversation.append({"role": "user", "content": user_input})
            response = stream_response(client, conversation)
            conversation.append({"role": "assistant", "content": response})
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
