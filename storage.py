import datetime
import os

base_dir = os.path.expanduser("~/.azx")
loaded_at = datetime.datetime.now().strftime("%Y_%m%d_%H%M%S")


def store(role: str, msg: str):
    session_dir = os.path.join(base_dir, loaded_at)
    os.makedirs(session_dir, exist_ok=True)

    now = datetime.datetime.now().strftime("%Y_%m%d_%H%M%S")
    msg = msg if msg.endswith("\n") else f"{msg}\n"
    with open(os.path.join(session_dir, f"{now}_{role}.md"), "w") as f:
        f.write(msg)


def history() -> str:
    if not os.path.exists(base_dir):
        return "No history found."

    subdirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            subdirs.append(item)

    subdirs.sort(reverse=True)

    markdown_list = []
    for subdir in subdirs:
        subdir_path = os.path.join(base_dir, subdir)
        files = [
            f
            for f in os.listdir(subdir_path)
            if os.path.isfile(os.path.join(subdir_path, f))
        ]

        if files:
            files.sort()
            first_file = files[0]
            file_path = os.path.join(subdir_path, first_file)

            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    markdown_list.append(f"- **{subdir}**: {content}")
            except Exception as e:
                markdown_list.append(f"- **{subdir}**: [Error reading file: {e}]")

    return "\n".join(markdown_list) if markdown_list else "No history found."
