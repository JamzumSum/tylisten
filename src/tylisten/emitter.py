import asyncio
import logging
from collections import deque
from inspect import isawaitable
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from weakref import WeakSet

from typing_extensions import ParamSpec, Self

from .message import BaseMessage

_M = TypeVar("_M", bound=BaseMessage)
_P = ParamSpec("_P")
TyListener = Callable[[_M], Union[Awaitable[Any], Any]]

log = logging.getLogger(__name__)


def discard(q: Deque, v):
    if v in q:
        q.remove(v)


async def call_listeners(listeners: Iterable[TyListener[_M]], msg: _M):
    clist: List[Awaitable[Any]] = []
    for listener in listeners:
        try:
            c = listener(msg)
        except:
            log.error("sync listener error!", exc_info=True)
            continue
        if isawaitable(c):
            clist.append(asyncio.ensure_future(c))
    if clist:
        try:
            await asyncio.wait(clist)
        except asyncio.CancelledError:
            raise
        except:
            log.error("async listener error!", exc_info=True)


class Emitter(Generic[_M, _P]):
    """An emitter which could be listened on or waited for."""

    listeners: List[TyListener[_M]]
    _waiters: Deque[asyncio.Future]

    def __init__(self, ty: Callable[_P, _M]) -> None:
        self._ty = ty
        self.listeners = []
        """You can access to this list to add/remove/clear_all listeners."""
        self._waiters = deque()

    async def wait(self) -> _M:
        fut = asyncio.get_event_loop().create_future()
        self._waiters.append(fut)
        try:
            return await fut
        finally:
            discard(self._waiters, fut)

    async def emit(self, *args: _P.args, **kwds: _P.kwargs):
        inst_msg = self._ty(*args, **kwds)
        await call_listeners(self.listeners, inst_msg)

        for fut in self._waiters:
            if not fut.done():
                fut.set_result(inst_msg)

    def abort(self, exc: Union[BaseException, Type[BaseException], None] = None):
        for fut in self._waiters:
            if exc is None:
                fut.cancel()
            else:
                fut.set_exception(exc)
        self._waiters.clear()


class VirtualEmitter(Generic[_M]):
    listeners: List[TyListener[_M]]
    connect_listeners: List[Callable[[Self, Emitter[_M, Any]], Any]]

    def __init__(self, _: Optional[Type[_M]] = None) -> None:
        super().__init__()
        self.listeners = []
        self.connect_listeners = []
        self.connected = WeakSet()  # type: WeakSet[Emitter[_M, Any]]

    def connect(self, connect_emitter: Emitter[_M, Any]):
        self.connected.add(connect_emitter)
        connect_emitter.listeners.append(lambda m: call_listeners(self.listeners, m))
        for listener in self.connect_listeners:
            try:
                listener(self, connect_emitter)
            except:
                log.error("sync connect_listener error!", exc_info=True)

    async def wait(self) -> Optional[_M]:
        if not self.connected:
            return

        all_wait = [asyncio.create_task(i.wait()) for i in self.connected]
        done, _ = await asyncio.wait(all_wait, return_when="FIRST_COMPLETED")
        return next(iter(done)).result()
