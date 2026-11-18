"""Composes the complete animated space environment."""
import math
import random
import pygame

import config
from graphics.camera import Camera
from graphics.starfield import Starfield
from graphics.nebula import Nebula
from graphics.celestial import CelestialSystem


class SpaceBackground:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.starfield = Starfield(width, height)
        self.nebula = Nebula(width, height)
        self.celestial = CelestialSystem()
        self.elapsed = 0.0
        rng = random.Random(404)
        self.dust = [
            [rng.uniform(0, width), rng.uniform(0, height),
             rng.uniform(5.0, 18.0), rng.uniform(0.5, 1.5),
             rng.uniform(0, math.tau)]
            for _ in range(44)
        ]

    def update(self, dt: float) -> None:
        dt = min(max(0.0, dt), 0.1)
        self.elapsed += dt
        self.starfield.update(dt)
        for particle in self.dust:
            particle[0] -= particle[2] * dt
            particle[1] += math.sin(self.elapsed * particle[3] + particle[4]) * 1.8 * dt
            if particle[0] < -4:
                particle[0] = self.width + 4
                particle[1] = (particle[1] + 137) % max(1, self.height)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.fill(config.BACKGROUND_COLOR)
        self.nebula.draw(surface, camera, self.elapsed)
        self.starfield.draw(surface, camera, self.elapsed)
        self.celestial.draw(surface, camera, self.elapsed)
        # Sparse foreground dust gives the scene a subtle sense of depth.
        for x, y, speed, frequency, phase in self.dust:
            px = int(x % max(1, surface.get_width()))
            py = int(y % max(1, surface.get_height()))
            twinkle = 0.45 + 0.35 * math.sin(self.elapsed * frequency + phase)
            shade = int(75 + 75 * twinkle)
            pygame.draw.circle(surface, (shade // 2, shade, min(255, shade + 35)),
                               (px, py), 1)
