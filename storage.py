import datetime
import os

base_dir = os.path.expanduser("~/.azx")


class Store:
    def __init__(self):
        self.started_at = _now_str()
        self.ended_at = self.started_at
        self.conversation = []

    def log(self, role: str, msg: str):
        self.conversation.append({"role": role, "content": msg})

        session_dir = os.path.join(base_dir, self.started_at)
        os.makedirs(session_dir, exist_ok=True)

        self.ended_at = _now_str()
        with open(os.path.join(session_dir, f"{self.ended_at}.{role}.md"), "w") as f:
            f.write(msg)

    def resume(self, started_at: str):
        dir_path = os.path.join(base_dir, started_at)
        if not os.path.exists(dir_path):
            return []

        self.started_at = started_at
        self.conversation.clear()

        files = [
            f
            for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
            and (f.endswith("user.md") or f.endswith("assistant.md"))
        ]
        files.sort()

        for filename in files:
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    role = "user" if filename.endswith("user.md") else "assistant"
                    self.conversation.append({"role": role, "content": content})
            except Exception:
                continue

def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y_%m%d_%H%M%S")


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
