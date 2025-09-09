import datetime
import json
import os
import re

base_dir = os.path.expanduser("~/.azx")


class Store:
    tool_status_map = {"success": "data", "error": "err", "partial": "proceed"}

    def __init__(self):
        self.started_at = _now_str()
        self.ended_at = self.started_at
        self.progress = 0
        self.conversation = []
        self.usage = 0

    def tool(self, id: str, name: str, args: str, ret: dict):
        self._add_tool_to_last_assistant_msg(id, name, args)
        self.ended_at = _now_str()
        self.conversation.append(
            {
                "role": "tool",
                "tool_call_id": id,
                "name": name,
                "content": json.dumps(ret),
            }
        )

        status = ret["status"]
        msg = ret[self.tool_status_map[status]]

        os.makedirs(self._loc(), exist_ok=True)
        with open(self._log_path("tool"), "w") as f:
            f.write("\n".join([id, name, args, status, msg]))

    def log(self, role: str, msg: str):
        self.ended_at = _now_str()
        self.conversation.append({"role": role, "content": msg})

        os.makedirs(self._loc(), exist_ok=True)
        with open(self._log_path(role), "w") as f:
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
            for speak in self.conversation:
                if speak["role"] == "user":
                    return speak["content"]

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
            and (
                f.endswith("user.md")
                or f.endswith("system.md")
                or f.endswith("assistant.md")
                or f.endswith("tool.md")
            )
        ]
        files.sort()

        if not files:
            return

        self.ended_at = os.path.basename(files[-1]).split(".")[0]
        self.progress = len(files)
        self.conversation.clear()

        for filename in files:
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, "r") as f:
                    segments = filename.split(".")
                    role = segments[-2]
                    if role == "tool":
                        fn_id = f.readline().strip()
                        fn_name = f.readline().strip()
                        fn_args = f.readline().strip()
                        content = {
                            "status": None,
                            "data": None,
                            "err": None,
                            "proceed": None,
                        }
                        fn_status = f.readline().strip()
                        fn_msg = f.read().strip()
                        content["status"] = fn_status
                        content[self.tool_status_map[fn_status]] = fn_msg
                        self.tool_status_map[fn_status]
                        self._add_tool_to_last_assistant_msg(fn_id, fn_name, fn_args)
                        self.conversation.append(
                            {
                                "role": role,
                                "tool_call_id": fn_id,
                                "name": fn_name,
                                "content": json.dumps(content),
                            }
                        )
                    else:
                        self.conversation.append(
                            {"role": role, "content": f.read().strip()}
                        )
            except Exception:
                continue

    def __str__(self):
        return f"**{self.started_at}** ~ **{self.ended_at}**: {self.sum_or_quest()}"

    def _loc(self) -> str:
        return os.path.join(base_dir, self.started_at)

    def _log_path(self, role) -> str:
        file_name = f"{self.ended_at}.{self.progress}.{role}.md"
        full_path = os.path.join(self._loc(), file_name)
        self.progress += 1
        return full_path

    def _add_tool_to_last_assistant_msg(self, id, name, args):
        last_msg = next(
            (msg for msg in reversed(self.conversation) if msg["role"] == "assistant"),
            None,
        )

        if "tool_calls" not in last_msg:
            last_msg["tool_calls"] = []

        last_msg["tool_calls"].append(
            {
                "id": id,
                "type": "function",
                "function": {"name": name, "arguments": args},
            }
        )


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
        and re.match(r"^\d{4}_\d{4}_\d{6}$", item)
    ]

    stores.sort(key=lambda s: s.ended_at)

    items = [f"{i + 1}. {store}" for i, store in enumerate(stores)]

    return "\n".join(items) if items else "No history found."
