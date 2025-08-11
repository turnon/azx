from openai import OpenAI
import os


def stream_response(client, prompt):
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


def main():
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=os.getenv("CLASSMATE_KEY")
    )

    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ("exit", "quit"):
                break

            stream_response(client, user_input)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
