import asyncio

import pytest

from tylisten import BaseMessage, Emitter, VirtualEmitter

pytestmark = pytest.mark.asyncio


class test_message(BaseMessage):
    def __init__(self, a) -> None:
        super().__init__()


class TestEmitter:
    async def test_wait(self):
        source = Emitter(test_message)
        loop = asyncio.get_event_loop()

        async def emit():
            await asyncio.sleep(0.4)
            await source.emit(a=1)

        async def wait():
            msg = await source.wait()
            assert loop.time() - start >= 0.4
            assert isinstance(msg, test_message)

        start = loop.time()
        await asyncio.gather(emit(), wait())

    async def test_listener(self):
        source = Emitter(test_message)
        pool = []

        # fmt: off
        async def aboom(_): raise RuntimeError
        async def boom(_): raise RuntimeError
        # fmt: on

        async def listener(msg: test_message):
            assert isinstance(msg, test_message)
            pool.append("async")

        source.listeners.append(aboom)
        source.listeners.append(boom)
        source.listeners.append(listener)
        source.listeners.append(lambda _: pool.append("sync"))

        async def emit():
            await source.emit(a=1)

        async def wait():
            msg = await source.wait()
            assert "sync" in pool
            assert "async" in pool
            assert isinstance(msg, test_message)

        await asyncio.gather(emit(), wait())

    async def test_abort(self):
        source = Emitter(test_message)

        async def wait_cancel(exc):
            with pytest.raises(exc):
                msg = await source.wait()
                assert isinstance(msg, test_message)

        async def abort():
            await asyncio.sleep(0.1)
            source.abort()

        await asyncio.gather(wait_cancel(asyncio.CancelledError), abort())
        assert not source._waiters

        async def abort_exc():
            await asyncio.sleep(0.1)
            source.abort(IOError)

        await asyncio.gather(wait_cancel(IOError), abort_exc())
        assert not source._waiters


class TestVirtualEmitter:
    async def test_connect(self):
        vemitter: VirtualEmitter[test_message] = VirtualEmitter()
        assert not vemitter.connected
        assert vemitter.listeners is None
        assert await vemitter.wait() is None

        async def boom(*_):
            raise RuntimeError

        pool = []
        source = Emitter(test_message)

        vemitter.connect_listeners.append(boom)
        vemitter.connect_listeners.append(lambda v, e: pool.append(id(v)) or pool.append(id(e)))
        vemitter.connect(source)

        assert vemitter.connected
        assert vemitter._conn_point() is source
        assert vemitter.listeners is source.listeners
        assert id(vemitter) in pool
        assert id(source) in pool

    async def test_wait(self):
        loop = asyncio.get_event_loop()
        vemitter: VirtualEmitter[test_message] = VirtualEmitter()
        source = Emitter(test_message)
        assert await vemitter.wait() is None
        vemitter.connect(source)

        async def emit():
            await asyncio.sleep(0.4)
            await source.emit(a=1)

        async def wait():
            msg = await vemitter.wait()
            assert loop.time() - start >= 0.4
            assert isinstance(msg, test_message)

        start = loop.time()
        await asyncio.gather(emit(), wait())
