"""Proxy class"""
from logging import getLogger, DEBUG
import json
from socket_pair import Settings, SocketPair
from datetime import datetime

class Proxy:
    def __init__(
        self,
        settings: Settings,
        socks: SocketPair,
    ) -> None:
        self.settings = settings
        self.socks = socks
        self.logger = getLogger("fee-reverse " + socks.client_addr[0])
        self.last_submit = datetime(2022,1,1)


    def client_to_server(self) -> None:
        with self.socks.guard() as (client, server):
            with client.makefile("rb") as input_stream:
                for line in input_stream:
                    self.logger.log(DEBUG - 5, line)
                    obj = json.loads(line)
                    if obj["method"].lower() == "mining.subscribe":
                        obj["params"] = [
                            "cgminer/4.11.1",
                            obj["params"][1] if len(obj["params"]) > 1 else None,
                            self.settings.remote_stratum,
                            self.settings.remote_port
                        ]
                        line = (json.dumps(obj) + "\n").encode("utf-8")

                    if obj["method"].lower() == "mining.authorize":
                        current_worker = obj["params"][0]
                        self.logger.info(
                            "Changing worker name from \"%s\" to \"%s\"",
                            current_worker,
                            self.settings.worker
                        )
                        obj["params"] = [
                            self.settings.worker,
                            self.settings.password
                        ]
                        line = (json.dumps(obj) + "\n").encode("utf-8")

                    if obj["method"].lower() == "mining.submit":
                        obj["params"][0] = self.settings.worker
                        line = (json.dumps(obj) + "\n").encode("utf-8")
                        now = datetime.now()
                        diff = now - self.last_submit
                        if diff.total_seconds() > 60:
                            self.logger.info("Submit work")
                            self.last_submit = now

                    self.logger.debug("--> %s", obj["method"])

                    server.sendall(line)


    def server_to_client(self) -> None:
        with self.socks.guard() as (client, server):
            with server.makefile("rb") as input_stream:
                for line in input_stream:
                    self.logger.log(DEBUG - 5, line)
                    obj = json.loads(line)       
                    if "method" in obj:
                        self.logger.debug("<-- %s", obj["method"])
                    client.sendall(line)
