"""A hung UIA provider cannot keep the controlling CLI alive indefinitely."""

import multiprocessing

from .contracts import JevError


def _worker(connection, handle, executable):
    try:
        from .native import NativeDriver, list_windows

        driver = NativeDriver(handle, executable) if handle is not None else None
        connection.send((True, None))
        while True:
            command, args = connection.recv()
            try:
                if command == "windows":
                    value = list_windows()
                elif command == "observe" and driver:
                    value = driver.observe()
                elif command == "execute" and driver:
                    value = driver.execute(*args)
                else:
                    raise JevError("invalid_worker_command")
                connection.send((True, value))
            except JevError as e:
                connection.send((False, e.code))
            except Exception:
                connection.send((False, "native_worker_error"))
    except JevError as e:
        connection.send((False, e.code))
    except (EOFError, BrokenPipeError):
        pass
    except Exception:
        try:
            connection.send((False, "native_worker_error"))
        except (EOFError, BrokenPipeError):
            pass
    finally:
        connection.close()


class ProcessDriver:
    def __init__(self, handle=None, executable=None, *, timeout=15):
        self.timeout = timeout
        self.closed = False
        ctx = multiprocessing.get_context("spawn")
        self.connection, child = ctx.Pipe()
        self.process = ctx.Process(target=_worker, args=(child, handle, executable), daemon=True)
        self.process.start()
        child.close()
        try:
            self._receive()
        except Exception:
            self.close()
            raise

    def _receive(self):
        if not self.connection.poll(self.timeout):
            self.close()
            raise JevError("native_worker_timeout")
        try:
            ok, value = self.connection.recv()
        except (EOFError, OSError):
            self.close()
            raise JevError("native_worker_disconnected") from None
        if not ok:
            raise JevError(value)
        return value

    def _call(self, command, *args):
        if self.closed:
            raise JevError("native_worker_closed")
        try:
            self.connection.send((command, args))
        except (OSError, EOFError):
            self.close()
            raise JevError("native_worker_disconnected") from None
        return self._receive()

    def windows(self):
        return self._call("windows")

    def observe(self):
        return self._call("observe")

    def execute(self, snapshot, candidate, max_age):
        return self._call("execute", snapshot, candidate, max_age)

    def close(self):
        if not self.closed:
            self.closed = True
            self.connection.close()
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=2)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
