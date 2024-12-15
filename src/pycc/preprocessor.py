"""A partial implementation of a C processor."""

from __future__ import annotations

import os
from collections.abc import Generator, Iterable, Iterator
from itertools import chain

from ._compat import Optional
from .errors import CSyntaxError, warn_from_token
from .lexer import Lexer
from .token import Token, TokenKind


__all__ = ("Preprocessor",)


class Preprocessor:
    tokens: Iterator[Token]
    local_dir: str
    include_dirs: list[str]
    ignore_missing_includes: bool

    def __init__(self, tokens: Iterable[Token], local_dir: str = ""):
        self.tokens = iter(tokens)
        self.local_dir = local_dir
        self.include_dirs = []
        self.ignore_missing_includes = False

    # region ---- Preprocessing helpers ----

    def peek(self) -> Optional[Token]:
        # TODO: Is this the most efficient option for iterators in 3.9+?
        # Prior art:
        #   - The lookahead recipe in the itertools 3.14+ docs.
        #   - more_itertools.peekable.

        lookahead = next(self.tokens, None)
        if lookahead is not None:
            self.tokens = chain([lookahead], self.tokens)
        return lookahead

    def skip_line(self) -> None:
        """Skip tokens until the next newline is found.

        This is for directives where extra tokens are allowed before the newline that ends them.
        """

        if ((lookahead := next(self.tokens, None)) is None) or lookahead.at_bol:
            return

        warn_from_token(lookahead)

        next_line_start = next((t for t in self.tokens if t.at_bol), None)
        if next_line_start is not None:
            self.tokens = chain([next_line_start], self.tokens)

    def find_include_path(self, potential_path: str) -> str:
        for include_dir in chain([self.local_dir], self.include_dirs):
            candidate = os.path.normpath(os.path.join(include_dir, potential_path))
            if os.path.exists(candidate):
                return candidate

        # Default to the original path as a last resort.
        return potential_path

    # endregion

    # region ---- Preprocessing loop and rules

    def preprocess(self) -> Generator[Token]:
        inside_pp_directive: bool = False

        for tok in self.tokens:
            if tok.kind is TokenKind.PP_OCTO:
                inside_pp_directive = True

            elif inside_pp_directive:
                if tok.value == "include":
                    self.pp_include()

                elif tok.value == "pragma":
                    self.pp_pragma()

                else:
                    msg = "Invalid preprocessor directive."
                    raise CSyntaxError.from_token(msg, tok)

                inside_pp_directive = False

            else:
                yield tok

        if inside_pp_directive and not tok.at_bol:
            msg = "Invalid preprocessor directive."
            raise CSyntaxError(msg)

    def pp_include(self) -> None:
        """include directive: Find the included file and prepend its preprocessed tokens to our tokens."""

        include_start = next(self.tokens)

        if include_start.kind is TokenKind.STRING_LITERAL:
            # Pattern 1: #include "foo.h"
            parsed_include_path = include_start.value[1:-1]
            self.skip_line()

        elif include_start.kind is TokenKind.LE:
            # Pattern 2: #include <foo.h>

            # Find the closing ">" before a newline.
            _include_name_toks: list[Token] = []
            for _tok in self.tokens:
                if _tok.at_bol:
                    msg = "Expected '>'."
                    raise CSyntaxError.from_token(msg, _tok)

                if _tok.kind is TokenKind.GE:
                    break

                _include_name_toks.append(_tok)

            else:
                # We consumed all the remaining tokens without finding ">" *or* hitting a newline.
                msg = "Expected '>'."
                raise CSyntaxError.from_token(msg, include_start)

            parsed_include_path = "".join(t.value for t in _include_name_toks)

        else:
            # Pattern 3: #include FOO
            # TODO: Perform macro expansion.
            raise NotImplementedError

        parsed_include_path: str = "REPLACE_ME"
        include_path = self.find_include_path(parsed_include_path)

        try:
            with open(include_path, encoding="utf-8") as fp:
                include_source = fp.read()
        except OSError as exc:
            if not self.ignore_missing_includes:
                msg = f"Cannot open included file: {include_path!r}"
                raise CSyntaxError.from_token(msg, include_start) from exc
        else:
            # TODO: Can we avoid instantiating new lexers and preprocessors here?
            lexer = Lexer(include_source, include_path)
            preprocessor = Preprocessor(lexer.lex(), os.path.dirname(include_path))
            self.tokens = chain(preprocessor.preprocess(), self.tokens)

    def pp_include_next(self) -> None:
        raise NotImplementedError

    def pp_define(self) -> None:
        raise NotImplementedError

    def pp_undef(self) -> None:
        raise NotImplementedError

    def pp_if(self) -> None:
        raise NotImplementedError

    def pp_ifdef(self) -> None:
        raise NotImplementedError

    def pp_ifndef(self) -> None:
        raise NotImplementedError

    def pp_elif(self) -> None:
        raise NotImplementedError

    def pp_else(self) -> None:
        raise NotImplementedError

    def pp_endif(self) -> None:
        raise NotImplementedError

    def pp_line(self) -> None:
        raise NotImplementedError

    def pp_pragma_once(self) -> None:
        raise NotImplementedError

    def pp_pragma(self) -> None:
        """pragma directive: Ignore and skip to the next line."""

        # TODO: Capturing these might be useful for certain kinds of analysis.
        self.skip_line()

    def pp_error(self) -> None:
        raise NotImplementedError

    def pp_warning(self) -> None:
        raise NotImplementedError

    # endregion
