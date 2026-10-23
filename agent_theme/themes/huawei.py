"""The original Huawei-style artwork, copy and Bloom scene."""
import json
from importlib.resources import files

from ..i18n import pick
from . import Animation, Theme


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


def load_art():
    return json.loads(files('agent_theme.themes').joinpath('assets/huawei.json').read_text(encoding='utf-8'))


def create_scene(*args, **kwargs):
    from .huawei_bloom import Bloom
    return Bloom(*args, **kwargs)


THEME = Theme(
    key='huawei', label='Huawei Bloom', load_art=load_art, create_scene=create_scene,
    dark={'ink': (238, 233, 228), 'soft': (196, 189, 184), 'muted': (128, 121, 119),
          'accent': (232, 52, 60), 'bg': (14, 15, 18)},
    light={'ink': (30, 26, 27), 'soft': (70, 64, 64), 'muted': (122, 116, 114),
           'accent': (199, 0, 11), 'bg': (250, 250, 250)},
    copy={
        'claude': dict(header=pick('盤古·Claude', '盘古·Claude'),
                       title=pick('盤古·Claude', '盘古·Claude'),
                       slogan=pick('從一行代碼，打開新的可能', '从一行代码，打开新的可能'),
                       tagline='MAKE IT POSSIBLE',
                       platform=pick('盤古大模型 · 昇騰計算平台', '盘古大模型 · 昇腾计算平台')),
        'codex': dict(header=pick('盤古 · Codex', '盘古 · Codex'),
                      title=pick('✿ 盤古 · Codex', '✿ 盘古 · Codex'),
                      slogan=pick('讓想法，碼上成真', '让想法，码上成真'),
                      tagline='CODE IT POSSIBLE',
                      platform=pick('盤古大模型 · 昇騰計算平台', '盘古大模型 · 昇腾计算平台')),
    },
    header_icon='\U000f0d08', header_colour=(232, 52, 60),
    header_fallback=(FLOWER_TOP, FLOWER_MID, FLOWER_BOTTOM),
    animations=(Animation('bloom', 'Petal bloom', create_scene),),
)
