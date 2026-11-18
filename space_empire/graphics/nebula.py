"""Procedural nebula clouds, generated once and rendered with parallax."""
from __future__ import annotations

import math
import random
import pygame


class Nebula:
    def __init__(self, width: int, height: int, seed: int = 91) -> None:
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.clouds = []
        palette = [
            (38, 35, 105), (24, 67, 105), (77, 35, 100),
            (26, 76, 91), (86, 43, 83)
        ]
        for _ in range(13):
            self.clouds.append({
                "x": self.rng.uniform(-width * 0.8, width * 1.8),
                "y": self.rng.uniform(-height * 0.8, height * 1.8),
                "rx": self.rng.randint(130, 330),
                "ry": self.rng.randint(75, 190),
                "color": self.rng.choice(palette),
                "phase": self.rng.uniform(0, math.tau),
            })

        # Pre-render soft cloud sprites; avoids expensive blur work every frame.
        self.sprites = [self._make_cloud(c) for c in self.clouds]
        # Cache scaled variants by a quantized zoom level. This avoids
        # resampling every cloud on every frame while the camera eases.
        self._scaled_cache: dict[tuple[int, int], pygame.Surface] = {}

    @staticmethod
    def _make_cloud(cloud: dict) -> pygame.Surface:
        rx, ry = cloud["rx"], cloud["ry"]
        sprite = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
        base = cloud["color"]
        # Multi-lobed gas volumes and filament wisps are baked once per scene.
        rng = random.Random(int(cloud["x"] * 13 + cloud["y"] * 7) & 0xffffffff)
        for index in range(12, 0, -1):
            factor = index / 12
            rect = pygame.Rect(int(rx*(1-factor)), int(ry*(1-factor)),
                               int(rx*2*factor), int(ry*2*factor))
            alpha = int(2 + (12-index)*1.25)
            pygame.draw.ellipse(sprite, (*base, alpha), rect)
        for _ in range(7):
            ox=rng.randint(-rx//2,rx//2); oy=rng.randint(-ry//2,ry//2)
            rw=rng.randint(max(12,rx//5),max(13,rx//2))
            rh=rng.randint(max(8,ry//7),max(9,ry//3))
            tint=tuple(min(255,int(c*1.25)) for c in base)
            pygame.draw.ellipse(sprite,(*tint,8),
                                (rx+ox-rw//2,ry+oy-rh//2,rw,rh),max(1,rx//100))
        # Dusty star knots inside the nebula silhouette.
        for _ in range(18):
            sx=rng.randrange(2,rx*2-2); sy=rng.randrange(2,ry*2-2)
            pygame.draw.circle(sprite,(145,190,235,rng.randint(18,48)),(sx,sy),1)
        return sprite

    def draw(self, surface: pygame.Surface, camera, elapsed: float) -> None:
        size = surface.get_size()
        zoom_bucket = max(1, round(camera.zoom * 20))
        effective_zoom = zoom_bucket / 20.0

        for index, (cloud, sprite) in enumerate(zip(self.clouds, self.sprites)):
            px, py = camera.world_to_screen(
                (cloud["x"], cloud["y"]), size, parallax=0.16
            )
            cache_key = (index, zoom_bucket)
            scaled = self._scaled_cache.get(cache_key)
            if scaled is None:
                scaled = pygame.transform.smoothscale(
                    sprite,
                    (max(1, int(sprite.get_width() * effective_zoom)),
                     max(1, int(sprite.get_height() * effective_zoom)))
                )
                self._scaled_cache[cache_key] = scaled
            surface.blit(scaled, scaled.get_rect(center=(px, py)))
