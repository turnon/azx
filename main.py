import os

from openai import OpenAI
from renderer import render
from storage import store, history


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
        base_url="https://openrouter.ai/api/v1", api_key=os.getenv("AZX_KEY")
    )
    conversation = []

    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ("\q", "\quit"):
                break
            elif user_input.lower() in ("\h", "\hist", "\history"):
                print(history())
                continue

            store("user", user_input)

            conversation.append({"role": "user", "content": user_input})
            response = stream_response(client, conversation)
            conversation.append({"role": "assistant", "content": response})
            store("ai", response)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
