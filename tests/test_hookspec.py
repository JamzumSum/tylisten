import asyncio
from time import time

import pytest

from tylisten import hookdef

pytestmark = pytest.mark.asyncio


@hookdef
async def test_message(a: int) -> int:
    """A test hook defination."""
    return 0


# fmt: off
async def aboom(a): raise RuntimeError
async def boom(a): raise RuntimeError
# fmt: on


@pytest.fixture
def hook():
    return test_message()


class TestHookSpec:
    async def test_results(self, hook: test_message.TyInst):
        assert not hook.has_impl

        async def async_add(a: int):
            return a + 2

        hook.add_impl(lambda a: a - 1)
        hook.add_impl(boom)
        hook.add_impl(lambda a: a + 1)
        hook.add_impl(aboom)
        hook.add_impl(async_add)

        assert hook.has_impl
        o = await hook.results(4)
        assert o == [3, 5, 6]

    async def test_first(self, hook: test_message.TyInst):
        assert not hook.has_impl

        async def async_add(a: int):
            return a + 2

        hook.add_impl(boom)
        hook.add_impl(aboom)
        hook.add_impl(async_add)
        hook.add_impl(lambda a: a + 1)
        hook.add_impl(lambda a: a - 1)

        assert hook.has_impl
        assert 6 == await hook.first(4)

    async def test_call(self, hook: test_message.TyInst):
        assert not hook.has_impl

        hook.add_impl(boom)
        hook.add_impl(aboom)

        assert hook.has_impl
        assert 0 == await hook(4)

        hook.add_impl(lambda a: a - 1)
        assert 3 == await hook(4)

    async def test_async(self, hook: test_message.TyInst):
        assert not hook.has_impl

        async def sleep_echo(a: int):
            await asyncio.sleep(1)
            return a

        for _ in range(4):
            hook.add_impl(sleep_echo)

        start = asyncio.get_event_loop().time()
        await hook.emit(1)
        end = asyncio.get_event_loop().time()

        assert end - start < 2

    def test_wrap(self):
        assert test_message.__name__ == "test_message"
        assert test_message.__qualname__.endswith("test_message")
        assert __name__ in test_message.__module__
        assert test_message.__doc__
        assert "A test hook defination." in test_message.__doc__
