from __future__ import unicode_literals

import asyncio
import websockets


# taken from https://github.com/python/cpython/blob/3.9/Lib/asyncio/runners.py with modifications
def run_with_loop(main, loop):
    if asyncio.events._get_running_loop() is not None:
        raise RuntimeError(
            "asyncio.run() cannot be called from a running event loop")

    if not asyncio.coroutines.iscoroutine(main):
        raise ValueError("a coroutine was expected, got {!r}".format(main))

    try:
        # asyncio.events.set_event_loop(loop)
        return loop.run_until_complete(main)
    finally:
        try:
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            # asyncio.events.set_event_loop(None)
            pass


def _cancel_all_tasks(loop):
    to_cancel = asyncio.tasks.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(
        asyncio.tasks.gather(*to_cancel, loop=loop, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'unhandled exception during asyncio.run() shutdown',
                'exception': task.exception(),
                'task': task,
            })


class WebSocketsWrapper():
    "Wraps websockets module to use in non-async scopes"

    def __init__(self, url, headers=None):
        self.conn = websockets.connect(url, extra_headers=headers)
        self.loop = asyncio.events.get_event_loop() or asyncio.events.new_event_loop()

    def __enter__(self):
        return WebSocketsConnPool(run_with_loop(self.conn.__aenter__(), self.loop), self.loop)

    def __exit__(self, type, value, traceback):
        try:
            return run_with_loop(self.conn.__aexit__(type, value, traceback), self.loop)
        finally:
            self.loop.close()


class WebSocketsConnPool():
    def __init__(self, impl, loop):
        self.impl = impl
        self.loop = loop

    def send(self, *args):
        run_with_loop(self.impl.send(*args), self.loop)

    def recv(self, *args):
        run_with_loop(self.impl.recv(*args), self.loop)

    def __exit__(self, type, value, traceback):
        run_with_loop(self.impl.__aexit__(type, value, traceback), self.loop)
