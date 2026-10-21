"""App profiles: patterns, samples and per-CLI policies.

Everything that differs between Claude Code and Codex lives here.  The
profiles are data plus two small decisions (replacement bytes and argument
classification); the transport and drawing code do not know app names.
"""
import base64
import re

from . import i18n

# --------------------------------------------------------------------------- art

FLOWER_TOP = (
    b'\x1b[49m\x1b[22;38;2;175;27;31m \x1b[22;38;2;192;25;28m\xe2\x96\x97'
    b'\x1b[22;38;2;210;24;25m\xe2\x96\x97\x1b[22;38;2;222;54;50m\xe2\x96\x88'
    b'\x1b[22;38;2;231;99;86m \x1b[22;38;2;238;131;113m\xe2\x96\x88'
    b'\x1b[22;38;2;232;103;89m\xe2\x96\x96\x1b[22;38;2;223;59;53m\xe2\x96\x96')
FLOWER_MID = (
    b'\x1b[49m\x1b[22;38;2;165;28;33m\xe2\x96\x97\x1b[22;38;2;180;27;30m\xe2\x96\x88'
    b'\x1b[22;38;2;194;25;28m\xe2\x96\x99\x1b[22;38;2;207;24;25m\xe2\x96\x88'
    b'\x1b[22;38;2;215;25;25m \x1b[22;38;2;217;34;33m\xe2\x96\x88'
    b'\x1b[22;38;2;216;26;27m\xe2\x96\x9f\x1b[22;38;2;208;24;25m\xe2\x96\x88'
    b'\x1b[22;38;2;196;25;27m\xe2\x96\x96')
FLOWER_BOTTOM = (
    b'\x1b[49m\x1b[22;38;2;151;30;35m\xe2\x96\x9d\x1b[22;38;2;156;29;34m\xe2\x96\x9c'
    b'\x1b[22;38;2;166;28;32m\xe2\x96\x88\x1b[22;38;2;175;27;31m\xe2\x96\x98'
    b'\x1b[22;38;2;180;27;30m \x1b[22;38;2;182;27;30m\xe2\x96\x9d'
    b'\x1b[22;38;2;181;27;30m\xe2\x96\x88\x1b[22;38;2;176;27;31m\xe2\x96\x9b'
    b'\x1b[22;38;2;167;28;32m\xe2\x96\x98')

_FLOWER_CACHE = {}


def flower_rows():
    """Render the mini mark at runtime so it uses the same octant/quadrant table
    as the rest of the theme. The embedded rows are only a fallback."""
    global _FLOWER_CACHE
    try:
        from . import art
        key = art.glyph_mode()
        if key not in _FLOWER_CACHE:
            rows = art.mini_logo()
            _FLOWER_CACHE[key] = tuple(
                b'\x1b[49m' + art.render_run(
                    [(ch, rgb, False) for ch, rgb in cells[:width]]).encode('utf-8')
                for cells, width in zip(rows, (8, 9, 9)))
        return _FLOWER_CACHE[key]
    except Exception:
        return (FLOWER_TOP, FLOWER_MID, FLOWER_BOTTOM)


# --------------------------------------------------------------------------- samples

CLAUDE_SAMPLE = base64.b64decode(
    'GzcbW3IbOBtbPzI1aBtbPzIwMDRoG1s/MjAzMWgbWz8xMDA0aBtbPHUbWz41dRtbPjQ7Mm0bXTA7'
    '4pyzIENsYXVkZSBDb2RlBxtbPzEwNDloG1syShtbSBtbPHUbWz41dRtbPjQ7Mm0bWz8xMDAwaBtb'
    'PzEwMDJoG1s/MTAwM2gbWz8xMDA2aBtbPzI1bBtbPzI1bBtbSA0bWzFCG1s5MW0g4paQG1s0MG3i'
    'lpvilojilojilojilpvilogbWzEyRxtbMzltG1s0OW0bWzFtQ2xhdWRlIENvZGUbWzI0RxtbMjJt'
    'G1szODs1OzE0NG12Mi4xLjMwNQ0bWzFCG1s5MW3ilp3ilpwbWzQwbeKWiOKWiOKWiOKWiOKWiBtb'
    'NDlt4paI4paAG1sxMkcbWzM4OzU7MTQ0bUNsYXVkZSBDb2RlIMK3IHRlcm1pbmFsIGRlbW8NG1sx'
    'QhtbOTFtIOKWneKWnSAgIOKWneKWnSAbWzEyRxtbMzg7NTsxNDRtfi9wcm9qZWN0DRtbMTAzQxtb'
    'MjJC4peIIG1heCDCtyAvZWZmb3J0DRtbMUIbWzM4OzU7MTQ1beKUgOKUgOKUgOKUgOKUgOKUgOKU'
    'gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU'
    'gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU'
    'gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU')
