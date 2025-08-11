from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

console = Console()


def render(strings) -> str:
    full_response = ""
    with Live(console=console, auto_refresh=False) as live:
        for string in strings:
            full_response += string
            markdown = Markdown(full_response)
            live.update(markdown)
            live.refresh()
    return full_response
