"""Command-line surface for huawei-bloom."""
import os
import shutil
import subprocess
import sys

from . import __version__
from .apps import PROFILES
from .launcher import Launcher

VERSION = __version__


ELEMENT_FLAGS = {
    '--logo': ('logo', True), '--no-logo': ('logo', False),
    '--header': ('header', True), '--no-header': ('header', False),
    '--title': ('title', True), '--no-title': ('title', False),
    '--home': ('home', True), '--no-home': ('home', False),
}

HELP = """huawei-bloom %s - Huawei branding for Claude Code and Codex CLI.

Usage:
  huawei-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]

Elements (defaults: logo=on header=on title=off home=on):
  --logo / --no-logo       Header mark only. Claude: 3-row flower; Codex: ✿
                           instead of >_. The home flower is not affected.
  --header / --no-header   Header name: 盤古·Claude / 盤古 · Codex.
  --title / --no-title     Window title. Off by default to keep tmux pane
                           titles searchable.
  --home / --no-home       Background Bloom, ambient sweep and home. --no-home
                           disables the overlay; Codex restores its native
                           welcome.

Behavior:
  A fresh session plays the one-shot intro. Resuming, continuing, or passing
  an initial prompt skips it. The ambient sweep stops on submit and returns
  after /clear. Non-interactive commands bypass the wrapper.

Other:
  --raw                    Run the app untouched.
  --check                  Verify embedded patterns, engine, binary and version.
  -h, --help               Show this help.
  -V, --version            Show huawei-bloom version.

Element flags, --raw and --check may appear before or after the app name.
--help/--version are wrapper options only before the app. Use -- to pass any
flag with the same spelling to the app.

Exit status:
  0 success; 1 check failed; 2 usage error; 127 app missing;
  128+signal for signal termination; otherwise the app's exit status.
"""


def usage_error(message):
    sys.stderr.write('huawei-bloom: %s\n' % message)
    sys.stderr.write("Try 'huawei-bloom --help'.\n")
    raise SystemExit(2)


def parse(argv):
    app = None
    app_args = []
    overrides = []
    raw = check = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--':
            rest = argv[i + 1:]
            if app is None:
                if not rest:
                    usage_error('missing app after --')
                app, app_args = rest[0], rest[1:]
            else:
                app_args.extend(rest)
            break
        if app is None and a in ('-h', '--help'):
            sys.stdout.write(HELP % VERSION)
            raise SystemExit(0)
        if app is None and a in ('-V', '--version'):
            sys.stdout.write('huawei-bloom %s\n' % VERSION)
            raise SystemExit(0)
        if a in ELEMENT_FLAGS:
            overrides.append(ELEMENT_FLAGS[a])
        elif a == '--raw':
            raw = True
        elif a == '--check':
            check = True
        elif app is None:
            if a.startswith('-'):
                usage_error('unknown option %s' % a)
            app = a
        else:
            app_args.append(a)
        i += 1
    if app is None:
        usage_error('missing app')
    app = app.lower()
    if app not in PROFILES:
        usage_error('unknown app %s' % app)
    if raw and check:
        usage_error('--raw and --check cannot be combined')
    return app, app_args, overrides, raw, check


def engine_check(profile):
    """Exercise the optional engine modules; fail-open code deserves a loud check."""
    rows = []
    try:
        from . import art, overlay
        brand = art.BRANDS[profile.key]
        base = (overlay.CodexOverlay if profile.key == 'codex'
                else overlay.ClaudeOverlay)
        ov = base(120, 32, brand, in_alt=True, reveal=False,
                  pal=art.palette(), strict=False)
        ov.note_input(b'check\r')
        rows.append(('overlay', ov.submitted, 'constructs; input tracked'))
    except Exception as exc:  # noqa: BLE001 - a check must report any failure
        rows.append(('overlay', False, '%s: %s' % (type(exc).__name__, exc)))
    try:
        from . import art, intro
        brand = art.BRANDS[profile.key]
        scene = intro.Bloom(120, 32, art.palette(), brand, bloom_length=2.95)
        ok = bool(scene.ok and scene.frame(1.0))
        rows.append(('bloom', ok, 'frames' if ok else 'no mark'))
    except Exception as exc:  # noqa: BLE001
        rows.append(('bloom', False, '%s: %s' % (type(exc).__name__, exc)))
    return rows


def binary_check(profile):
    """Confirm the wrapped CLI exists and prints a version, without running it."""
    binary = shutil.which(profile.binary)
    if not binary:
        return [('binary', False, '%s not found on PATH' % profile.binary)]
    rows = [('binary', True, binary)]
    try:
        result = subprocess.run(
            [binary, '--version'], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=3, text=True)
        output = result.stdout or ''
        line = output.strip().splitlines()
        marker_ok = (not profile.version_marker
                     or profile.version_marker.lower() in output.lower())
        rows.append(('version', result.returncode == 0 and bool(line) and marker_ok,
                     line[0][:60] if line else 'no output'))
    except Exception as exc:  # noqa: BLE001
        rows.append(('version', False, '%s: %s' % (type(exc).__name__, exc)))
    return rows


def main():
    app, app_args, overrides, raw, check = parse(sys.argv[1:])
    profile = PROFILES[app]
    opts = dict(profile.defaults)
    for key, value in overrides:
        opts[key] = value
    if check:
        rows = (profile.check(opts) + engine_check(profile)
                + binary_check(profile))
        rows.append(('home', True, 'on (background)' if opts['home'] else 'off'))
        print('huawei-bloom %s check: %s' % (VERSION, app))
        ok = True
        for name, passed, detail in rows:
            print('  %-12s %-4s %s' % (name, 'ok' if passed else 'FAIL', detail))
            ok = ok and passed
        return 0 if ok else 1
    binary = shutil.which(profile.binary)
    if not binary:
        sys.stderr.write('huawei-bloom: %s not found on PATH\n' % profile.binary)
        return 127
    if raw or os.environ.get('TERM') == 'dumb' or not (os.isatty(0) and os.isatty(1)):
        os.execvpe(binary, [binary] + app_args, os.environ)
    mode = profile.classify(app_args)
    if mode == 'direct':
        os.execvpe(binary, [binary] + app_args, os.environ)
    prompt = profile.has_prompt(app_args)
    launcher = Launcher(profile, binary, app_args, opts,
                        strict=(mode == 'overlay' or prompt),
                        play_intro=(mode == 'intro' and not prompt))
    try:
        return launcher.start()
    except SystemExit:
        raise
    except BaseException:
        if not hasattr(launcher, 'pid'):
            if os.environ.get('AGENT_THEME_DEBUG'):
                import traceback
                traceback.print_exc()
            # Fail open: if the PTY setup did not start, run the app untouched.
            os.execvpe(binary, [binary] + app_args, os.environ)
        raise


if __name__ == '__main__':
    sys.exit(main())
