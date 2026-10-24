"""Command-line surface for agent-bloom."""
import os
import shutil
import subprocess
import sys

from . import __version__
from .apps import PROFILES
from .launcher import Launcher
from .themes import DEFAULT_THEME, THEME_NAMES, get_theme

VERSION = __version__


ELEMENT_FLAGS = {
    '--logo': ('logo', True), '--no-logo': ('logo', False),
    '--header': ('header', True), '--no-header': ('header', False),
    '--title': ('title', True), '--no-title': ('title', False),
    '--home': ('home', True), '--no-home': ('home', False),
    '--ambient': ('ambient', True), '--no-ambient': ('ambient', False),
}

HELP = """agent-bloom %s - Built-in terminal themes for Claude Code and Codex CLI.

Usage:
  agent-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
  agent-bloom [--theme NAME] --list

Elements (defaults: logo=on header=on title=off home=on ambient=on):
  --theme NAME            Built-in theme name; huawei is default. See --list.
  --animation SELECTION   One animation, comma-separated candidates, or random.
                          Defaults: huawei=bloom; apple=random; others use their
                          selected entrance. Chosen once per
                          launch; comma lists choose one, not a playlist.
  --logo / --no-logo       Theme header badge. Does not change the home artwork.
  --header / --no-header   Theme header name.
  --title / --no-title     Window title. Off by default to keep tmux pane
                           titles searchable.
  --home / --no-home       Opening animation, ambient sweep and home. --no-home
                           disables the overlay; app settings stay unchanged.
  --ambient / --no-ambient Idle sweep. --no-ambient keeps the intro and static home.

Behavior:
  A fresh session plays the one-shot intro. Resuming, continuing, or passing
  an initial prompt skips it. The ambient sweep stops on submit and returns
  after /clear. Non-interactive commands bypass the wrapper.

Other:
  --list                   List themes and animations without launching an app.
  --raw                    Run the app untouched.
  --check                  Verify embedded patterns, engine, binary and version.
  -h, --help               Show this help.
  -V, --version            Show agent-bloom version.

--theme, --animation, --list, element flags, --raw and --check may appear before
or after the app name.
--help/--version are wrapper options only before the app. Use -- to pass any
flag with the same spelling to the app.

Exit status:
  0 success; 1 check failed; 2 usage error; 127 app missing;
  128+signal for signal termination; otherwise the app's exit status.
"""


def usage_error(message):
    sys.stderr.write('agent-bloom: %s\n' % message)
    sys.stderr.write("Try 'agent-bloom --help'.\n")
    raise SystemExit(2)


def list_themes(name=None):
    for key in (THEME_NAMES if name is None else (name,)):
        theme = get_theme(key)
        print('%s  %s  (default: %s)' % (key, theme.label, theme.default_animation))
        for animation in theme.animations:
            slogan = animation.slogan or theme.copy['claude']['slogan']
            print('  %-16s %-24s %s' % (animation.key, animation.label, slogan))


def parse(argv):
    app = None
    app_args = []
    overrides = []
    raw = check = False
    listing = False
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
            sys.stdout.write('agent-bloom %s\n' % VERSION)
            raise SystemExit(0)
        if a == '--theme' or a.startswith('--theme='):
            if a == '--theme':
                i += 1
                if i >= len(argv):
                    usage_error('--theme requires a name')
                name = argv[i]
            else:
                name = a.split('=', 1)[1]
            if name not in THEME_NAMES:
                usage_error('unknown theme %r; choose %s' % (name, ', '.join(THEME_NAMES)))
            overrides.append(('theme', name))
        elif a == '--animation' or a.startswith('--animation='):
            if a == '--animation':
                i += 1
                if i >= len(argv):
                    usage_error('--animation requires a selection')
                selection = argv[i]
            else:
                selection = a.split('=', 1)[1]
            overrides.append(('animation', selection))
        elif a == '--list':
            listing = True
        elif a in ELEMENT_FLAGS:
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
    if listing:
        if raw or check or app_args or any(key != 'theme' for key, _ in overrides):
            usage_error('--list accepts only --theme and an optional app name')
        if app is not None and app.lower() not in PROFILES:
            usage_error('unknown app %s' % app)
        list_themes(dict(overrides).get('theme'))
        raise SystemExit(0)
    if app is None:
        usage_error('missing app')
    app = app.lower()
    if app not in PROFILES:
        usage_error('unknown app %s' % app)
    if raw and check:
        usage_error('--raw and --check cannot be combined')
    opts = dict(overrides)
    try:
        get_theme(opts.get('theme', DEFAULT_THEME)).candidates(opts.get('animation'))
    except ValueError as exc:
        usage_error(str(exc))
    return app, app_args, overrides, raw, check


def engine_check(profile, theme=None):
    """Exercise the optional engine modules; fail-open code deserves a loud check."""
    rows = []
    theme = theme or get_theme()
    try:
        from . import art
        brand = theme.brands[profile.key]
        base = profile.overlay_type()
        ov = base(120, 32, brand, in_alt=True, reveal=False,
                  pal=art.palette(theme), strict=False)
        ov.note_input(b'check\r')
        rows.append(('overlay', ov.submitted, 'constructs; input tracked'))
    except Exception as exc:  # noqa: BLE001 - a check must report any failure
        rows.append(('overlay', False, '%s: %s' % (type(exc).__name__, exc)))
    try:
        from . import art
        brand = theme.brands[profile.key]
        count = [0] * 32
        for row in (1, 2, 3, 28, 29, 30, 31):
            count[row] = 1
        band = art.choose_band(brand, 120, 32, count)
        if band is None:
            ok = False
        else:
            lock, start, end = band
            scene = theme.create_scene(120, 32, art.palette(theme), brand,
                                lock=lock,
                                top=art.place(lock, start, end))
            ok = bool(scene.ok and scene.frame(1.0))
        rows.append(('scene', ok, 'frames' if ok else 'no mark'))
    except Exception as exc:  # noqa: BLE001
        rows.append(('scene', False, '%s: %s' % (type(exc).__name__, exc)))
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
        rows = profile.check(opts)
        theme = get_theme(opts['theme'])
        for key in theme.candidates(opts.get('animation')):
            _, selected = theme.select_animation(key)
            rows.extend(('%s/%s' % (key, name), ok, detail)
                        for name, ok, detail in engine_check(profile, selected))
        rows += binary_check(profile)
        rows.append(('theme', True, opts['theme']))
        rows.append(('home', True, 'on (background)' if opts['home'] else 'off'))
        rows.append(('ambient', True, 'on' if opts['home'] and opts['ambient']
                     else ('off' if opts['home'] else 'off (home disabled)')))
        print('agent-bloom %s check: %s' % (VERSION, app))
        ok = True
        for name, passed, detail in rows:
            print('  %-12s %-4s %s' % (name, 'ok' if passed else 'FAIL', detail))
            ok = ok and passed
        return 0 if ok else 1
    binary = shutil.which(profile.binary)
    if not binary:
        sys.stderr.write('agent-bloom: %s not found on PATH\n' % profile.binary)
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
