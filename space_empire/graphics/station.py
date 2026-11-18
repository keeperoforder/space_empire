"""Modular central station assembly, animation and selection rendering."""
from __future__ import annotations

import math
import pygame

from graphics import station_sprites
from graphics.asset_library import scaled_sprite


class StationModule:
    """A separately-rendered sprite attached to the station's local origin."""

    def __init__(self, name: str, image: pygame.Surface,
                 offset: tuple[float, float], *,
                 parallax: float = 1.0, rotation_speed: float = 0.0,
                 draw_order: int = 0) -> None:
        self.name = name
        self.image = image
        self.offset = pygame.Vector2(offset)
        self.parallax = parallax
        self.rotation_speed = rotation_speed
        self.rotation = 0.0
        self.draw_order = draw_order
        self.spawn_age = 99.0
        self.animation_phase = (sum(ord(ch) for ch in name) % 31) * 0.17

    def add_constructed_building(self, building_id: str, name: str, sprite_kind: str):
        """Attach a completed construction as a new visible station module."""
        index = self.constructed_count
        angle = index * 2.399963229728653  # golden-angle distribution
        ring = index // 6
        radius = 300 + ring * 105
        offset = (math.cos(angle) * radius, math.sin(angle) * radius * 0.72)
        image = station_sprites.make_building_sprite(sprite_kind)
        module = self.add_module(
            f"{building_id}_{index + 1}", image, offset,
            draw_order=7 + index
        )
        module.building_id = building_id
        module.display_name = name
        module.spawn_age = 0.0
        self.constructed_count += 1
        return module

    def upgrade_constructed_building(self, building_id: str):
        """Visually reinforce the first matching module after an upgrade."""
        for module in self.modules:
            if getattr(module, "building_id", None) == building_id:
                w, h = module.image.get_size()
                module.image = pygame.transform.scale(
                    module.image, (max(1, int(w * 1.08)), max(1, int(h * 1.08)))
                )
                return True
        return False

    @property
    def visual_scale(self):
        # Each completed module slightly enlarges the assembled station silhouette.
        return 1.0 + min(0.55, self.constructed_count * 0.045)

    def update(self, dt: float) -> None:
        self.rotation = (self.rotation + self.rotation_speed * dt) % 360.0