CODEX_SAMPLE = base64.b64decode(
    'G1s/MjAwNGgbWz40OzBtG1s+NXUbWz40OzJtG1s/MTAwNGgbWzZuG10xMDs/G1wbXTExOz8bXBtb'
    'P3UbW2MbWz8yMDI2aBtbPzI1bBtbPzEwNDloG1s+NDswbRtbPjV1G1s+NDsybRtbPzEwMDdsG1s/'
    'MTAwMGgbWz8xMDAyaBtbPzEwMDNoG1s/MTAwNmgbWz8yNWwbWzE7MUgbW0obWz8yMDI2aBtbPzI1'
    'bBtbMjszSBtbMzg7Mjs5OTsxNjg7MjQ4OzQ5bT5fIBtbMW0bWzM5OzQ5bU9wZW5BSSBDb2RleBtb'
    'MjJtG1sybRtbMm0gKHYwLjE2My4wKRtbMzs2SGxvYWRpbmcbWzg7NTZI4qOA4qOk4qOk4qOk4qOA'
    '4qOAG1s5OzUzSOKjoOKjtuKjv+Kjv+Kjv+Kjv+Kjv+Kjv+Kjv+Kjv+KjpuKjpOKjpOKjpOKjpOKj'
    'pOKjpOKhgBtbMTA7NTFI4qKA4qO+4qO/4qO/4qC/4qCL4qCJ4qCJ4qKJ4qOt4qO/4qO/4qO/4qO/'
    '4qO/4qC/4qO/4qO/4qO/4qO/4qO34qOEG1sxMTs1MEjio4Dio77io7/io7/ioIMbWzExOzU2SOKj'
    'gOKj')
CODEX_TITLE_SAMPLE = base64.b64decode(
    'G10wO2RlbW8tc2Vzc2lvbgc=')
NOTICE = b"\x1b[38;5;174mAuto mode is now Claude Code's default permission mode."

# --------------------------------------------------------------------------- patterns

NEW_CLAUDE = i18n.BRAND_CLAUDE.encode()
NEW_CODEX = i18n.BRAND_CODEX.encode()
NEW_CODEX_TITLE = i18n.CODEX_TITLE.encode()

CLAUDE_HEADER = re.compile(
    rb'(\x1b\[39m\x1b\[49m\x1b\[1m)Claude Code')
CLAUDE_HEADER_CLASSIC = re.compile(
    rb'(\x1b\[39m\x1b\[49m\x1b\[1m)Claude\x1b\[\d+GCode')
CLAUDE_HEADER_COMPACT = re.compile(
    rb'(\x1b\[H\r(?:\x1b\[\d+C)?\x1b\[1B\x1b\[1m)Claude Code')
CLAUDE_TITLE = re.compile(rb'(\x1b\]0;[^\x07\x1b]{0,64}?)Claude Code')

COLOR = rb'\x1b\[(?:38;2;\d+;\d+;\d+|9[0-7])m'
BG = rb'\x1b\[(?:48;2;\d+;\d+;\d+|4[0-7])m'
CLAUDE_MASCOT = [
    (re.compile(COLOR + rb' \xe2\x96\x90(?:' + BG + rb')?'
                rb'\xe2\x96\x9b\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x9b\xe2\x96\x88'),
     FLOWER_TOP),
    (re.compile(COLOR + rb'\xe2\x96\x9d\xe2\x96\x9c(?:' + BG + rb')?'
                rb'(?:\xe2\x96\x88){5}(?:\x1b\[49m)?\xe2\x96\x88\xe2\x96\x80'),
     FLOWER_MID),
    (re.compile(COLOR + rb' \xe2\x96\x9d\xe2\x96\x9d(?:   |\x1b\[\d+G)\xe2\x96\x9d\xe2\x96\x9d ?'),
     FLOWER_BOTTOM),
]

CODEX_HEADER = re.compile(
    rb'(\x1b\[38;2;\d+;\d+;\d+(;49)?m)>_ ((?:\x1b\[[0-9;]*m)*)OpenAI Codex')
CODEX_TITLE = re.compile(rb'(\x1b\]0;)[^\x07\x1b]*(\x07|\x1b\\)')

# --------------------------------------------------------------------------- profiles

