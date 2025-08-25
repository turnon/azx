from pathlib import Path

import yaml


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

    def default_chat_model(self) -> dict:
        return self.config["keys"][0]

    def default_chat_prompt(self) -> dict:
        return self.config.get("prompt", None)

    def default_cli_ocr_model(self) -> dict:
        for k in self.config["keys"]:
            if self.config["cli_ocr"] == k["name"]:
                return k
        return None
