from logging import getLogger
from socket import socket, SHUT_RDWR
from contextlib import contextmanager
from typing import Iterator
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class Settings:
    remote_stratum: str
    remote_port: int
    worker: str
    port: int
    password: str


class SocketPair:
    def __init__(self, client: socket, server: socket) -> None:
        self.client = client
        self.server = server
        self.client_addr = client.getpeername()
        self.server_addr = server.getpeername()
        self.lock = Lock()
        self.is_closed = False
        self.logger = getLogger("fee-reverse")

    @contextmanager
    def guard(self) -> Iterator[tuple[socket, socket]]:
        try:
            yield (self.client, self.server)
            with self.lock:
                if not self.is_closed:
                    self.logger.info (f"Connection between {self.client_addr} and {self.server_addr} closed normally")
        except Exception as err:
            self._manage_exception(err)
        self.close()

    def close(self) -> None:
        with self.lock:
            if self.is_closed:
                return
            self._shutdown()
            self._close()
            self.is_closed = True

    def _shutdown(self) -> None:
        for sock, addr in [(self.client, self.client_addr), (self.server, self.server_addr)]:
            try:
                sock.shutdown(SHUT_RDWR)
            except OSError:
                pass
            except Exception:
                self.logger.exception("%s: exception", addr)

    def _close(self) -> None:
        for sock, addr in [(self.client, self.client_addr), (self.server, self.server_addr)]:
            try:
                sock.close()
            except Exception:
                self.logger.exception("%s: exception", addr)

    def _manage_exception(self, err: Exception) -> None:
        with self.lock:
            if self.is_closed:
                return
            if isinstance(err, TimeoutError):
                self.logger.info (f"Connection between {self.client_addr} and {self.server_addr} timed out: {err.strerror}")
                return
            if isinstance(err, BrokenPipeError):
                self.logger.info (f"Connection between {self.client_addr} and {self.server_addr} interrupted: {err.strerror}")
                return
            if isinstance(err, OSError):
                self.logger.info (f"Connection between {self.client_addr} and {self.server_addr}: OSError happened: {err.strerror}")
                return
            self.logger.exception (f"Connection between {self.client_addr} and {self.server_addr} exception occured")
