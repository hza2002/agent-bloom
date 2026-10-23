"""Apple artwork and complete, internally maintained animation variants."""
import json
from importlib.resources import files

from . import Animation, Theme


def load_art():
    return json.loads(files('agent_theme.themes').joinpath('assets/apple.json').read_text(encoding='utf-8'))


def spectrum(*args, **kwargs):
    from .apple_motion import Spectrum
    return Spectrum(*args, **kwargs)


def constellation(*args, **kwargs):
    from .apple_motion import Constellation
    return Constellation(*args, **kwargs)


THEME = Theme(
    key='apple', label='Apple', load_art=load_art, create_scene=spectrum,
    dark={'ink': (241, 243, 247), 'soft': (190, 196, 207), 'muted': (125, 133, 147),
          'accent': (148, 179, 240), 'bg': (14, 15, 18)},
    light={'ink': (29, 29, 31), 'soft': (73, 78, 89), 'muted': (111, 116, 128),
           'accent': (61, 89, 158), 'bg': (250, 250, 250)},
    copy={
        'claude': dict(header='AppleClaude', title='Apple · Claude',
                       slogan='Choose your superpower', tagline='Think different',
                       platform='Apple silicon · macOS'),
        'codex': dict(header='Apple Codex', title='Apple · Codex',
                      slogan='Choose your superpower', tagline='Think different',
                      platform='Apple silicon · macOS'),
    },
    # Nerd Font fa-apple, in the same one-cell slot used by Huawei's flower.
    header_icon='\uf179', header_colour=(148, 179, 240), mini_shrink=1.0,
    animations=(
        Animation('spectrum', 'Six-colour assembly', spectrum),
        Animation('constellation', 'Particle convergence', constellation),
    ),
    default_animation='random',
)
