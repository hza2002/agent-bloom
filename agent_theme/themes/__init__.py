"""Explicit registry of project-owned themes. No dynamic imports or user plugins."""
from dataclasses import dataclass, replace
from functools import cached_property, lru_cache
import random
from typing import Callable


@dataclass(frozen=True)
class Brand:
    key: str
    theme: 'Theme'
    header: str
    title: str
    slogan: str
    tagline: str
    platform: str

    @property
    def sizes(self):
        return self.theme.art.get('slogans', {}).get(self.key, {}).get('sizes', ())


@dataclass(frozen=True)
class Animation:
    key: str
    label: str
    create_scene: Callable
    load_art: Callable = None
    slogan: str = None
    tagline: str = None


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    load_art: Callable
    create_scene: Callable
    dark: dict
    light: dict
    copy: dict
    header_icon: str
    header_colour: tuple
    header_fallback: tuple = ()
    mini_shrink: float = 0.75
    animations: tuple = ()
    default_animation: str = 'bloom'

    def candidates(self, selector=None):
        """Validate the whole candidate list without loading artwork or choosing."""
        selector = self.default_animation if selector is None else selector
        names = tuple(animation.key for animation in self.animations)
        if selector == 'random':
            return names
        selected = tuple(dict.fromkeys(part.strip() for part in selector.split(',')))
        if not selected or any(name not in names for name in selected):
            raise ValueError('invalid animation selection %r for %s; choose %s or random'
                             % (selector, self.key, ', '.join(names)))
        return selected

    def select_animation(self, selector=None):
        """Resolve once per launch; scenes and static artwork share this snapshot."""
        candidates = self.candidates(selector)
        key = candidates[0] if len(candidates) == 1 else random.choice(candidates)
        animation = next(item for item in self.animations if item.key == key)
        copy = {app: dict(values) for app, values in self.copy.items()}
        for values in copy.values():
            for field in ('slogan', 'tagline'):
                value = getattr(animation, field)
                if value is not None:
                    values[field] = value
        return key, replace(self, create_scene=animation.create_scene,
                            load_art=animation.load_art or self.load_art, copy=copy)

    @cached_property
    def art(self):
        return self.load_art()

    @cached_property
    def brands(self):
        return {key: Brand(key, self, **copy) for key, copy in self.copy.items()}


THEME_NAMES = ('huawei', 'apple')
DEFAULT_THEME = 'huawei'


@lru_cache(maxsize=len(THEME_NAMES))
def get_theme(name=DEFAULT_THEME):
    if name == 'huawei':
        from .huawei import THEME
    elif name == 'apple':
        from .apple import THEME
    else:
        raise ValueError('unknown built-in theme: ' + str(name))
    return THEME
