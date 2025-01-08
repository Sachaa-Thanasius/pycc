# ruff: noqa: ERA001, T201, T203

import time
from pprint import pprint

from pycp.preprocessor import Preprocessor
from pycp.tokenizer import Tokenizer


class TimeCatcher:
    elapsed: float

    def __init__(self):
        self.elapsed = 0.0

    def __enter__(self):
        self.elapsed = time.perf_counter()
        return self

    def __exit__(self, *_exc_info: object):
        self.elapsed = time.perf_counter() - self.elapsed


def tokenizing_example() -> None:
    with open("scripts/sample.c", encoding="utf-8") as fp:
        file_source = fp.read()
        file_name = fp.name

    tokenizer = Tokenizer(file_source, file_name)

    with TimeCatcher() as tc:
        raw_tokens = list(tokenizer)

    pprint(raw_tokens)
    print("=" * 40)
    print(f"Time to tokenize: {tc.elapsed}")

    print("=" * 40)
    print("".join(t.value for t in raw_tokens))
    print("\n")


def preprocessing_example() -> None:
    with open("scripts/sample.c", encoding="utf-8") as fp:
        file_source = fp.read()
        file_name = fp.name

    tokenizer = Tokenizer(file_source, file_name)
    preprocessor = Preprocessor(tokenizer)
    preprocessor.ignore_missing_includes = True

    with TimeCatcher() as tc:
        post_pp_tokens = list(preprocessor)

    pprint(post_pp_tokens)
    print("=" * 40)
    print(f"Time to tokenize + preprocess: {tc.elapsed}")

    # print("=" * 40)
    # print(" ".join(t.value for t in post_pp_tokens))
    # print("\n")


def main() -> None:
    tokenizing_example()
    preprocessing_example()


if __name__ == "__main__":
    main()
