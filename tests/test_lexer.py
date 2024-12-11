from pprint import pprint

from pycc.lexer import Lexer


test_source = """\
int main(void) {
    return 1;
}
"""

my_lex = Lexer(test_source, "<string>")
pprint(list(my_lex.lex()))
