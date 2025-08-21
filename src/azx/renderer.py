from markdown_it import MarkdownIt
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.theme import Theme

console = Console(theme=Theme({"markdown.hr": "medium_purple4"}))


def render(strings) -> str:
    whole_string = ""
    current_block = ""

    def flatten_strings():
        for string in strings:
            for char in string:
                yield char

    def block_recognized():
        nonlocal whole_string
        md = MarkdownIt("js-default")
        tokens_len = 0
        for char in flatten_strings():
            whole_string += char
            tokens = md.parse(whole_string)
            new_block = tokens_len != len(tokens) and whole_string[-3:][:2] == "\n\n"
            tokens_len = len(tokens)
            yield (char, new_block)

    def new_live() -> Live:
        live = Live(console=console, auto_refresh=False)
        live.start()
        return live

    live = new_live()

    for char, new_block in block_recognized():
        if new_block:
            current_block = ""
            live.stop()
            live = new_live()

        current_block += char
        live.update(Markdown(current_block))
        live.refresh()

    live.stop()

    return whole_string
