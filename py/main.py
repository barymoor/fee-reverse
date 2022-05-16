import os
import sys
from logging import getLogger, config as log_config, DEBUG
import click
from listener import Listener
from socket_pair import Settings


def get_logger_config(is_daemon: bool) -> dict:
    return {
        "version": 1,
        "formatters": {
            "syslog_format": {
                "format": "%(name)s: %(message)s"
            },
            "stream_format": {
                "format": "%(asctime)s %(name)s %(levelname)s: %(message)s"
            },
        },
        "handlers": {
            "syslog": {
                "class": "logging.handlers.SysLogHandler",
                "address": "/dev/log",
                "formatter": "syslog_format",
            },
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "stream_format",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "handlers": ["syslog"],
            "level": "INFO",
        },
        "disable_existing_loggers": False,
    }


def daemonize() -> None:
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError:
        getLogger().exception("1st fork failed")
        sys.exit(1)
    # decouple from parent environment
    os.chdir('/')
    os.setsid()
    os.umask(0)
    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError:
        getLogger().exception("2nd fork failed")
        sys.exit(1)
    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'w')
    se = open(os.devnull, 'w')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


@click.command()
@click.option("--debug", is_flag=True, default=False)
@click.option(
    "-d", "daemon",
    help="run as daemon",
    is_flag=True,
    default=False
)
@click.option(
    "--remote_stratum",
    help="remoteStratum cannot be null.",
    default="localhost"
)
@click.option(
    "--remote_port",
    help="remotePort cannot be null.",
    default=3333
)
@click.option(
    "--worker",
    help="worker cannot be null.",
    default="pool_worker")
@click.option(
    "--port",
    help="worker cannot be null.",
    default="3333"
)
@click.option(
    "--password",
    help="password cannot be null.",
    default="d=512"
)
def main(
    debug: bool,
    daemon: bool,
    remote_stratum: str,
    remote_port: int,
    worker: str,
    port: int,
    password: str
) -> None:
    log_config.dictConfig(get_logger_config(daemon))
    if debug:
        getLogger().setLevel(DEBUG)
    if daemon:
        daemonize()

    port = int(port)
    remote_port = int(remote_port)

    settings = Settings(remote_stratum, remote_port, worker, port, password)

    tcp_ip_proxy = Listener(settings)
    tcp_ip_proxy.listen()


if __name__ == "__main__":
    main()