class SpaceStation:
    """Station root positioned in world space; modules use core-relative offsets."""

    def __init__(self, position: tuple[float, float] = (0, 0)) -> None:
        self.position = pygame.Vector2(position)
        self.selected = False
        self.elapsed = 0.0
        self.modules: list[StationModule] = []
        self.constructed_count = 0
        self._build_initial_station()

    def _build_initial_station(self) -> None:
        # The opening state is a damaged command core and inert wreckage only.
        # No solar arrays, engines, hangars or functional production modules exist.
        self.damaged = True
        self.add_module("broken_truss", station_sprites.make_truss(), (0, 8),
                        draw_order=0)
        self.add_module("command_core", station_sprites.make_core(), (0, 0),
                        draw_order=5)
        self.add_module("broken_antenna", station_sprites.make_antenna(),
                        (34, -86), rotation_speed=2.2, draw_order=6)

    def add_module(self, name: str, image: pygame.Surface,
                   offset: tuple[float, float], **kwargs) -> StationModule:
        """Attach a new independently-rendered sprite relative to the core."""
        module = StationModule(name, image, offset, **kwargs)
        self.modules.append(module)
        self.modules.sort(key=lambda item: item.draw_order)
        return module

    def add_constructed_building(self, building_id: str, name: str, sprite_kind: str):
        """Attach a completed construction as a new visible station module."""
        index = self.constructed_count
        angle = index * 2.399963229728653  # golden-angle distribution
        ring = index // 6
        radius = 300 + ring * 105
        offset = (math.cos(angle) * radius, math.sin(angle) * radius * 0.72)
        image = station_sprites.make_building_sprite(sprite_kind)
        module = self.add_module(
            f"{building_id}_{index + 1}", image, offset,
            draw_order=7 + index
        )
        module.building_id = building_id
        module.display_name = name
        module.spawn_age = 0.0
        self.constructed_count += 1
        return module

    def upgrade_constructed_building(self, building_id: str):
        """Visually reinforce the first matching module after an upgrade."""
        for module in self.modules:
            if getattr(module, "building_id", None) == building_id:
                w, h = module.image.get_size()
                module.image = pygame.transform.scale(
                    module.image, (max(1, int(w * 1.08)), max(1, int(h * 1.08)))
                )
                return True
        return False

    @property
    def visual_scale(self):
        # Each completed module slightly enlarges the assembled station silhouette.
        return 1.0 + min(0.55, self.constructed_count * 0.045)

    def update(self, dt: float) -> None:
        self.elapsed += dt
        for module in self.modules:
            module.update(dt)
            module.spawn_age = min(99.0, module.spawn_age + dt)

    def _screen_center(self, camera, surface: pygame.Surface) -> tuple[int, int]:
        return camera.world_to_screen(self.position, surface.get_size())

    def _station_bounds(self, camera, surface: pygame.Surface) -> pygame.Rect:
        center = pygame.Vector2(self._screen_center(camera, surface))
        # Conservative selection bounds around the complete assembled station.
        expansion = self.visual_scale
        half_w = int((310 + self.constructed_count * 28) * camera.zoom * expansion)
        half_h = int((180 + self.constructed_count * 20) * camera.zoom * expansion)
        return pygame.Rect(
            round(center.x - half_w), round(center.y - half_h),
            max(1, half_w * 2), max(1, half_h * 2)
        )

    def contains_screen_point(self, point: tuple[int, int],
                              camera, surface: pygame.Surface) -> bool:
        return self._station_bounds(camera, surface).inflate(18, 18).collidepoint(point)

    def draw(self, surface: pygame.Surface, camera) -> None:
        center = pygame.Vector2(self._screen_center(camera, surface))
        zoom = camera.zoom

        # Selected halo sits behind all modules.
        bounds = self._station_bounds(camera, surface)
        if self.selected:
            halo_bounds = bounds.inflate(int(42 * zoom), int(26 * zoom))
            # Allocate only the local halo area rather than a full-window alpha surface.
            glow = pygame.Surface((max(1, halo_bounds.width), max(1, halo_bounds.height)), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(self.elapsed * 2.4)
            color = (65, 190, 255, int(22 + pulse * 22))
            outer = pygame.Rect(0, 0, halo_bounds.width, halo_bounds.height)
            pygame.draw.ellipse(glow, color, outer, 0)
            inner = outer.inflate(-int(32 * zoom), -int(18 * zoom))
            pygame.draw.ellipse(
                glow, (87, 207, 255, int(90 + pulse * 70)),
                inner, max(1, int(2 * zoom))
            )
            surface.blit(glow, halo_bounds.topleft)

        # Energy shimmer under the propulsion units.
        engine_pulse = 0.65 + 0.35 * math.sin(self.elapsed * 7.0)
        for local_x, local_y in ((-91, 106), (91, -46)):
            ex, ey = camera.world_to_screen(
                (self.position.x + local_x, self.position.y + local_y),
                surface.get_size()
            )
            flame_length = max(3, int((17 + 9 * engine_pulse) * zoom))
            flame_width = max(2, int(9 * zoom))
            flame = pygame.Surface(
                (flame_width * 2 + 8, flame_length + 8), pygame.SRCALPHA
            )
            pygame.draw.polygon(
                flame, (54, 174, 255, 45),
                [(flame_width + 4, 0), (2, flame_length),
                 (flame_width + 4, flame_length - 4),
                 (flame_width * 2 + 6, flame_length)]
            )
            pygame.draw.polygon(
                flame, (110, 225, 255, 155),
                [(flame_width + 4, 2), (flame_width, flame_length - 4),
                 (flame_width + 4, flame_length - 8),
                 (flame_width * 2 + 4, flame_length - 4)]
            )
            surface.blit(flame, flame.get_rect(center=(ex, ey)))

        if getattr(self, "damaged", False):
            # Keep the emergency spark animation initialized before its first use.
            spark = 0.5 + 0.5 * math.sin(self.elapsed * 8.0)
            # Nearby cargo-ship wreckage is the visible target of the one-shot salvage tutorial.
            wreck_center = camera.world_to_screen(
                (self.position.x + 430, self.position.y + 95), surface.get_size()
            )
            wx, wy = wreck_center
            hull = [
                (wx - int(42 * zoom), wy - int(13 * zoom)),
                (wx - int(12 * zoom), wy - int(28 * zoom)),
                (wx + int(39 * zoom), wy - int(8 * zoom)),
                (wx + int(31 * zoom), wy + int(17 * zoom)),
                (wx - int(23 * zoom), wy + int(23 * zoom)),
            ]
            pygame.draw.polygon(surface, (57, 77, 94), hull)
            pygame.draw.lines(surface, (128, 157, 177), True, hull,
                              max(1, int(2 * zoom)))
            pygame.draw.line(surface, (191, 91, 73),
                             (wx - int(15 * zoom), wy - int(18 * zoom)),
                             (wx + int(8 * zoom), wy + int(12 * zoom)),
                             max(1, int(2 * zoom)))
            for dx, dy, radius in ((-52, -24, 5), (47, 25, 7), (8, -38, 4)):
                pygame.draw.circle(surface, (91, 111, 126),
                                   (wx + int(dx * zoom), wy + int(dy * zoom)),
                                   max(2, int(radius * zoom)))
            pygame.draw.circle(surface, (255, 129, 76), (wx, wy),
                               max(2, int((2 + 2 * spark) * zoom)))

        # Draw every module independently. Nearest-neighbour scaling preserves pixel edges.
        for module in self.modules:
            world = self.position + module.offset * self.visual_scale
            px, py = camera.world_to_screen(world, surface.get_size(),
                                            module.parallax)
            image = module.image
            if module.rotation:
                image = pygame.transform.rotate(image, module.rotation)
            age = module.spawn_age
            reveal = min(1.0, age / 0.9)
            pulse = 0.5 + 0.5 * math.sin(self.elapsed * 4.0 + module.animation_phase)
            scale_factor = (0.82 + 0.18 * reveal) if age < 0.9 else 1.0
            target_size = (
                max(1, round(image.get_width() * zoom * self.visual_scale * scale_factor)),
                max(1, round(image.get_height() * zoom * self.visual_scale * scale_factor))
            )
            if target_size != image.get_size():
                image = pygame.transform.scale(image, target_size)
            surface.blit(image, image.get_rect(center=(px, py)))

            if module.name == "broken_antenna":
                # Rotating radar sweep around the dish; geometry stays pixel-crisp.
                sweep = self.elapsed * 1.05
                dish_x = px
                dish_y = py - int(34 * zoom * self.visual_scale)
                reach = max(4, int(24 * zoom * self.visual_scale))
                end = (dish_x + int(math.cos(sweep) * reach),
                       dish_y + int(math.sin(sweep) * reach * 0.42))
                pygame.draw.line(surface, (78, 205, 245), (dish_x, dish_y),
                                 end, max(1, int(2 * zoom)))
                pygame.draw.circle(surface, (160, 235, 255), end,
                                   max(1, int(2 * zoom)))

            # Solar modules get a restrained moving specular sweep across their cells.
            if getattr(module, "building_id", None) and "solar" in module.building_id:
                sweep_x = int((0.5 + 0.5 * math.sin(self.elapsed * 0.8 + module.animation_phase)) * 34)
                sx = px + int((sweep_x - 17) * zoom * self.visual_scale)
                sy = py - int(19 * zoom * self.visual_scale)
                pygame.draw.line(surface, (111, 220, 255), (sx, sy),
                                 (sx, sy + max(2, int(24 * zoom))), 1)

            # Newly completed modules rise into view with a short expanding beacon.
            if age < 1.25:
                frame = min(7, max(0, int((age / 1.25) * 8)))
                effect_size = max(12, int(112 * zoom * self.visual_scale))
                effect = scaled_sprite("effects", f"construction_{frame:02d}.png",
                                       (effect_size, effect_size))
                surface.blit(effect, effect.get_rect(center=(px, py)))

        if getattr(self, "damaged", False):
            # Visible fractures and intermittent emergency sparks around the core.
            crack_color = (190, 83, 73)
            crack_paths = [
                [(-44, -18), (-28, -5), (-34, 12), (-18, 25)],
                [(38, -26), (25, -8), (39, 7), (30, 24)],
                [(-8, 42), (3, 28), (15, 36)],
            ]
            for path in crack_paths:
                points = []
                for ox, oy in path:
                    sx, sy = camera.world_to_screen(
                        (self.position.x + ox, self.position.y + oy),
                        surface.get_size()
                    )
                    points.append((sx, sy))
                if len(points) > 1:
                    pygame.draw.lines(surface, crack_color, False, points,
                                      max(1, int(2 * zoom)))
            if spark > 0.82:
                sx, sy = camera.world_to_screen(
                    (self.position.x + 56, self.position.y - 34),
                    surface.get_size()
                )
                pygame.draw.circle(surface, (255, 126, 76), (sx, sy),
                                   max(2, int(4 * zoom)))

        # Pulsing blue emergency lights on the command module.
        pulse = 0.72 + 0.28 * math.sin(self.elapsed * 3.5)
        light_color = (int(65 * pulse), int(190 * pulse), int(240 * pulse))
        for local in ((-42, 28), (42, 28), (0, -12)):
            lx, ly = camera.world_to_screen(
                (self.position.x + local[0], self.position.y + local[1]),
                surface.get_size()
            )
            r = max(1, round(3 * zoom))
            pygame.draw.rect(surface, light_color, (lx-r, ly-r, r*2+1, r*2+1))
            if math.sin(self.elapsed * 5.5 + local[0]) > 0.15:
                pygame.draw.circle(surface, (140, 235, 255), (lx, ly),
                                   max(1, int(5 * zoom)), 1)

        if self.selected:
            pygame.draw.rect(
                surface, (95, 205, 255),
                self._station_bounds(camera, surface), max(1, int(2 * zoom)), 5
            )
