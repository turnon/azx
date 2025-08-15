from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

style = Style.from_dict(
    {
        "prompt": "ansigreen",  # Blue prompt text
        "": "ansigreen",  # Green input text
    }
)


def session() -> PromptSession:
    return PromptSession(">>> ", style=style)
