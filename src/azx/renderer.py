from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

console = Console()


def render(strings) -> str:
    whole_string = ""
    last_length = len(whole_string)

    with Live(console=console, auto_refresh=False) as live:

        def refresh(content):
            markdown = Markdown(content)
            live.update(markdown)
            live.refresh()

        for string in strings:
            whole_string += string
            current_length = len(whole_string)
            if current_length - last_length > 5:
                refresh(whole_string)
                last_length = current_length

        refresh(whole_string)

    return whole_string
