from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

console = Console()


def render(stream) -> str:
    full_response = ""
    with Live(console=console, auto_refresh=False) as live:
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                markdown = Markdown(full_response)
                live.update(markdown)
                live.refresh()
    return full_response
