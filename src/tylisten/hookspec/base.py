import asyncio
import logging
import typing as t
from inspect import isawaitable

from typing_extensions import Self

from ._type import _P, _T, TyImpl

log = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from .static import StaticHookSpec

__all__ = ["HookSpec"]


async def call_impls(
    impls: t.Iterable[TyImpl[_P, _T]], *args: _P.args, **kwds: _P.kwargs
) -> t.AsyncGenerator[_T, t.Any]:
    """A uniform interface to call a batch of hook implements."""
    rfuts: t.List[t.Union[asyncio.Future[_T], _T]] = []
    for impl in impls:
        try:
            c = impl(*args, **kwds)
        except:
            log.error("sync listener error")
            continue

        rfuts.append(asyncio.ensure_future(c) if isawaitable(c) else c)  # type: ignore
        asyncio.Future

    for rfut in rfuts:
        if asyncio.isfuture(rfut):
            try:
                yield await rfut
            except asyncio.CancelledError:
                raise
            except:
                log.error("async listener error!", exc_info=True)
                continue
        else:
            yield rfut  # type: ignore


class HookSpec(t.Generic[_P, _T]):
    """An instance of a :class:`StaticHookSpec`.

    .. seealso:: :meth:`StaticHookSpec.__call__`
    """

    __slots__ = ("__def__", "impls")

    impls: t.List[TyImpl[_P, _T]]
    """You can access this list to add/remove/clear_all implements."""

    def __init__(self, hookdef: "StaticHookSpec[_P, _T]") -> None:
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
        """
        Get the first valid result.

        If all results are invalid, raise `StopAsyncIteration`.
        """
        for impl in self.impls:
            try:
                c = impl(*args, **kwds)
                if isawaitable(c):
                    return await c
                return c  # type: ignore
            except asyncio.CancelledError:
                raise
            except:
                log.error("listener error", exc_info=True)
                continue

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
