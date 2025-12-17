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
        except BaseException:
            log.error("sync listener error!", exc_info=True)
            continue

        rfuts.append(asyncio.ensure_future(c) if isawaitable(c) else c)  # type: ignore
        asyncio.Future

    for rfut in rfuts:
        if asyncio.isfuture(rfut):
            try:
                yield await rfut
            except asyncio.CancelledError:
                raise
            except BaseException:
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

    @t.overload
    def replace_impl(
        self, index_or_impl: t.Union[int, TyImpl[_P, _T]]
    ) -> t.Callable[[TyImpl[_P, _T]], None]: ...

    @t.overload
    def replace_impl(
        self, index_or_impl: t.Union[int, TyImpl[_P, _T]], new_impl: TyImpl[_P, _T]
    ) -> None: ...

    def replace_impl(
        self,
        index_or_impl: t.Union[int, TyImpl[_P, _T]],
        new_impl: t.Optional[TyImpl[_P, _T]] = None,
    ) -> t.Union[None, t.Callable[[TyImpl[_P, _T]], None]]:
        """Replace an implementation according to the given index or function.

        :param index_or_impl: The index or the function.
            The function will be transformed to index by :obj:`.impls`.index.
        :param new_impl: If not given, this method could be used as a decorator.

        :raise ValueError: If :obj:`index_or_impl` is a function AND not present in :obj:`.impls`.
        """
        if not isinstance(index_or_impl, int):
            index_or_impl = self.impls.index(index_or_impl)

        if new_impl is None:
            return lambda f: self.impls.__setitem__(index_or_impl, f)

        self.impls[index_or_impl] = new_impl

    async def gather(self, *args: _P.args, **kwds: _P.kwargs) -> t.List[_T]:
        """Gather all results, results respsect the corresponding order in :obj:`.impls`.

        :return: All results corresponding the order in :obj:`.impls`
        """
        return [i async for i in call_impls(self.impls, *args, **kwds)]

    results = gather
    """An alias to :meth:`.gather`."""

    async def emit(self, *args: _P.args, **kwds: _P.kwargs) -> None:
        """Like :meth:`.gather`, but returns `None`."""
        await self.gather(*args, **kwds)

    async def first(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """
        Get the first valid result.

        If all results are invalid, raises :exc:`StopAsyncIteration`.

        :raise StopAsyncIteration: If all results are invalid.

        :return: The first valid result.
        """
        for impl in self.impls:
            try:
                c = impl(*args, **kwds)
                if isawaitable(c):
                    return await c
                return c  # type: ignore
            except asyncio.CancelledError:
                raise
            except BaseException:
                log.error("listener error", exc_info=True)
                continue

        raise StopAsyncIteration

    async def __call__(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """
        Get the first valid result.
        If all results are invalid, call the defination and return its result.

        :return: The first valid result. If all results are invalid, returns the result of the defination.
        """
        try:
            return await self.first(*args, **kwds)
        except StopAsyncIteration:
            c = self.__def__(*args, **kwds)
            return await c if isawaitable(c) else c  # type: ignore

    @property
    def has_impl(self) -> bool:
        """Return if a hook is implemented.

        :return: If this hook is implemented.
        """
        return bool(self.impls)
