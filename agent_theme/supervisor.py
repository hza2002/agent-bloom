"""Run the app in its own foreground process group and mirror stops.

Ported from pangu/unix.py (MIT).  The extra supervisor process makes Ctrl-Z
and terminal hangup reliable: pty.fork alone leaves the app in an orphaned
process group, so the kernel drops SIGTSTP.
"""
import os
import signal

from .terminal import exit_code


def supervise(command):
    """Run the app in its own foreground process group and mirror stops.

    Ported from pangu/unix.py (MIT). The extra supervisor process is what makes
    Ctrl-Z and terminal hangup reliable: pty.fork alone leaves the app in an
    orphaned process group, so the kernel drops SIGTSTP.
    """
    signal.set_wakeup_fd(-1)
    for sig in (signal.SIGWINCH, signal.SIGCHLD):
        signal.signal(sig, signal.SIG_DFL)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    child = os.fork()
    if child == 0:
        os.setpgid(0, 0)
        os.tcsetpgrp(0, os.getpgrp())
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)
        os.execvp(command[0], command)
    try:
        os.setpgid(child, child)
    except OSError:
        pass
    try:
        os.tcsetpgrp(0, child)
    except OSError:
        pass

    def forward(signum, frame):
        try:
            os.killpg(child, signum)
        except OSError:
            pass

    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT, signal.SIGQUIT):
        signal.signal(sig, forward)
    while True:
        try:
            _, st = os.waitpid(child, os.WUNTRACED)
        except InterruptedError:
            continue
        except ChildProcessError:
            os._exit(1)
        if os.WIFSTOPPED(st):
            os.kill(os.getpid(), signal.SIGSTOP)
            try:
                os.tcsetpgrp(0, child)
            except OSError:
                pass
            os.killpg(child, signal.SIGCONT)
            continue
        os._exit(exit_code(st))
