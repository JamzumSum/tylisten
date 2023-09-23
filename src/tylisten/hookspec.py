import asyncio
import logging
from inspect import isawaitable
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    TypeVar,
    Union,
)

from typing_extensions import ParamSpec, Self

_T = TypeVar("_T")
_P = ParamSpec("_P")
TyImpl = Callable[_P, Union[Awaitable[_T], _T]]

log = logging.getLogger(__name__)


async def call_impls(
    listeners: Iterable[TyImpl[_P, _T]], *args: _P.args, **kwds: _P.kwargs
) -> AsyncGenerator[_T, Any]:
    for listener in listeners:
        try:
            c = listener(*args, **kwds)
        except:
            log.error("sync listener error!", exc_info=True)
            continue

        if isawaitable(c):
            try:
                c = await c
            except asyncio.CancelledError:
                raise
            except:
                log.error("async listener error!", exc_info=True)
                continue

        yield c  # type: ignore


class HookSpec(Generic[_P, _T]):
    """Define a hook. The wrapped function will be the original defination."""

    __slots__ = ("impls", "__def__")

    impls: List[TyImpl[_P, _T]]
    """You can access this list to add/remove/clear_all implements."""

    def __init__(self, defination: TyImpl[_P, _T]) -> None:
        self.__def__ = defination

    def new(self):
        o = HookSpec(self.__def__)
        o.impls = []
        return o

    def add_impl(self, impl: TyImpl[_P, _T]) -> Self:
        """A shortcut to `.impls.append`."""
        self.impls.append(impl)
        return self

    async def results(self, *args: _P.args, **kwds: _P.kwargs) -> List[_T]:
        """Get all results, according to the order in `.impls`."""
        return [i async for i in call_impls(self.impls, *args, **kwds)]

    async def first(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """Get the first valid result from `.results`. If no results is valid, raise `StopAsyncIteration`."""
        async for i in call_impls(self.impls, *args, **kwds):
            return i
        raise StopAsyncIteration

    async def __call__(self, *args: _P.args, **kwds: _P.kwargs) -> Optional[_T]:
        """Get the first valid result from `.results`. If no results is valid, return result from the defination."""
        try:
            return await self.first(*args, **kwds)
        except StopAsyncIteration:
            c = self.__def__(*args, **kwds)
            return await c if isawaitable(c) else c  # type: ignore

    @property
    def has_impl(self):
        """Return if a hook is implemented."""
        return bool(self.impls)
