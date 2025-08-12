from prompt_toolkit import PromptSession


def session() -> PromptSession:
    return PromptSession(">>> ")
