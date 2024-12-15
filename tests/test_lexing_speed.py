import time
from pprint import pprint

from pycc.lexer import Lexer


class TimeCatch:
    elapsed: float

    def __init__(self):
        self.elapsed = 0.0

    def __enter__(self):
        self.elapsed = time.perf_counter()
        return self

    def __exit__(self, *_exc_info: object):
        self.elapsed = time.perf_counter() - self.elapsed


test_source = """\
#include <stdio.h>
int main() {
    int a;
    long b;   // equivalent to long int b;
    long long c;  // equivalent to long long int c;
    double e;
    long double f;

    printf("Size of int = %zu bytes \n", sizeof(a));
    printf("Size of long int = %zu bytes\n", sizeof(b));
    printf("Size of long long int = %zu bytes\n", sizeof(c));
    printf("Size of double = %zu bytes\n", sizeof(e));
    printf("Size of long double = %zu bytes\n", sizeof(f));
    
    return 0;
}
"""


def test_lexing_example():
    lexer = Lexer(test_source, "<string>")
    with TimeCatch() as tc:
        tokens = list(lexer.lex())

    print(f"Time to lex: {tc.elapsed}")
    print("=" * 40)
    pprint(tokens)

if __name__ == "__main__":
    test_lexing_example()