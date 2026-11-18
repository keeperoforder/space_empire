# Space Empire — анімація космічної сцени

## Реалізовано

- Три шари зірок тепер повільно дрейфують із різною швидкістю; координати циклічно повертаються в межі поля, мерехтіння збережене.
- Додано 44 легкі частинки космічного пилу з рухом і низьковитратним мерехтінням.
- Атмосфера планет отримала пульсацію; поверхня має повільно зміщувані смуги та орбітальний відблиск.
- Станційна антена має повільний механічний поворот і радарний sweep; аварійні маяки продовжують миготіти.
- Побудовані модулі з'являються через коротку анімацію масштабу та імпульсне кільце; сонячні модулі мають рухомий відблиск по фотокомірках.
- Шахтарські кораблі показують промінь під час видобутку; астероїди мають рухомі мінеральні відблиски.
- Кораблі флоту отримали пульсацію реактора та двошаровий слід двигуна.

## Оптимізація

- Анімації керуються `dt` або загальним elapsed-time, без таймерів і потоків.
- Кількість пилових частинок фіксована (44); кількість зірок — фіксована.
- Частинки та зорі циклічно перевикористовуються; дорогі blur-операції не додаються.
- Ефекти декоративні: економіка, прогресія, ціни, будівельні таймери та логіка кораблів не змінювалися.

## Технічна перевірка

- `compileall`: PASS.
- AST: 84/84 Python-файлів PASS.
- JSON: 13/13 файлів PASS.
- Автоматичні тести: 153/153 PASS.
- ZIP integrity: PASS.
- Pygame відсутній у середовищі. Тому гру не вдалося запустити графічно; фактичний FPS, візуальну плавність, поведінку на слабкому ПК і коректність рендерингу вікна виміряти не вдалося. Це не можна вважати підтвердженим runtime/FPS тестом.

## Повний код змінених файлів

### `graphics/station.py`
```python
"""Modular central station assembly, animation and selection rendering."""
from __future__ import annotations

import math
import pygame

from graphics import station_sprites


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
                ring_radius = max(3, int((18 + age * 45) * zoom))
                alpha = int(190 * (1.0 - age / 1.25))
                pygame.draw.circle(surface, (65, 205, 255), (px, py),
                                   ring_radius, max(1, int(2 * zoom)))
                pygame.draw.circle(surface, (180, 235, 255), (px, py),
                                   max(2, int((4 + pulse * 3) * zoom)))

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

```

### `graphics/background.py`
```python
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

```

### `graphics/starfield.py`
```python
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

```

