import asyncio
import logging

import pytest

from tylisten import hookdef
from tylisten.hookspec.base import call_impls

pytestmark = pytest.mark.asyncio


@hookdef
async def message_hook(a: int) -> int:
    """A test hook defination."""
    return 0


# fmt: off
async def aboom(a): raise RuntimeError
def boom(a): raise RuntimeError
# fmt: on


@pytest.fixture
def hook():
    return message_hook()


@pytest.fixture
def timeout():
    return message_hook.with_timeout(0.5)


class TestHookSpec:
    async def test_results(self, hook: message_hook.TyInst):
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

    async def test_first(self, hook: message_hook.TyInst):
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

    async def test_call(self, hook: message_hook.TyInst):
        assert not hook.has_impl

        hook.add_impl(boom)
        hook.add_impl(aboom)

        assert hook.has_impl
        assert 0 == await hook(4)

        hook.add_impl(lambda a: a - 1)
        assert 3 == await hook(4)

    async def test_async(self, hook: message_hook.TyInst):
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

    async def test_wrap(self):
        assert message_hook.__name__ == "message_hook"
        assert message_hook.__qualname__.endswith("message_hook")
        assert __name__ in message_hook.__module__
        assert message_hook.__doc__
        assert "A test hook defination." in message_hook.__doc__
        assert "a" in message_hook.__annotations__

    async def test_inherit(self, hook: message_hook.TyInst):
        assert 0 == await hook(1)

        hook.add_impl(sup := lambda a: 1)
        assert 1 == await hook(1)

        hook.add_impl(lambda a: 9)

        @hook.replace_impl(sup)
        async def plus1(a: int):
            return a + 1

        assert 2 == await hook(1)

        hook.replace_impl(0, lambda a: a + 2)
        assert 3 == await hook(1)

    async def test_replace_impl_out_of_range(self, hook: message_hook.TyInst):
        hook.add_impl(lambda a: a)

        with pytest.raises(IndexError):
            hook.replace_impl(5, lambda a: a)

    async def test_replace_impl_missing(self, hook: message_hook.TyInst):
        with pytest.raises(ValueError):
            hook.replace_impl(lambda a: a)

    async def test_listener_error_logged_with_impl(self, hook: message_hook.TyInst, caplog):
        hook.add_impl(boom)

        with caplog.at_level(logging.ERROR, logger="tylisten.hookspec.base"):
            assert await hook.gather(1) == []

        messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == "tylisten.hookspec.base"
        ]
        assert any("boom" in message for message in messages)

    async def test_definition_error_has_no_internal_context(self):
        @hookdef
        async def failing(a: int) -> int:
            raise ValueError("definition failed")

        hook = failing()
        hook.add_impl(boom)

        with pytest.raises(ValueError) as excinfo:
            await hook(1)

        assert excinfo.value.__context__ is None


async def test_call_impls_cancels_pending_on_early_close():
    cancelled = asyncio.Event()

    async def quick(a: int):
        return a

    async def slow(a: int):
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    agen = call_impls([quick, slow], 1)
    assert await anext(agen) == 1
    await agen.aclose()

    assert cancelled.is_set()


@pytest.mark.parametrize("exc_type", [KeyboardInterrupt, SystemExit])
async def test_process_exception_propagates(exc_type):
    def raise_process_exception(a: int):
        raise exc_type

    hook = message_hook()
    hook.add_impl(raise_process_exception)

    with pytest.raises(exc_type):
        await hook.gather(1)

    with pytest.raises(exc_type):
        await hook.first(1)


async def test_sync_cancelled_error_propagates():
    def cancel(a: int):
        raise asyncio.CancelledError

    hook = message_hook()
    hook.add_impl(cancel)

    with pytest.raises(asyncio.CancelledError):
        await hook.gather(1)

    with pytest.raises(asyncio.CancelledError):
        await hook.first(1)


@pytest.mark.parametrize("entry", ["gather", "results", "emit", "first", "__call__"])
async def test_timeout_applies_to_all_entrypoints(entry: str):
    timeout = message_hook.with_timeout(0.05)

    async def sleep(a: int):
        await asyncio.sleep(0.5)
        return a

    timeout.add_impl(sleep)

    with pytest.raises(asyncio.TimeoutError):
        await getattr(timeout, entry)(1)


async def test_timeout_cancels_all_listeners():
    timeout = message_hook.with_timeout(0.05)
    started = [asyncio.Event(), asyncio.Event()]
    cancelled = [asyncio.Event(), asyncio.Event()]

    def make_listener(index: int):
        async def listener(a: int):
            started[index].set()
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                cancelled[index].set()
                raise

        return listener

    timeout.add_impl(make_listener(0))
    timeout.add_impl(make_listener(1))

    with pytest.raises(asyncio.TimeoutError):
        await timeout.gather(1)

    assert all(event.is_set() for event in started)
    assert all(event.is_set() for event in cancelled)


async def test_timeout(timeout: message_hook.TyTmInst):
    assert not timeout.has_impl

    async def sleep(a: int):
        await asyncio.sleep(a)
        return a

    timeout.add_impl(lambda a: a)
    timeout.add_impl(sleep)

    with pytest.raises(asyncio.TimeoutError):
        await timeout.gather(1)

    assert 1 == await timeout.first(1)
    assert 1 == await timeout(1)
    await timeout.emit_suppress_timeout(1)
