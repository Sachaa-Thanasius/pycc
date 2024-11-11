# ruff: noqa: T201
import sys
from collections.abc import Sequence


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print("Invalid number of arguments")
        return 1

    potential_num = argv[1]

    if not potential_num.isdigit():
        print("Given argument is not an integer")
        return 1

    if len(potential_num) > 100:
        print("Given argument is larger than 100 digits")
        return 1

    num = int(potential_num)

    print(".intel_syntax noprefix")
    print(".globl main")
    print("main:")
    print(f"    mov rax, {num}")
    print("    ret")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
