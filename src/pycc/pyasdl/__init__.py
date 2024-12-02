# -------------------------------------------------------------------------------
# Parser for ASDL [1] definition files. Reads in an ASDL description and parses
# it into an AST that describes it.
#
# The EBNF we're parsing here: Figure 1 of the paper [1]. Extended to support
# modules and attributes after a product. Words starting with Capital letters
# are terminals. Literal tokens are in "double quotes". Others are
# non-terminals. Id is either TokenId or ConstructorId.
#
# module        ::= "module" Id "{" [definitions] "}"
# definitions   ::= { TypeId "=" type }
# type          ::= product | sum
# product       ::= fields ["attributes" fields]
# fields        ::= "(" { field, "," } field ")"
# field         ::= TypeId ["?" | "*"] [Id]
# sum           ::= constructor { "|" constructor } ["attributes" fields]
# constructor   ::= ConstructorId [fields]
#
# [1] "The Zephyr Abstract Syntax Description Language" by Wang, et. al. See
#     http://asdl.sourceforge.net/
# -------------------------------------------------------------------------------
from __future__ import annotations

from collections.abc import Generator
from typing import Any, Optional, Union

from .ast import AST, Constructor, Field, Module, NodeVisitor, Product, Sum, Type
from .errors import ASDLSyntaxError
from .tokenize import Token, TokenKind, tokenize_asdl


__all__ = [
    "builtin_types",
    "parse",
    "Check",
    "check",
]


builtin_types = {"identifier", "string", "int", "constant"}


class Check(NodeVisitor):
    """A visitor that checks a parsed ASDL tree for correctness.

    Errors are printed and accumulated.
    """

    def __init__(self):
        super().__init__()
        self.cons: dict[str, str] = {}
        self.errors: int = 0
        self.types: dict[str, list[str]] = {}
        self.current_type_name: str = ""

    def visit_Type(self, node: Type) -> Generator[AST, Any, Any]:
        self.current_type_name = str(node.name)
        yield from self.generic_visit(node)

    def visit_Constructor(self, node: Constructor) -> Generator[AST, Any, Any]:
        parent_name = self.current_type_name
        self.current_type_name = str(node.name)

        try:
            conflict = self.cons[self.current_type_name]
        except KeyError:
            self.cons[self.current_type_name] = parent_name
        else:
            print(f"Redefinition of constructor {self.current_type_name}")
            print(f"Defined in {conflict} and {parent_name}")
            self.errors += 1

        yield from self.generic_visit(node)

    def visit_Field(self, field: Field, name: str) -> None:
        key = str(field.type)
        self.types.setdefault(key, []).append(name)


def check(mod: Module) -> bool:
    """Check the parsed ASDL tree for correctness.

    Return True if success. For failure, the errors are printed out and False
    is returned.
    """

    v = Check()
    v.visit(mod)

    for t in v.types:
        if t not in mod.types and t not in builtin_types:
            v.errors += 1
            uses = ", ".join(v.types[t])
            print(f"Undefined type {t}, used in {uses}")
    return not v.errors


# The ASDL parser itself comes next. The only interesting external interface
# here is the top-level parse function.


def parse(filename: str) -> Module:
    """Parse ASDL from the given file and return a Module node describing it."""

    with open(filename, encoding="utf-8") as f:
        parser = ASDLParser()
        return parser.parse(f.read())


class ASDLParser:
    """Parser for ASDL files.

    Create, then call the parse method on a buffer containing ASDL.
    This is a simple recursive descent parser that uses tokenize_asdl for the
    lexing.
    """

    _id_kinds = (TokenKind.ConstructorId, TokenKind.TypeId)

    cur_token: Optional[Token]

    def __init__(self):
        self._tokenizer = None
        self.cur_token = None

    def parse(self, buf: str) -> Module:
        """Parse the ASDL in the buffer and return an AST with a Module root."""

        self._tokenizer = tokenize_asdl(buf)
        self._advance()
        return self._parse_module()

    def _parse_module(self) -> Module:
        if self._at_keyword("module"):
            self._advance()
        else:
            msg = f'Expected "module" (found {self.cur_token.value})'
            raise ASDLSyntaxError(msg, self.cur_token.lineno)
        name = self._match(self._id_kinds)
        self._match(TokenKind.LBrace)
        defs = self._parse_definitions()
        self._match(TokenKind.RBrace)
        return Module(name, defs)

    def _parse_definitions(self) -> list[Type]:
        defs: list[Type] = []
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            self._match(TokenKind.Equals)
            type = self._parse_type()
            defs.append(Type(typename, type))
        return defs

    def _parse_type(self) -> Union[Product, Sum]:
        if self.cur_token.kind == TokenKind.LParen:
            # If we see a (, it's a product
            return self._parse_product()
        else:
            # Otherwise it's a sum. Look for ConstructorId
            sumlist = [Constructor(self._match(TokenKind.ConstructorId), self._parse_optional_fields())]
            while self.cur_token.kind == TokenKind.Pipe:
                # More constructors
                self._advance()
                sumlist.append(Constructor(self._match(TokenKind.ConstructorId), self._parse_optional_fields()))
            return Sum(sumlist, self._parse_optional_attributes())

    def _parse_product(self) -> Product:
        return Product(self._parse_fields(), self._parse_optional_attributes())

    def _parse_fields(self) -> list[Field]:
        fields: list[Field] = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            is_seq, is_opt = self._parse_optional_field_quantifier()
            id = self._advance() if self.cur_token.kind in self._id_kinds else None
            fields.append(Field(typename, id, seq=is_seq, opt=is_opt))
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()
        self._match(TokenKind.RParen)
        return fields

    def _parse_optional_fields(self) -> Optional[list[Field]]:
        if self.cur_token.kind == TokenKind.LParen:
            return self._parse_fields()
        else:
            return None

    def _parse_optional_attributes(self) -> Optional[list[Field]]:
        if self._at_keyword("attributes"):
            self._advance()
            return self._parse_fields()
        else:
            return None

    def _parse_optional_field_quantifier(self) -> tuple[bool, bool]:
        is_seq, is_opt = False, False
        if self.cur_token.kind == TokenKind.Asterisk:
            is_seq = True
            self._advance()
        elif self.cur_token.kind == TokenKind.Question:
            is_opt = True
            self._advance()
        return is_seq, is_opt

    def _advance(self) -> Optional[str]:
        """Return the value of the current token and read the next one into self.cur_token."""

        cur_val = None if self.cur_token is None else self.cur_token.value
        try:
            self.cur_token = next(self._tokenizer)
        except StopIteration:
            self.cur_token = None
        return cur_val

    def _match(self, kind: Union[TokenKind, tuple[TokenKind, ...]]) -> str:
        """The 'match' primitive of RD parsers.

        *   Verifies that the current token is of the given kind (kind can be a tuple, in which the kind must match one
            of its members).
        *   Returns the value of the current token
        *   Reads in the next token
        """

        if (isinstance(kind, tuple) and self.cur_token.kind in kind) or self.cur_token.kind == kind:
            value = self.cur_token.value
            self._advance()
            return value
        else:
            msg = f"Unmatched {kind} (found {self.cur_token.kind})"
            raise ASDLSyntaxError(msg, self.cur_token.lineno)

    def _at_keyword(self, keyword: str) -> bool:
        return self.cur_token.kind == TokenKind.TypeId and self.cur_token.value == keyword
