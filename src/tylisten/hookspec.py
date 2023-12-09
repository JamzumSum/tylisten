import asyncio
import logging
import typing as t
from inspect import isawaitable
from typing import Any

from typing_extensions import ParamSpec, Self

_T = t.TypeVar("_T")
_P = ParamSpec("_P")
TyImpl = t.Callable[_P, t.Union[t.Awaitable[_T], _T]]

log = logging.getLogger(__name__)


async def call_impls(
    impls: t.Iterable[TyImpl[_P, _T]], *args: _P.args, **kwds: _P.kwargs
) -> t.AsyncGenerator[_T, t.Any]:
    """A uniform interface to call a batch of hook implements."""
    rfuts = [
        asyncio.ensure_future(c) if isawaitable(c := impl(*args, **kwds)) else c for impl in impls
    ]

    for rfut in rfuts:
        if asyncio.isfuture(rfut):
            try:
                yield await rfut
            except asyncio.CancelledError:
                raise
            except:
                log.error("async listener error!", exc_info=True)
                continue

        yield c  # type: ignore


class StaticHookSpec(t.Generic[_P, _T]):
    """Define a hook. The wrapped function will be the original defination."""

    __slots__ = ("__def__",)

    def __init__(self, defination: TyImpl[_P, _T]) -> None:
        self.__def__ = defination

    def instantiate(self) -> "HookSpec[_P, _T]":
        """Get a :class:`HookSpec` of this hook."""
        return HookSpec(self)

    __call__ = instantiate

    @property
    def TyInst(self) -> "t.Type[HookSpec[_P, _T]]":
        """Designed for type checkers. Used to annotate the type of the instantiated hook."""
        return HookSpec

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("__name__", "__qualname__", "__doc__", "__module__"):
            return getattr(self.__def__, __name)
        return super().__getattribute__(__name)


class HookSpec(t.Generic[_P, _T]):
    """An instance of a :class:`StaticHookSpec`."""

    __slots__ = ("__def__", "impls")

    impls: t.List[TyImpl[_P, _T]]
    """You can access this list to add/remove/clear_all implements."""

    def __init__(self, hookdef: StaticHookSpec[_P, _T]) -> None:
        super().__init__()
        self.impls = []
        self.__def__ = hookdef.__def__

    def add_impl(self, impl: TyImpl[_P, _T]) -> Self:
        """A shortcut to :obj:`.impls`.append."""
        self.impls.append(impl)
        return self

    async def gather(self, *args: _P.args, **kwds: _P.kwargs) -> t.List[_T]:
        """Gather all results, results respsect the corresponding order in `.impls`."""
        return [i async for i in call_impls(self.impls, *args, **kwds)]

    results = gather
    """An alias to :meth:`.gather`."""

    async def emit(self, *args: _P.args, **kwds: _P.kwargs) -> None:
        """Like :meth:`.gather`, but returns `None`."""
        await self.gather(*args, **kwds)

    async def first(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """Get the first valid result. If all results are invalid, raise `StopAsyncIteration`."""
        async for i in call_impls(self.impls, *args, **kwds):
            return i
        raise StopAsyncIteration

    async def __call__(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """
        Get the first valid result.
        If all results are invalid, call the defination and return its result.
        """
        try:
            return await self.first(*args, **kwds)
        except StopAsyncIteration:
            c = self.__def__(*args, **kwds)
            return await c if isawaitable(c) else c  # type: ignore

    @property
    def has_impl(self) -> bool:
        """Return if a hook is implemented."""
        return bool(self.impls)
