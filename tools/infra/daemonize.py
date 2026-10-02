#!/usr/bin/env python3
"""Daemoniza un comando con doble-fork: el hijo termina reparentado a PID 1
(tini), fuera del árbol de la llamada de herramienta que lo lanzó."""
import os
import sys

def main():
    cmd = sys.argv[1:]
    if not cmd:
        print("uso: daemonize.py CMD [ARGS...]", file=sys.stderr)
        sys.exit(2)
    # primer fork: el padre sale ya → el hijo queda huérfano → reparentado a init
    pid = os.fork()
    if pid > 0:
        print("[+] daemonize: padre sale (hijo %d reparentado a init)" % pid)
        return
    os.setsid()
    # segundo fork: garantiza que nunca controle terminal y queda nieto huérfano
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)
    # redirigir stdio al log y cerrar los heredados de la herramienta
    log = open(os.environ.get("DAEMON_LOG", "/home/z/my-project/scripts/daemon.log"), "ab", buffering=0)
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    main()
