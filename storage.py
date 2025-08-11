import datetime
import os

base_dir = os.path.expanduser("~/.azx")
loaded_at = datetime.datetime.now().strftime("%Y_%m%d_%H%M%S")


def store(role: str, msg: str):
    session_dir = os.path.join(base_dir, loaded_at)
    os.makedirs(session_dir, exist_ok=True)

    now = datetime.datetime.now().strftime("%Y_%m%d_%H%M%S")
    msg = msg if msg.endswith('\n') else f"{msg}\n"
    with open(os.path.join(session_dir, f"{now}_{role}.md"), "w") as f:
        f.write(msg)
