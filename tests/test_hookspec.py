import asyncio

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


class TestHookSpec:
    async def test_results(self):
        test_message.impls.clear()
        assert not test_message.has_impl

        async def async_add(a: int):
            return a + 2

        test_message.add_impl(lambda a: a - 1)
        test_message.add_impl(boom)
        test_message.add_impl(lambda a: a + 1)
        test_message.add_impl(aboom)
        test_message.add_impl(async_add)

        assert test_message.has_impl
        o = await test_message.results(4)
        assert o == [3, 5, 6]

    async def test_first(self):
        test_message.impls.clear()
        assert not test_message.has_impl

        async def async_add(a: int):
            return a + 2

        test_message.add_impl(boom)
        test_message.add_impl(aboom)
        test_message.add_impl(async_add)
        test_message.add_impl(lambda a: a + 1)
        test_message.add_impl(lambda a: a - 1)

        assert test_message.has_impl
        assert 6 == await test_message.first(4)

    async def test_call(self):
        test_message.impls.clear()
        assert not test_message.has_impl

        test_message.add_impl(boom)
        test_message.add_impl(aboom)

        assert test_message.has_impl
        assert 0 == await test_message(4)

        test_message.add_impl(lambda a: a - 1)
        assert 3 == await test_message(4)
