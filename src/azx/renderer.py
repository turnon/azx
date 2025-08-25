from markdown_it import MarkdownIt
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from rich.theme import Theme

console = Console(theme=Theme({"markdown.hr": "medium_purple4"}))


def render_user_input(string):
    text = Text(f">>> {string}")
    text.stylize("green")
    console.print(text)


def render_md_full(string):
    console.print(Markdown(string))


def render_md_stream(strings) -> str:
    whole_string = ""
    current_block = ""

    def flatten_strings():
        for string in strings:
            for char in string:
                yield char

    def block_recognized():
        nonlocal current_block
        md = MarkdownIt("js-default")
        tokens_len = 0
        for char in flatten_strings():
            current_block += char
            tokens = md.parse(current_block)
            new_block = (
                tokens_len != len(tokens)
                and current_block[-3:][:2] == "\n\n"
                and char not in "-*123456789|"
            )
            tokens_len = len(tokens)
            yield (char, new_block)

    def new_live() -> Live:
        live = Live(console=console, refresh_per_second=25)
        live.start()
        return live

    live = new_live()

    for char, new_block in block_recognized():
        if new_block:
            current_block = char
            live.stop()
            console.print("")
            live = new_live()

        whole_string += char
        live.update(Markdown(current_block))

    live.stop()

    return whole_string
