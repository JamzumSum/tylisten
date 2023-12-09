"""A tiny hook specification library with typing support."""

from typing import Any

from .futstore import FutureStore
from .hookspec import HookSpec, StaticHookSpec

__all__ = [
    "StaticHookSpec",
    "HookSpec",
    "hookdef",
    "null_emitter",
    "FutureStore",
]

hookdef = StaticHookSpec
null_emitter: HookSpec[Any, Any] = StaticHookSpec(lambda *args, **kwds: None).instantiate()
"""
A built-in emitter which could be used as a default spec.
"""
