"""Listener class"""
from socket import socket, create_server, SHUT_RDWR
from logging import getLogger
from threading import Thread
from proxy import Proxy
from socket_pair import Settings, SocketPair


class Listener:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = getLogger("fee-reverse")


    def listen(self) -> None:
        serverSocket = create_server(("", self.settings.port))
        self.logger.info("Stratum server was started on port %d", self.settings.port)
        while True:
            sock, addr = serverSocket.accept()
            self.logger.info("New connection from: %s", addr)
            Thread(target=lambda: self._start_proxy(sock)).start()
    
    def _start_proxy(self, client_socket: socket) -> None: 
        try:
            server_socket = socket()
            server_socket.connect((self.settings.remote_stratum, self.settings.remote_port))
        except Exception:
            self.logger.exception("Connection to %s failed", self.settings.remote_stratum)
            try:
                client_socket.shutdown(SHUT_RDWR)
            except Exception:
                pass
            client_socket.close()
            return

        socket_pair = SocketPair(client_socket, server_socket)
        proxy = Proxy(self.settings, socket_pair)
        Thread(target=proxy.client_to_server).start()
        proxy.server_to_client()
