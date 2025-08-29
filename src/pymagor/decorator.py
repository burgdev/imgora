"""Decorators for pymagor.

This module provides decorators for pymagor.

Examples:

```python
from pymagor import Imagor, Signer
from pymagor.decorator import filter, operation, chained_method

class MyImagor(Imagor):
    @filter
    def my_filter(self, arg1: int, arg2: str) -> Self:
        self.add_filter("my_filter", arg1, arg2)

    @operation
    def my_operation(self, arg1: int, arg2: str) -> Self:
        self.add_operation("my_operation", arg1, arg2)

    @chained_method
    def with_image(self, image: str) -> Self:
        self._image = image.replace("jpeg", "jpg")
```

"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

__all__ = ["chained_method", "operation", "filter"]

_F = TypeVar("_F", bound=Callable[..., Any])


def chained_method(method: _F) -> _F:
    """Decorator for methods that return a new instance with modifications.

    The decorated method should modify the instance in-place and not return anything.
    The decorator will handle creating and returning the new instance.
    """

    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        new_instance = self._clone()
        method(new_instance, *args, **kwargs)
        return new_instance

    # The cast is important for type checking and IDE support
    return cast(_F, wrapper)


# Alias for backward compatibility
operation = chained_method
"""Decorator for methods that return a new instance with modifications."""

filter = chained_method
"""Decorator for methods that return a new instance with modifications."""
