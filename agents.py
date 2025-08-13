from openai import OpenAI


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

        return (
            chunk.choices[0].delta.content
            for chunk in stream
            if chunk.choices[0].delta.content
        )
