import logging
import typing as t
from functools import WRAPPER_ASSIGNMENTS
from typing import Any

from ._type import _P, _T, TyImpl
from .base import HookSpec
from .timeout import TimeoutHookSpec

__all__ = ["StaticHookSpec"]

log = logging.getLogger(__name__)


class StaticHookSpec(t.Generic[_P, _T]):
    """Defines a hook. The wrapped function will be the original defination."""

    __slots__ = ("__def__",)

    def __init__(self, defination: TyImpl[_P, _T]) -> None:
        self.__def__ = defination

    @property
    def TyInst(self) -> t.Type[HookSpec[_P, _T]]:
        """Designed for type checkers. Used to annotate the type of a derived :class:`HookSpec`."""
        return HookSpec

    @property
    def TyTmInst(self) -> t.Type[TimeoutHookSpec[_P, _T]]:
        """Designed for type checkers. Used to annotate the type of a derived :class:`TimeoutHookSpec`."""
        return TimeoutHookSpec

    def __getattribute__(self, __name: str) -> Any:
        if __name in WRAPPER_ASSIGNMENTS:
            return getattr(self.__def__, __name)
        if __name == "__annotations__":
            # python 3.14: __annotations__ lazy evaluation
            # BUG: is this readonly?
            return getattr(self.__def__, __name, {})
        return super().__getattribute__(__name)

    def __call__(self) -> HookSpec[_P, _T]:
        """Get a :class:`HookSpec` of this hook."""
        return HookSpec(self)

    def with_timeout(self, timeout: float):
        """Get a :class:`TimeoutHookSpec` of this hook."""
        return TimeoutHookSpec(self, timeout=timeout)
