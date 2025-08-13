from itertools import tee

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

        stream1, stream2 = tee(stream)

        return (
            (
                chunk.choices[0].delta.content
                for chunk in stream1
                if chunk.choices[0].delta.content
            ),
            (
                chunk.choices[0].delta.tool_calls
                for chunk in stream2
                if chunk.choices[0].delta.tool_calls
            ),
        )
