from __future__ import annotations

import sys
from typing import TYPE_CHECKING


__all__ = ("TypeAlias",)


if sys.version_info >= (3, 10):
    from typing import TypeAlias
elif TYPE_CHECKING:
    from typing_extensions import TypeAlias
else:

    class TypeAlias:
        """Placeholder for typing.TypeAlias."""
