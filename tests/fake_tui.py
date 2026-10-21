#!/usr/bin/env python3
"""Minimal app used by test_integration.py: alt screen, header, prompt, input."""
import os
import json
import signal
import sys
import time

APP = os.environ.get('FAKE_APP', 'claude')


def write(data):
    os.write(1, data)


def main():
    if os.environ.get('FAKE_PLAIN') == '1':
        write(b'plain output\n')
        return 0
    if os.environ.get('FAKE_SILENT') == '1':
        time.sleep(60)
        return 0

    try:
        rows = os.get_terminal_size(1).lines
    except OSError:
        rows = 40

    write(b'\x1b[?1049h\x1b[H\x1b[2J')
    if APP == 'codex':
        write(b'\x1b[1;1H\x1b[38;2;232;52;60m>_ '
              b'\x1b[1m\x1b[39;49mOpenAI Codex')
    else:
        write(b'\x1b[1;1H\x1b[39m\x1b[49m\x1b[1mClaude Code\x1b[22m')
    write(b'\x1b[2;1H~/fake')
    write(('\x1b[%d;1H> ' % rows).encode())
    # Claude probes synchronized-update support after entering the alt screen.
    write(b'\x1b[?2026$p')

    def resized(_signum, _frame):
        write(b'\x1b[3;1HRESIZED\x1b[K')

    signal.signal(signal.SIGWINCH, resized)
    for line in sys.stdin.buffer:
        text = line.strip()
        if text == b'/args':
            write(b'ARGS_BEGIN:' + json.dumps(sys.argv[1:]).encode() + b':ARGS_END')
            continue
        if text == b'/ack' and os.environ.get('FAKE_ACK_PATH'):
            with open(os.environ['FAKE_ACK_PATH'], 'w') as ack:
                ack.write('received')
        if text in (b'/flood', b'/tail'):
            # Exceed the 256 KiB output high-water mark even before PTY buffers.
            size = 512 * 1024 if text == b'/flood' else 128 * 1024
            data = memoryview(b'PAYLOAD_BEGIN:' + b'z' * size + b':PAYLOAD_END')
            while data:
                data = data[os.write(1, data):]
            return 0
        if text == b'/exit':
            write(b'\x1b[?1049l')
            return 7
        write(b'\x1b[4;1HACK ' + text + b'\x1b[K')
    return 0


if __name__ == '__main__':
    sys.exit(main())