CLAUDE_DIRECT_FLAGS = {
    '-p', '--print', '-h', '--help', '-v', '--version', '--safe-mode', '--bare',
    '--bg', '--background', '--desktop', '--cloud', '--ax-screen-reader',
    '--output-format', '--input-format',
}
CLAUDE_DIRECT_SUBCOMMANDS = {
    'doctor', 'update', 'upgrade', 'install', 'auth', 'mcp', 'plugin', 'plugins',
    'project', 'agents', 'attach', 'logs', 'stop', 'kill', 'rm', 'respawn', 'gateway',
    'import', 'setup-token', 'config', 'migrate-installer', 'api-key', 'help',
}
CLAUDE_VALUE_FLAGS = {
    '--model', '--settings', '--setting-sources', '--add-dir', '--plugin-dir',
    '--mcp-config', '--append-system-prompt', '--system-prompt', '--permission-mode',
    '--allowedTools', '--allowed-tools', '--disallowedTools', '--disallowed-tools',
    '--agents', '--agent', '--session-id', '--fallback-model', '--debug-file',
    '--betas', '--name', '-n', '--effort', '--tools', '--max-turns', '--worktree', '-w',
}

CODEX_DIRECT_FLAGS = {'-h', '--help', '-V', '--version', '--no-alt-screen'}
CODEX_DIRECT_SUBCOMMANDS = {
    'agents', 'exec', 'e', 'review', 'login', 'logout', 'mcp', 'plugin', 'app-server',
    'remote-control', 'app', 'completion', 'update', 'doctor', 'sandbox', 'debug',
    'apply', 'a', 'queue', 'archive', 'delete', 'migrate-rollouts', 'unarchive',
    'cloud', 'exec-server', 'features', 'help', 'mcp-server', 'proto',
    'responses-api-proxy', 'stdio-to-uds', 'generate-ts',
}
CODEX_VALUE_FLAGS = {
    '-c', '--config', '--enable', '--disable', '--remote', '--remote-auth-token-env',
    '-i', '--image', '-m', '--model', '--local-provider', '-p', '--profile',
    '-s', '--sandbox', '-C', '--cd', '--add-dir', '-a', '--ask-for-approval',
}


class Profile:
    key = ''
    binary = ''
    defaults = {}
    starts = ()
    sample = b''
    version_marker = ''
    subcommands = frozenset()
    overlay_only = frozenset()
    direct_flags = frozenset()
    resume_flags = frozenset()
    value_flags = frozenset()
    home_top = 3

    def overlay_type(self):
        """The app's home-layout class, imported lazily so --help stays cheap."""
        raise NotImplementedError

    def _walk(self, argv):
        """Yield (index, arg, is_flag), skipping the values of value options."""
        i = 0
        while i < len(argv):
            a = argv[i]
            if a == '--':
                return
            if a.startswith('-') and len(a) > 1:
                yield i, a, True
                i += 2 if (a in self.value_flags and '=' not in a) else 1
                continue
            yield i, a, False
            i += 1

    def classify(self, argv):
        """'direct' (run untouched), 'overlay' (no intro) or 'intro'."""
        resume = False
        for _, a, is_flag in self._walk(argv):
            if is_flag:
                flag = a.split('=', 1)[0]
                if flag in self.direct_flags:
                    return 'direct'
                if flag in self.resume_flags:
                    resume = True
                continue
            if a in self.overlay_only:
                return 'overlay'
            if a in self.subcommands:
                return 'direct'
            break
        return 'overlay' if resume else 'intro'

    def has_prompt(self, argv):
        """True when the session opens with a prompt from the command line."""
        for _, a, is_flag in self._walk(argv):
            if not is_flag:
                return a not in self.subcommands and a not in self.overlay_only
        return '--' in argv and argv.index('--') + 1 < len(argv)

