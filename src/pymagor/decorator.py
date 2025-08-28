from functools import wraps
from typing import Any, Callable, TypeVar, cast

__all__ = ["chained_method", "operation", "filter"]

T = TypeVar("T")  # , bound="BaseImage")


def chained_method(method: Callable[..., None]) -> Callable[..., T]:
    """Decorator for methods that return a new instance with modifications.

    This decorator handles the common pattern of creating a copy of the instance,
    applying modifications to it, and returning the new instance.

    A '_clone' method is required to be implemented by the class.

    Args:
        method: The method to decorate. It should modify the instance in-place
               and return None.

    Returns:
        A wrapped method that returns a new instance with the modifications applied.
    """

    @wraps(method)
    def wrapper(self: T, *args: Any, **kwargs: Any) -> T:
        new_instance = self._clone()
        method(new_instance, *args, **kwargs)
        return new_instance

    return cast(Callable[..., T], wrapper)


operation = chained_method
filter = chained_method
