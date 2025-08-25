import argparse


def parse():
    parser = argparse.ArgumentParser()

    parser.add_argument("--ocr", action="store_true", help="OCR.")
    parser.add_argument("--models", action="store_true", help="List models")
    parser.add_argument("--model", type=str, help="Select a model", default=None)
    parser.add_argument("files", nargs="*", help="One or more file paths.")

    return parser.parse_args()