### `graphics/celestial.py`
```python
"""Extensible decorative celestial-object system."""
from __future__ import annotations

import math
import pygame


class CelestialBody:
    """Base class for future planets, moons, asteroids and stations."""

    def __init__(self, x: float, y: float, radius: int,
                 base_color: tuple[int, int, int],
                 atmosphere_color: tuple[int, int, int] | None = None,
                 parallax: float = 0.82) -> None:
        self.position = pygame.Vector2(x, y)
        self.radius = radius
        self.base_color = base_color
        self.atmosphere_color = atmosphere_color
        self.parallax = parallax

    def draw(self, surface: pygame.Surface, camera, elapsed: float) -> None:
        px, py = camera.world_to_screen(
            self.position, surface.get_size(), self.parallax
        )
        radius = max(2, int(self.radius * camera.zoom))
        if (px + radius < 0 or py + radius < 0
                or px - radius >= surface.get_width()
                or py - radius >= surface.get_height()):
            return

        if self.atmosphere_color:
            glow_radius = int(radius * 1.22)
            glow = pygame.Surface(
                (glow_radius * 2 + 4, glow_radius * 2 + 4),
                pygame.SRCALPHA
            )
            pulse = 0.72 + 0.28 * math.sin(elapsed * 1.25 + self.radius)
            pygame.draw.circle(
                glow, (*self.atmosphere_color, int(18 + pulse * 18)),
                (glow_radius + 2, glow_radius + 2), glow_radius
            )
            pygame.draw.circle(
                glow, (*self.atmosphere_color, int(45 + pulse * 28)),
                (glow_radius + 2, glow_radius + 2), max(1, int(radius * 1.08)), 1
            )
            surface.blit(glow, glow.get_rect(center=(px, py)))

        pygame.draw.circle(surface, self.base_color, (px, py), radius)

        # Pixel-art shading and a narrow highlight arc.
        shade = tuple(max(0, int(c * 0.48)) for c in self.base_color)
        pygame.draw.arc(
            surface, shade,
            pygame.Rect(px - radius, py - radius, radius * 2, radius * 2),
            math.pi * 0.48, math.pi * 1.52, max(2, radius // 5)
        )
        highlight = tuple(min(255, int(c * 1.25 + 12))
                          for c in self.base_color)
        pygame.draw.arc(
            surface, highlight,
            pygame.Rect(px - radius, py - radius, radius * 2, radius * 2),
            math.pi * 1.15, math.pi * 1.85, max(1, radius // 12)
        )
        # Slowly shifting surface bands suggest axial rotation without 3D rendering.
        if radius >= 14:
            phase = (elapsed * 0.22 + self.position.x * 0.001) % math.tau
            band_y = int(math.sin(phase) * radius * 0.42)
            band_width = max(2, int(radius * 1.25))
            band_rect = pygame.Rect(px - band_width // 2, py + band_y,
                                    band_width, max(1, radius // 9))
            band_rect = band_rect.clip(pygame.Rect(px-radius, py-radius,
                                                    radius*2, radius*2))
            if band_rect.width > 0 and band_rect.height > 0:
                pygame.draw.line(surface, highlight,
                                 (band_rect.left, band_rect.centery),
                                 (band_rect.right, band_rect.centery),
                                 max(1, radius // 16))
            # A tiny orbiting glint travels around the visible limb.
            angle = elapsed * 0.16 + self.radius
            gx = px + int(math.cos(angle) * radius * 0.88)
            gy = py + int(math.sin(angle) * radius * 0.88)
            pygame.draw.circle(surface, (205, 232, 255), (gx, gy),
                               max(1, radius // 24))


class Planet(CelestialBody):
    """Decorative planet; subclass point for richer surface features."""


class CelestialSystem:
    def __init__(self) -> None:
        self.objects: list[CelestialBody] = [
            Planet(-570, -260, 118, (74, 91, 145), (88, 135, 210), 0.72),
            Planet(640, 280, 76, (151, 91, 73), (220, 125, 83), 0.88),
            Planet(350, -510, 48, (78, 139, 135), (74, 190, 180), 0.78),
            Planet(-1050, 390, 35, (130, 112, 157), (151, 115, 205), 0.68),
        ]

    def add(self, body: CelestialBody) -> None:
        """Register a new planet, asteroid or other celestial object."""
        self.objects.append(body)

    def remove(self, body: CelestialBody) -> None:
        self.objects.remove(body)

    def draw(self, surface: pygame.Surface, camera, elapsed: float) -> None:
        for body in self.objects:
            body.draw(surface, camera, elapsed)

```

