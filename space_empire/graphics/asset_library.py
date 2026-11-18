"""Central PNG sprite loader with alpha conversion, scaling and memory caches."""
from __future__ import annotations
from pathlib import Path
import pygame

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "sprites"
_IMAGE_CACHE: dict[str, pygame.Surface] = {}
_SCALE_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}


def load_sprite(category: str, name: str) -> pygame.Surface:
    key = f"{category}/{name}"
    if key not in _IMAGE_CACHE:
        path = ASSET_ROOT / category / name
        image = pygame.image.load(str(path))
        try:
            image = image.convert_alpha()
        except pygame.error:
            image = image.copy()
        _IMAGE_CACHE[key] = image
    return _IMAGE_CACHE[key]


def scaled_sprite(category: str, name: str, size: tuple[int, int]) -> pygame.Surface:
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    key = (f"{category}/{name}", w, h)
    if key not in _SCALE_CACHE:
        source = load_sprite(category, name)
        _SCALE_CACHE[key] = pygame.transform.smoothscale(source, (w, h))
    return _SCALE_CACHE[key]


def clear_scaled_cache() -> None:
    _SCALE_CACHE.clear()


def cache_stats() -> dict[str, int]:
    return {"images": len(_IMAGE_CACHE), "scaled": len(_SCALE_CACHE),
            "bytes": sum(s.get_pitch()*s.get_height() for s in _IMAGE_CACHE.values()) +
                     sum(s.get_pitch()*s.get_height() for s in _SCALE_CACHE.values())}
