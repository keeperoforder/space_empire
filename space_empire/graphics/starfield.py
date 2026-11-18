"""Deterministic multi-layer starfield with subtle twinkle and parallax."""
from __future__ import annotations

import math
import random
import pygame


class Star:
    __slots__ = ("x", "y", "radius", "brightness", "phase", "speed", "color")

    def __init__(self, rng: random.Random, width: int, height: int,
                 layer: int) -> None:
        self.x = rng.uniform(-width, width * 2)
        self.y = rng.uniform(-height, height * 2)
        self.radius = rng.choices(
            [1, 2, 3], weights=[76, 21, 3], k=1
        )[0] + (1 if layer == 2 and rng.random() < 0.12 else 0)
        self.brightness = rng.uniform(0.45, 1.0)
        self.phase = rng.uniform(0.0, math.tau)
        self.speed = rng.uniform(0.7, 2.2)
        palette = [(115, 150, 220), (170, 190, 235),
                   (255, 225, 190), (205, 220, 255)]
        self.color = rng.choice(palette)

    def draw(self, surface: pygame.Surface, camera, layer: int,
             elapsed: float) -> None:
        parallax = (0.10, 0.28, 0.58)[layer]
        px, py = camera.world_to_screen((self.x, self.y),
                                        surface.get_size(), parallax)
        # Twinkle is intentionally restrained to preserve pixel-art clarity.
        wave = 0.78 + 0.22 * math.sin(elapsed * self.speed + self.phase)
        intensity = max(0, min(255, int( self.brightness * wave * 255)))
        color = tuple(int(channel * intensity / 255) for channel in self.color)
        if -4 <= px < surface.get_width() + 4 and -4 <= py < surface.get_height() + 4:
            pygame.draw.circle(surface, color, (px, py), self.radius)
            if self.radius >= 3:
                pygame.draw.line(surface, color, (px - 3, py), (px + 3, py), 1)
                pygame.draw.line(surface, color, (px, py - 3), (px, py + 3), 1)


class Starfield:
    def __init__(self, width: int, height: int, seed: int = 17) -> None:
        self.width = width
        self.height = height
        rng = random.Random(seed)
        self.layers = [
            [Star(rng, width, height, layer) for _ in range(count)]
            for layer, count in enumerate((150, 95, 45))
        ]

    def update(self, dt: float) -> None:
        # Each depth layer drifts at a distinct, deliberately low speed.
        for layer_index, stars in enumerate(self.layers):
            drift = (2.0, 5.0, 10.0)[layer_index] * min(dt, 0.1)
            for star in stars:
                star.x -= drift
                if star.x < -self.width:
                    star.x += self.width * 3

    def draw(self, surface: pygame.Surface, camera, elapsed: float) -> None:
        for layer_index, stars in enumerate(self.layers):
            for star in stars:
                star.draw(surface, camera, layer_index, elapsed)
