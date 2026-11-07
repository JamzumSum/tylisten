"""A tiny hook specification library with typing support."""

from typing import Any

from .futstore import FutureStore
from .hookspec import HookSpec, StaticHookSpec, TimeoutHookSpec

__all__ = [
    "FutureStore",
    "HookSpec",
    "StaticHookSpec",
    "TimeoutHookSpec",
    "hookdef",
    "null_emitter",
]

hookdef = StaticHookSpec
null_emitter: HookSpec[Any, Any] = StaticHookSpec(lambda *args, **kwds: None)()
"""
A built-in emitter which could be used as a default spec.
"""
