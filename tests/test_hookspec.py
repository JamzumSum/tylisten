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
    return test_message.new()


class TestHookSpec:
    async def test_results(self, hook):
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

    async def test_first(self, hook):
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

    async def test_call(self, hook):
        assert not hook.has_impl

        hook.add_impl(boom)
        hook.add_impl(aboom)

        assert hook.has_impl
        assert 0 == await hook(4)

        hook.add_impl(lambda a: a - 1)
        assert 3 == await hook(4)
