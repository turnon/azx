from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.theme import Theme

console = Console(theme=Theme({"markdown.hr": "medium_purple4"}))


def render(strings) -> str:
    whole_string = ""
    last_length = len(whole_string)

    with Live(console=console, auto_refresh=False, vertical_overflow="visible") as live:

        def refresh(content):
            markdown = Markdown(content)
            live.update(markdown)
            live.refresh()

        for string in strings:
            for i, line in enumerate(string.split("\n")):
                substring = f"\n{line}" if i > 0 else line
                whole_string += substring
                current_length = len(whole_string)
                if current_length - last_length > 5:
                    refresh(whole_string)
                    last_length = current_length

        refresh(whole_string)

    return whole_string
