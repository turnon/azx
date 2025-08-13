import datetime
import os

base_dir = os.path.expanduser("~/.azx")


class Store:
    def __init__(self):
        self.started_at = _now_str()
        self.ended_at = self.started_at
        self.conversation = []

    def log(self, role: str, msg: str, flush=True):
        if not msg:
            return

        self.ended_at = _now_str()
        self.conversation.append({"role": role, "content": msg})

        os.makedirs(self._loc(), exist_ok=True)
        with open(os.path.join(self._loc(), f"{self.ended_at}.{role}.md"), "w") as f:
            f.write(msg)

    def summary(self, sum: str):
        with open(os.path.join(self._loc(), f"{self.ended_at}.sum.md"), "w") as f:
            f.write(sum)

    def sum_or_quest(self):
        def last_summary():
            files = [
                f
                for f in os.listdir(self._loc())
                if os.path.isfile(os.path.join(self._loc(), f)) and f.endswith("sum.md")
            ]

            if not files:
                return ""

            files.sort()

            with open(os.path.join(self._loc(), files[-1]), "r") as f:
                return f.read().strip()

        def first_question():
            if self.conversation:
                return self.conversation[0]["content"]

        return last_summary() or first_question() or "nothing"

    def resume(self, started_at: str):
        self.started_at = started_at

        dir_path = self._loc()
        if not os.path.exists(dir_path):
            return

        files = [
            f
            for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
            and (f.endswith("user.md") or f.endswith("assistant.md"))
        ]
        files.sort()

        if not files:
            return

        self.ended_at = os.path.basename(files[-1]).split(".")[0]
        self.conversation.clear()

        for filename in files:
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    _, role, _ = filename.split(".")
                    self.conversation.append({"role": role, "content": content})
            except Exception:
                continue

    def __str__(self):
        return f"**{self.started_at}** ~ **{self.ended_at}**: {self.sum_or_quest()}"

    def _loc(self) -> str:
        return os.path.join(base_dir, self.started_at)


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y_%m%d_%H%M%S")


def history() -> str:
    if not os.path.exists(base_dir):
        return "No history found."

    def resume(started_at: str) -> Store:
        store = Store()
        store.resume(started_at)
        return store

    stores = [
        resume(item)
        for item in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, item))
    ]

    stores.sort(key=lambda s: s.ended_at, reverse=True)

    items = [f"- {store}" for store in stores]

    return "\n".join(items) if items else "No history found."
