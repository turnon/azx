import argparse


def parse():
    parser = argparse.ArgumentParser()

    parser.add_argument("--ocr", action="store_true", help="OCR.")
    parser.add_argument("--md", action="store_true", help="Enable Markdown output.")
    parser.add_argument("files", nargs="*", help="One or more file paths.")

    return parser.parse_args()