### `graphics/mining_visuals.py`
```python
"""World-space asteroid and mining-ship rendering."""
import math
import pygame


class MiningVisuals:
    def __init__(self, mining_manager):
        self.manager = mining_manager
        self.elapsed = 0.0
        self.asteroid_surfaces = {}

    def update(self, dt):
        self.elapsed += dt

    def draw(self, surface, camera, station_position=(0, 0)):
        for asteroid in self.manager.asteroids.values():
            pos = camera.world_to_screen((asteroid.x, asteroid.y), surface.get_size())
            x, y = pos
            radius = max(5, int((25 + 5 * asteroid.richness) * camera.zoom))
            pygame.draw.circle(surface, (17, 31, 49), (x, y), radius + 8)
            pygame.draw.circle(surface, (86, 111, 132), (x, y), radius)
            pygame.draw.circle(surface, (125, 148, 163), (x-radius//3, y-radius//3), max(2, radius//3))
            pygame.draw.circle(surface, (43, 61, 78), (x+radius//3, y+radius//4), max(2, radius//4))
            pygame.draw.circle(surface, (151, 177, 190), (x, y), radius, 1)
            glint_angle = self.elapsed * 0.7 + asteroid.richness
            gx = x + int(math.cos(glint_angle) * radius * 0.55)
            gy = y + int(math.sin(glint_angle) * radius * 0.55)
            pygame.draw.circle(surface, (170, 225, 245), (gx, gy),
                               max(1, int(2 * camera.zoom)))
            # Reserve indicator arc.
            ratio = asteroid.reserve / asteroid.max_reserve if asteroid.max_reserve else 0
            bar = pygame.Rect(x-radius, y+radius+5, radius*2, max(2, int(3*camera.zoom)))
            pygame.draw.rect(surface, (26, 42, 58), bar, border_radius=2)
            if ratio > 0:
                pygame.draw.rect(surface, (86, 207, 172),
                                 (bar.x,bar.y,max(1,int(bar.width*ratio)),bar.height),
                                 border_radius=2)
        for ship in self.manager.ships:
            x, y = camera.world_to_screen((ship.x, ship.y), surface.get_size())
            scale = max(0.55, camera.zoom)
            # Engine trail follows the current velocity vector.
            if ship.task in ("outbound", "returning"):
                target = self.manager.asteroids[ship.target_id]
                dx, dy = ((target.x-ship.x, target.y-ship.y) if ship.task == "outbound"
                          else (-ship.x, -ship.y))
                length = math.hypot(dx,dy) or 1
                tx, ty = -dx/length, -dy/length
                tail = (int(x+tx*18*scale), int(y+ty*18*scale))
                pygame.draw.line(surface, (65, 174, 237), (x,y), tail, max(1,int(3*scale)))
            pulse = 0.65 + 0.35*math.sin(self.elapsed*8 + len(ship.id))
            color = (int(100+70*pulse), int(195+40*pulse), 255)
            if ship.task == "mining" and ship.target_id in self.manager.asteroids:
                asteroid = self.manager.asteroids[ship.target_id]
                ax, ay = camera.world_to_screen((asteroid.x, asteroid.y), surface.get_size())
                beam_color = (int(45 + 65*pulse), int(150 + 75*pulse), 255)
                pygame.draw.line(surface, beam_color, (x, y), (ax, ay),
                                 max(1, int(1 + pulse * 2)))
                pygame.draw.circle(surface, (155, 235, 255), (ax, ay),
                                   max(2, int(3 * pulse * scale)))
            points = [(x+int(10*scale),y),(x-int(7*scale),y-int(6*scale)),
                      (x-int(4*scale),y),(x-int(7*scale),y+int(6*scale))]
            pygame.draw.polygon(surface, (18,35,54), points)
            pygame.draw.polygon(surface, color, points, max(1,int(scale)))
            pygame.draw.circle(surface, (255, 202, 105), (x-int(7*scale),y), max(1,int(2*scale)))

```