class Claude(Profile):
    key = 'claude'
    binary = 'claude'
    defaults = {'logo': True, 'header': True, 'title': False, 'home': True}
    starts = (b'\x1b[39m\x1b[49m\x1b[1mClaude',
              b'\x1b[H\r',
              b'\x1b]0;', b'\x1b[9', b'\x1b[38;2;')
    sample = CLAUDE_SAMPLE
    version_marker = 'Claude Code'
    subcommands = CLAUDE_DIRECT_SUBCOMMANDS
    direct_flags = CLAUDE_DIRECT_FLAGS
    value_flags = CLAUDE_VALUE_FLAGS
    overlay_only = frozenset()
    resume_flags = frozenset({'-c', '--continue', '-r', '--resume',
                              '--from-pr', '--teleport'})

    def overlay_type(self):
        from .overlay import ClaudeOverlay
        return ClaudeOverlay

    def replace(self, data, opts):
        if opts['header'] and b'Claude' in data:
            data = CLAUDE_HEADER.sub(lambda m: m.group(1) + NEW_CLAUDE, data)
            data = CLAUDE_HEADER_CLASSIC.sub(lambda m: m.group(1) + NEW_CLAUDE, data)
            data = CLAUDE_HEADER_COMPACT.sub(lambda m: m.group(1) + NEW_CLAUDE, data)
        if opts['title'] and b'Claude Code' in data:
            data = CLAUDE_TITLE.sub(lambda m: m.group(1) + NEW_CLAUDE, data)
        if opts['logo'] and b'\xe2\x96' in data:
            for (pattern, _), replacement in zip(CLAUDE_MASCOT, flower_rows()):
                data = pattern.sub(replacement, data)
        return data

    def check(self, opts):
        out = self.replace(self.sample, opts)
        rows = []
        if opts['logo']:
            n = sum(out.count(x) for x in flower_rows())
            rows.append(('logo', n == 3, 'flower rows %d/3' % n))
        else:
            rows.append(('logo', True, 'off'))
        if opts['header']:
            header_ok = b'\x1b[1m' + NEW_CLAUDE in out
            rows.append(('header', header_ok, 'Claude Code -> ' + i18n.BRAND_CLAUDE))
        else:
            rows.append(('header', True, 'off'))
        if opts['title']:
            m = re.search(rb'\x1b\]0;([^\x07\x1b]*)', out)
            title_ok = bool(m and NEW_CLAUDE in m.group(1))
            rows.append(('title', title_ok, 'title -> ' + i18n.BRAND_CLAUDE))
        else:
            rows.append(('title', True, 'off'))
        untouched = self.replace(NOTICE, opts) == NOTICE
        rows.append(('notice', untouched, 'unchanged' if untouched else 'CHANGED'))
        bold = b'\x1b[1mClaude Code in a plain transcript line'
        bold_ok = self.replace(bold, opts) == bold
        rows.append(('transcript', bold_ok, 'bold text untouched' if bold_ok else 'CHANGED'))
        compact = (b'\x1b[H\r\x1b[11C\x1b[1B\x1b[1mClaude Code'
                   b'\x1b[24G\x1b[22m')
        narrow = self.replace(compact, opts)
        if opts['header']:
            narrow_ok = NEW_CLAUDE in narrow
            narrow_detail = ('compact header -> ' + i18n.BRAND_CLAUDE
                             if narrow_ok else 'UNCHANGED')
        else:
            narrow_ok = narrow == compact
            narrow_detail = 'header off'
        rows.append(('narrow', narrow_ok, narrow_detail))
        return rows


class Codex(Profile):
    key = 'codex'
    binary = 'codex'
    defaults = {'logo': True, 'header': True, 'title': False, 'home': True}
    starts = (b'\x1b]0;', b'\x1b[9', b'\x1b[38;2;')
    sample = CODEX_TITLE_SAMPLE + CODEX_SAMPLE
    version_marker = 'codex'
    subcommands = CODEX_DIRECT_SUBCOMMANDS
    direct_flags = CODEX_DIRECT_FLAGS
    value_flags = CODEX_VALUE_FLAGS
    overlay_only = frozenset({'resume', 'fork'})
    resume_flags = frozenset()
    home_top = 10

    def overlay_type(self):
        from .overlay import CodexOverlay
        return CodexOverlay

    def _header(self, m, opts):
        suffix = m.group(2) or b''
        if opts['logo']:
            prefix = b'\x1b[38;2;232;52;60' + suffix + b'm\xe2\x9c\xbf '
            # `✿ ` is one cell narrower than `>_ `; keep the header's alignment.
            tail = b' '
        else:
            prefix = m.group(1) + b'>_ '
            tail = b''
        name = NEW_CODEX if opts['header'] else b'OpenAI Codex'
        return prefix + m.group(3) + name + tail

    def replace(self, data, opts):
        if (opts['logo'] or opts['header']) and b'OpenAI Codex' in data:
            data = CODEX_HEADER.sub(lambda m: self._header(m, opts), data)
        if opts['title'] and b'\x1b]0;' in data:
            data = CODEX_TITLE.sub(
                lambda m: m.group(1) + NEW_CODEX_TITLE + m.group(2), data)
        return data

    def check(self, opts):
        out = self.replace(self.sample, opts)
        rows = []
        if opts['logo'] or opts['header']:
            flower = b'\xe2\x9c\xbf ' in out
            name = NEW_CODEX in out
            old_name = b'OpenAI Codex' in out
            if opts['logo'] and opts['header']:
                ok = flower and name and not old_name
                detail = '✿ ... ' + i18n.BRAND_CODEX
            elif opts['logo']:
                ok = flower and old_name
                detail = '✿ OpenAI Codex'
            else:
                ok = not flower and name and not old_name
                detail = '>_ ' + i18n.BRAND_CODEX
            rows.append(('logo/header', ok, detail))
        else:
            rows.append(('logo', True, 'off'))
            rows.append(('header', True, 'off'))
        if opts['title']:
            rows.append(('title', NEW_CODEX_TITLE in out, 'title -> ' + i18n.BRAND_CODEX))
        else:
            rows.append(('title', True, 'off'))
        return rows


PROFILES = {'claude': Claude(), 'codex': Codex()}

