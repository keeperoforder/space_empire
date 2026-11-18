"""Camera transform with smooth movement and zoom."""
from __future__ import annotations

import math
import pygame

import config


class Camera:
    def __init__(self) -> None:
        self.position = pygame.Vector2(0.0, 0.0)
        self.target = pygame.Vector2(0.0, 0.0)
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.smoothing = 8.0

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        direction = pygame.Vector2(
            float(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - float(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            float(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - float(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.target += direction * (config.CAMERA_MOVE_SPEED * dt / self.zoom)

        # Frame-rate-independent exponential smoothing.
        blend = 1.0 - math.exp(-self.smoothing * dt)
        self.position += (self.target - self.position) * blend
        self.zoom += (self.target_zoom - self.zoom) * blend

    def move(self, dx: float, dy: float) -> None:
        self.target.x += dx / self.zoom
        self.target.y += dy / self.zoom

    def add_zoom(self, amount: float) -> None:
        self.target_zoom = max(
            config.CAMERA_MIN_ZOOM,
            min(config.CAMERA_MAX_ZOOM, self.target_zoom + amount),
        )

    def world_to_screen(
        self, point: tuple[float, float], size: tuple[int, int],
        parallax: float = 1.0
    ) -> tuple[int, int]:
        center = pygame.Vector2(size[0] / 2, size[1] / 2)
        relative = (pygame.Vector2(point) - self.position * parallax) * self.zoom
        result = center + relative
        return round(result.x), round(result.y)

    def screen_to_world(
        self, point: tuple[int, int], size: tuple[int, int]
    ) -> pygame.Vector2:
        center = pygame.Vector2(size[0] / 2, size[1] / 2)
        return (pygame.Vector2(point) - center) / self.zoom + self.position