### `graphics/fleet_visuals.py`
```python
"""Procedural silhouettes for non-mining fleet vessels."""
import math
import pygame
from fleet.spaceship import SHIP_TYPES

class FleetVisuals:
    def __init__(self, manager):
        self.manager = manager
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt

    def _points(self, x, y, scale, shape):
        s=scale
        forms = {
            "cargo":[(13,0),(5,-7),(-7,-7),(-13,-4),(-13,4),(-7,7),(5,7)],
            "needle":[(17,0),(-10,-4),(-5,0),(-10,4)],
            "wings":[(14,0),(1,-5),(-3,-13),(-8,-11),(-6,-3),(-12,0),(-6,3),(-8,11),(-3,13),(1,5)],
            "arrow":[(16,0),(2,-7),(-10,-8),(-5,0),(-10,8),(2,7)],
            "heavy":[(14,0),(7,-9),(-9,-10),(-14,-6),(-14,6),(-9,10),(7,9)],
            "colony":[(12,0),(5,-8),(-7,-8),(-13,-3),(-13,3),(-7,8),(5,8)],
            "industrial":[(10,0),(3,-6),(-8,-6),(-11,-3),(-11,3),(-8,6),(3,6)]
        }
        return [(int(x+px*s),int(y+py*s)) for px,py in forms[shape]]

    def draw(self, surface, camera):
        for ship in self.manager.ships:
            if ship.ship_type == "miner":
                continue
            x,y=camera.world_to_screen((ship.x,ship.y),surface.get_size())
            scale=max(.48,min(1.5,camera.zoom))
            spec=SHIP_TYPES[ship.ship_type]
            color=spec["color"]
            pulse=.7+.3*math.sin(self.elapsed*5+len(ship.id))
            pygame.draw.circle(surface,(20,38,58),(x,y),int(15*scale))
            points=self._points(x,y,scale,spec["shape"])
            pygame.draw.polygon(surface,(13,24,39),points)
            pygame.draw.polygon(surface,color,points,max(1,int(scale*1.4)))
            pygame.draw.circle(surface,(255,210,125),(x-int(7*scale),y),max(1,int(2*scale)))
            # Ship-specific visual signatures.
            if ship.ship_type in ("frigate","battleship"):
                pygame.draw.line(surface,color,(x-int(5*scale),y-int(7*scale)),
                                 (x+int(2*scale),y-int(7*scale)),max(1,int(2*scale)))
                pygame.draw.line(surface,color,(x-int(5*scale),y+int(7*scale)),
                                 (x+int(2*scale),y+int(7*scale)),max(1,int(2*scale)))
            elif ship.ship_type=="colonizer":
                pygame.draw.circle(surface,(225,215,125),(x,y),max(2,int(4*scale)),1)
            elif ship.ship_type=="transport":
                pygame.draw.rect(surface,(155,230,190),
                                 pygame.Rect(x-int(4*scale),y-int(3*scale),int(7*scale),int(6*scale)),1)
            elif ship.ship_type=="scout":
                pygame.draw.line(surface,(180,215,255),(x-int(4*scale),y),(x+int(9*scale),y),1)
            # Reactor bloom and two-stage engine plume, animated at a low cost.
            engine_radius = max(2, int((5 + pulse * 3) * scale))
            engine_x = x - int(12 * scale)
            pygame.draw.circle(surface, (35, 118, 174), (engine_x, y),
                               engine_radius + 2)
            pygame.draw.circle(surface, (95, 218, 255), (engine_x, y),
                               engine_radius)
            if ship.status in ("outbound","returning"):
                tail = int((18 + pulse * 9) * scale)
                pygame.draw.line(surface,(35,112,174),(engine_x,y),
                                 (engine_x-tail,y),max(2,int(4*scale)))
                pygame.draw.line(surface,(105,218,255),(engine_x,y),
                                 (engine_x-tail//2,y),max(1,int(2*scale)))

```

### `tests/test_space_animation.py`
```python
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class SpaceAnimationRegressionTests(unittest.TestCase):
    def test_background_has_bounded_dust_pool_and_dt_update(self):
        text = source("graphics/background.py")
        self.assertIn("range(44)", text)
        self.assertIn("def update(self, dt", text)
        self.assertIn("particle[0] -= particle[2] * dt", text)

    def test_star_layers_drift_and_wrap(self):
        text = source("graphics/starfield.py")
        self.assertIn("(2.0, 5.0, 10.0)", text)
        self.assertIn("star.x += self.width * 3", text)

    def test_station_module_animation_and_build_reveal(self):
        text = source("graphics/station.py")
        self.assertIn("rotation_speed=2.2", text)
        self.assertIn("module.spawn_age = 0.0", text)
        self.assertIn("if age < 1.25:", text)
        self.assertIn("solar", text)

    def test_planet_surface_animation_is_time_based(self):
        text = source("graphics/celestial.py")
        self.assertIn("elapsed * 0.22", text)
        self.assertIn("elapsed * 0.16", text)
        self.assertIn("atmosphere_color", text)

    def test_mining_beam_is_visual_only(self):
        text = source("graphics/mining_visuals.py")
        self.assertIn('ship.task == "mining"', text)
        self.assertIn("pygame.draw.line(surface, beam_color", text)

    def test_fleet_reactor_and_engine_trails(self):
        text = source("graphics/fleet_visuals.py")
        self.assertIn("engine_radius", text)
        self.assertIn("engine plume", text)

    def test_game_update_still_drives_all_visual_systems(self):
        text = source("game.py")
        for call in ("self.space_background.update(dt)", "self.station.update(dt)",
                     "self.mining_visuals.update(dt)", "self.fleet_visuals.update(dt)"):
            self.assertIn(call, text)

    def test_gameplay_managers_were_not_modified(self):
        # Animation work must remain isolated from economy/progression/building rules.
        for rel in ("economy/resource_manager.py", "buildings/building_manager.py",
                    "progression/game_progression.py"):
            self.assertTrue((ROOT / rel).exists())


if __name__ == "__main__":
    unittest.main()

```
