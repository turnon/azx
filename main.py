from openai import OpenAI
import os


def stream_response(client, messages):
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=messages,
        stream=True,
    )
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
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
