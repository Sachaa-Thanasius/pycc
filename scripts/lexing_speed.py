# ruff: noqa: T201, T203

import time
from pprint import pprint

from pycc.tokenizer import Tokenizer


class TimeCatch:
    elapsed: float

    def __init__(self):
        self.elapsed = 0.0

    def __enter__(self):
        self.elapsed = time.perf_counter()
        return self

    def __exit__(self, *_exc_info: object):
        self.elapsed = time.perf_counter() - self.elapsed


def lexing_example() -> None:
    with open("scripts/lexing_sample.c", encoding="utf-8") as fp:
        file_source = fp.read()
        file_name = fp.name

    tokenizer = Tokenizer(file_source, file_name)

    with TimeCatch() as tc:
        tokens = list(tokenizer)

    pprint(tokens)
    print("=" * 40)
    print(f"Time to lex: {tc.elapsed}")


if __name__ == "__main__":
    lexing_example()
