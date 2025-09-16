from pathlib import Path

import yaml

sys_prompt = """
You are an assistant integrated with a chat loop that can call external functions to enhance responses.

When a function is called, it returns a JSON object with the following structure:

{
  "status": "success | error | partial",
  "message": "xxx", // If status is success, then message is primary result or response data. If status is error, then message is context or error explaination. If status is partial, then message is what to do next
}
""".strip()


class Configure:
    def __init__(self):
        config_path = Path.home() / ".azx" / "config.yaml"
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def models(self) -> str:
        return "\n".join(
            [f"{i + 1}. {k['name']}" for i, k in enumerate(self.config["keys"])]
        )

    def find_model(self, name_or_num) -> dict:
        for i, k in enumerate(self.config["keys"]):
            if k["name"] == name_or_num or str(i + 1) == name_or_num:
                return k
        return None

    def tools(self) -> str:
        return "\n".join(
            [f"{i + 1}. {k['name']}" for i, k in enumerate(self.config["mcp"])]
        )

    def find_tool(self, name_or_num) -> str:
        for i, k in enumerate(self.config["mcp"]):
            if k["name"] == name_or_num or str(i + 1) == name_or_num:
                return k
        return None

    def default_chat_model(self) -> dict:
        return self.config["keys"][0]

    def default_chat_prompt(self) -> dict:
        custom_prompt = self.config.get("prompt", None)
        if custom_prompt is None:
            return sys_prompt
        return f"{sys_prompt}\n\n{custom_prompt.strip()}"

    def default_cli_ocr_model(self) -> dict:
        for k in self.config["keys"]:
            if self.config["cli_ocr"] == k["name"]:
                return k
        return None
