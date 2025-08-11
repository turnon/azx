import os

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

console = Console()

def stream_response(client, messages):
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=messages,
        stream=True,
    )
    full_response = ""
    with Live(console=console, auto_refresh=False) as live:
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                markdown = Markdown(full_response)
                live.update(markdown)
                live.refresh()
    print()
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
