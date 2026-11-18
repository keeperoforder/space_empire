# Space Empire — UI та графічне оновлення

## Зміни

- Верхня панель: індивідуальні векторні піктограми шести ресурсів, збільшені значення, контрастні кольори балансу, компактний поділ виробництва/споживання за наявності місця.
- Ліве меню: виразніші іконкові комірки, активний стан, hover-стан, помітніше блокування та збережені підказки/навігація.
- Центральна станція: додані дрібні піксельні деталі броні, заклепки, сервісні лінії, попереджувальні маркери та індикатори стикування.
- Права панель: покращена ієрархія, кольорові індикатори та компактні прогрес-бари.
- Журнал подій: окремий рядок заголовка, кольорові маркери повідомлень та розділювачі.
- Спільна тема: глибша графітово-синя основа, яскравіший бірюзовий контур і багатошарові рамки.

## Межі змін

Ігрові механіки, ціни, прогресія, маршрути подій та API панелей не змінювалися. Оновлено лише промальовування й спільні стилі; додано статичні регресійні перевірки UI API.

## Перевірки

- `compileall`: PASS.
- Автоматичні тести: 145/145 PASS.
- Python AST: 82/82 PASS.
- JSON: 13/13 PASS.
- ZIP integrity: PASS.
- Pygame відсутній у цьому середовищі. Реальний графічний запуск, наведення курсора, кліки та перевірка FPS не виконувалися. Перевірки UI взаємодії обмежені статичними тестами збереження API.

## Повний код змінених файлів

### `ui/theme.py`
```python
"""Shared visual language and layout constants for the Space Empire HUD."""
import pygame

BG = (5, 10, 22)
PANEL = (8, 18, 34)
PANEL_ALT = (12, 27, 47)
PANEL_HOVER = (20, 45, 70)
BORDER = (39, 88, 121)
BORDER_BRIGHT = (63, 180, 224)
CYAN = (75, 218, 250)
CYAN_DIM = (42, 123, 161)
TEXT = (218, 234, 247)
MUTED = (132, 164, 190)
GREEN = (89, 222, 164)
GOLD = (244, 190, 91)
RED = (245, 105, 113)
PURPLE = (177, 145, 255)

def panel(surface, rect, fill=PANEL, border=BORDER, radius=8, width=1):
    # Layered inset edge gives panels a more finished instrument-console look.
    pygame.draw.rect(surface, (4, 9, 19), rect.inflate(2, 2), border_radius=radius + 1)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)
    if rect.width > 28 and rect.height > 28:
        pygame.draw.line(surface, (25, 53, 76),
                         (rect.x + 12, rect.y + 1), (rect.right - 12, rect.y + 1), 1)


def resource_glyph(surface, center, color, kind, radius=11):
    """Small crisp vector glyphs used by the resource strip."""
    x, y = center
    pygame.draw.circle(surface, (12, 31, 49), (x, y), radius + 3)
    pygame.draw.circle(surface, color, (x, y), radius, 1)
    if kind == "metal":
        pygame.draw.line(surface, color, (x-5, y-4), (x+4, y-4), 2)
        pygame.draw.line(surface, color, (x-5, y), (x+5, y), 2)
        pygame.draw.line(surface, color, (x-3, y+4), (x+4, y+4), 2)
    elif kind == "energy":
        pygame.draw.polygon(surface, color, [(x+1,y-8),(x-5,y+1),(x-1,y+1),(x-3,y+8),(x+6,y-3),(x+2,y-3)])
    elif kind == "crystals":
        pygame.draw.polygon(surface, color, [(x,y-8),(x+6,y-1),(x+3,y+7),(x-4,y+6),(x-7,y-1)], 2)
        pygame.draw.line(surface, color, (x,y-7), (x,y+6), 1)
    elif kind == "fuel":
        pygame.draw.polygon(surface, color, [(x,y-8),(x+5,y),(x+4,y+5),(x,y+8),(x-4,y+5),(x-5,y)])
        pygame.draw.line(surface, color, (x,y-3), (x+2,y+2), 2)
    elif kind == "credits":
        pygame.draw.circle(surface, color, (x,y), 6, 2)
        pygame.draw.line(surface, color, (x-3,y), (x+3,y), 1)
        pygame.draw.line(surface, color, (x,y-4), (x,y+4), 1)
    elif kind == "science":
        pygame.draw.circle(surface, color, (x,y), 2)
        pygame.draw.ellipse(surface, color, (x-8,y-3,16,6), 1)
        pygame.draw.ellipse(surface, color, (x-3,y-8,6,16), 1)

def font(size, bold=False):
    return pygame.font.SysFont("consolas", size, bold=bold)

def label(surface, text, pos, size=15, color=TEXT, bold=False):
    surface.blit(font(size, bold).render(str(text), True, color), pos)

def fit_text(text, max_chars):
    text = str(text)
    return text if len(text) <= max_chars else text[:max(1, max_chars - 1)] + "…"

```

### `ui/top_bar.py`
```python
"""Live resource strip with detailed per-resource hover information."""
import pygame
from ui import theme


class TopBar:
    HEIGHT = 66
    RESOURCE_ORDER = ("metal", "energy", "crystals", "fuel", "credits", "science")

    def __init__(self, resource_manager, progression=None):
        self.resource_manager = resource_manager
        self.progression = progression
        self.resource_rects = {}

    @staticmethod
    def _format_amount(value):
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 10_000:
            return f"{value / 1_000:.1f}K"
        if value >= 1_000:
            return f"{value / 1_000:.2f}K"
        return f"{value:.1f}".rstrip("0").rstrip(".")

    @staticmethod
    def _rate(value):
        return f"{value:+.2f}/с"

    def tooltip_text(self, key):
        r = self.resource_manager.get(key)
        return (
            f"{r.name} | Запас: {r.amount:,.1f} / {r.capacity:,.1f} | "
            f"Виробництво: +{r.production:.2f}/с | "
            f"Споживання: -{r.consumption:.2f}/с | Баланс: {self._rate(r.balance)}"
        )

    def handle_event(self, event, tooltip):
        if event.type == pygame.MOUSEMOTION:
            for key, rect in self.resource_rects.items():
                if rect.collidepoint(event.pos):
                    tooltip.set(self.tooltip_text(key), event.pos)
                    return
            # Do not clear a tooltip owned by another HUD element.
            if tooltip.text and tooltip.text.split(" | ", 1)[0] in (
                self.resource_manager.get(k).name for k in self.RESOURCE_ORDER
            ):
                tooltip.text = None

    def draw(self, surface):
        w = surface.get_width()
        rect = pygame.Rect(12, 10, w - 24, self.HEIGHT)
        theme.panel(surface, rect, fill=(7, 17, 33), border=theme.BORDER_BRIGHT)
        theme.label(surface, "SPACE EMPIRE", (28, 17), 20, theme.CYAN, True)
        theme.label(surface, "COMMAND NETWORK  •  SECTOR 07", (29, 43), 9, theme.MUTED)
        pygame.draw.line(surface, (26, 64, 91), (28, 60), (190, 60), 1)

        start_x = min(320, max(235, int(w * 0.205)))
        right_x = w - 166
        available = max(480, right_x - start_x - 10)
        cell_w = available / len(self.RESOURCE_ORDER)
        self.resource_rects.clear()
        for i, key in enumerate(self.RESOURCE_ORDER):
            resource = self.resource_manager.get(key)
            x = int(start_x + i * cell_w)
            cell = pygame.Rect(x - 7, 14, max(50, int(cell_w - 3)), 56)
            self.resource_rects[key] = cell
            if i:
                pygame.draw.line(surface, (31, 75, 103), (x - 12, 20), (x - 12, 61), 1)

            theme.resource_glyph(surface, (x + 9, 38), resource.color, key, 10)
            theme.label(surface, resource.name.upper(), (x + 26, 16), 8, theme.MUTED, True)
            theme.label(surface, self._format_amount(resource.amount), (x + 26, 28),
                        17, theme.TEXT, True)

            balance_color = theme.GREEN if resource.balance > 0.001 else (
                theme.RED if resource.balance < -0.001 else theme.MUTED)
            theme.label(surface, self._rate(resource.balance), (x + 26, 49),
                        9, balance_color, True)
            # Tiny production/consumption split is available at a glance.
            if cell_w >= 150 and (resource.production > 0 or resource.consumption > 0):
                split = f"ВИР +{resource.production:.1f}  СПОЖ -{resource.consumption:.1f}"
                theme.label(surface, split, (x + 87, 51), 7, theme.MUTED)

        commander_x = w - 151
        pygame.draw.line(surface, theme.BORDER, (commander_x - 13, 20),
                         (commander_x - 13, 61), 1)
        theme.label(surface, "COMMANDER", (commander_x, 14), 8, theme.MUTED, True)
        level = int(getattr(self.progression, "commander_level", 1))
        xp = int(getattr(self.progression, "commander_xp", 0))
        theme.label(surface, f"LEVEL {level:02d}", (commander_x, 28), 13, theme.GREEN, True)
        theme.label(surface, f"XP {xp}", (commander_x, 46), 8, theme.MUTED)

```

### `ui/sidebar.py`
```python
"""Progression-aware vertical navigation; preserves the original sidebar layout."""
import pygame
from ui import theme


class Sidebar:
    WIDTH = 190
    ITEMS = [
        ("⌂", "Огляд"), ("▦", "Будівництво"), ("✥", "Флот"),
        ("⛏", "Видобуток"), ("⌬", "Дослідження"), ("◉", "Планети"),
        ("✧", "Галактична карта"), ("⇄", "Торгівля"), ("⚙", "Автоматизація"),
        ("✦", "Кампанія"), ("✚", "Прогрес"), ("⬡", "Оборона"),
        ("⚙", "Налаштування"),
    ]

    def __init__(self, progression=None, event_log=None):
        self.active = "Огляд"
        self.rects = {}
        self.hovered = None
        self.progression = progression
        self.event_log = event_log
        self._states = {}
        self._pulse = {}
        self._pulse_clock = 0.0
        if progression:
            self._states = {name: progression.section_state(name)[0]
                            for _, name in self.ITEMS}

    def _state(self, name):
        if name == "Прогрес":
            return "AVAILABLE", ""
        if self.progression is None:
            return "AVAILABLE", ""
        return self.progression.section_state(name)

    def update(self, dt):
        self._pulse_clock += max(0.0, float(dt))
        for name in list(self._pulse):
            self._pulse[name] = max(0.0, self._pulse[name] - max(0.0, float(dt)))
            if self._pulse[name] <= 0:
                del self._pulse[name]
        if not self.progression:
            return
        for _, name in self.ITEMS:
            state, _ = self._state(name)
            previous = self._states.get(name, state)
            if previous == "LOCKED" and state in ("AVAILABLE", "COMPLETED"):
                self._pulse[name] = 3.0
                if self.event_log:
                    self.event_log.push(f"НОВИЙ РОЗДІЛ ВІДКРИТО: {name.upper()}")
            self._states[name] = state

    def handle_event(self, event, tooltip):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = None
            for name, rect in self.rects.items():
                if rect.collidepoint(event.pos):
                    self.hovered = name
                    state, reason = self._state(name)
                    if state == "LOCKED":
                        tooltip.set(f"{name} — ЗАБЛОКОВАНО: {reason}", event.pos)
                    else:
                        tooltip.set(f"{name} — {state}", event.pos)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.rects.items():
                if rect.collidepoint(event.pos):
                    return name
        return None

    def draw(self, surface):
        x, y = 12, 86
        h = surface.get_height()
        panel_h = max(360, h - 190)
        rect = pygame.Rect(x, y, self.WIDTH, panel_h)
        theme.panel(surface, rect, fill=(8, 18, 33))
        theme.label(surface, "NAVIGATION", (x + 16, y + 15), 11, theme.MUTED, True)
        self.rects.clear()
        item_y = y + 43
        item_h = min(47, max(26, (panel_h - 105) // len(self.ITEMS)))
        for icon, name in self.ITEMS:
            r = pygame.Rect(x + 8, item_y, self.WIDTH - 16, item_h - 4)
            self.rects[name] = r
            state, _ = self._state(name)
            locked = state == "LOCKED"
            completed = state == "COMPLETED"
            pulse = self._pulse.get(name, 0.0)
            if name == self.active:
                pygame.draw.rect(surface, (17, 53, 77), r, border_radius=5)
                pygame.draw.rect(surface, theme.CYAN, (r.x, r.y + 5, 3, r.height - 10))
                pygame.draw.rect(surface, theme.BORDER_BRIGHT, r, 1, border_radius=5)
            elif pulse > 0:
                alpha = int(65 + 80 * (0.5 + 0.5 * __import__("math").sin(self._pulse_clock * 7)))
                glow = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                glow.fill((35, 190, 220, alpha))
                surface.blit(glow, r.topleft)
                pygame.draw.rect(surface, theme.CYAN, r, 1, border_radius=5)
            elif self.hovered == name:
                pygame.draw.rect(surface, (15, 36, 56) if not locked else (15, 25, 39),
                                 r, border_radius=5)
                pygame.draw.rect(surface, (48, 103, 132) if not locked else (47, 62, 78),
                                 r, 1, border_radius=5)
            if locked:
                color = (67, 83, 101)
                label_color = (76, 91, 108)
            elif completed:
                color = theme.GREEN
                label_color = theme.GREEN
            else:
                color = theme.CYAN if name == self.active or pulse > 0 else theme.MUTED
                label_color = theme.TEXT if name == self.active or pulse > 0 else theme.MUTED
            icon_box = pygame.Rect(r.x + 7, r.y + 6, 25, r.height - 12)
            pygame.draw.rect(surface, (10, 31, 48) if not locked else (13, 23, 36),
                             icon_box, border_radius=4)
            theme.label(surface, icon, (icon_box.x + 5, icon_box.y + 1), 17, color, True)
            theme.label(surface, name, (r.x + 40, r.y + 9), 13,
                        label_color, name == self.active or completed)
            if locked:
                # Locked entries stay legible but visibly inactive.
                lx, ly = r.right - 21, r.y + 9
                pygame.draw.arc(surface, (80, 96, 112), (lx + 3, ly, 9, 10), 0, 3.14, 2)
                pygame.draw.rect(surface, (80, 96, 112), (lx, ly + 6, 15, 11), border_radius=2)
                pygame.draw.circle(surface, (28, 39, 53), (lx + 7, ly + 11), 1)
            elif completed:
                theme.label(surface, "✓", (r.right - 22, r.y + 8), 14, theme.GREEN, True)
            item_y += item_h
        bottom = pygame.Rect(x + 8, y + panel_h - 44, self.WIDTH - 16, 32)
        pygame.draw.line(surface, theme.BORDER, (bottom.x + 3, bottom.y),
                         (bottom.right - 3, bottom.y), 1)
        pygame.draw.circle(surface, theme.GREEN, (bottom.x + 10, bottom.y + 16), 3)
        theme.label(surface, "SYSTEMS NOMINAL", (bottom.x + 20, bottom.y + 10),
                    9, theme.GREEN, True)

```

### `ui/right_panel.py`
```python
"""Contextual information panel for the selected station or HUD section."""
import pygame
from ui import theme

class RightPanel:
    WIDTH = 260

    def __init__(self):
        self.slide = 0.0
        self.target = 1.0
        self.section = "Огляд"

    def set_section(self, section):
        self.section = section
        self.target = 1.0

    def update(self, dt):
        self.slide += (self.target - self.slide) * min(1.0, dt * 8.0)

    def draw(self, surface, station_selected):
        w, h = surface.get_size()
        x = w - self.WIDTH - 12
        y = 86
        panel_h = max(360, h - 190)
        # Slight slide from the right edge.
        x += int((1.0 - self.slide) * (self.WIDTH + 20))
        r = pygame.Rect(x, y, self.WIDTH, panel_h)
        theme.panel(surface, r, fill=(7, 17, 32), border=theme.BORDER_BRIGHT)
        theme.label(surface, "TACTICAL DATA", (x + 16, y + 15), 10, theme.MUTED, True)
        pygame.draw.line(surface, theme.BORDER, (x + 14, y + 40), (x + self.WIDTH - 14, y + 40))
        title = "ОРБІТАЛЬНА СТАНЦІЯ" if self.section == "Огляд" else self.section.upper()
        theme.label(surface, title, (x + 16, y + 55), 14, theme.CYAN, True)
        if self.section == "Огляд":
            theme.label(surface, "STATION • ATLAS-01", (x + 16, y + 83), 11, theme.TEXT, True)
            theme.label(surface, "Статус", (x + 16, y + 116), 11, theme.MUTED)
            pygame.draw.circle(surface, theme.GREEN, (x + 132, y + 121), 4)
            theme.label(surface, "ONLINE", (x + 143, y + 114), 10, theme.GREEN, True)
            stats = [("◈  Корпус", "94%", .94, theme.GREEN),
                     ("ϟ  Енергосистема", "87%", .87, theme.CYAN),
                     ("♙  Екіпаж", "128 / 150", 128/150, theme.PURPLE),
                     ("▦  Модулі", "10", .66, theme.GOLD)]
            sy = y + 148
            for name, value, ratio, tint in stats:
                theme.label(surface, name, (x + 16, sy), 11, theme.MUTED)
                theme.label(surface, value, (x + 151, sy), 11, theme.TEXT, True)
                track = pygame.Rect(x + 16, sy + 19, self.WIDTH - 32, 5)
                pygame.draw.rect(surface, (22, 39, 57), track, border_radius=3)
                pygame.draw.rect(surface, tint,
                                 (track.x, track.y, max(2, int(track.width * ratio)), track.height),
                                 border_radius=3)
                sy += 48
            pygame.draw.line(surface, theme.BORDER, (x + 15, sy), (x + self.WIDTH - 15, sy))
            theme.label(surface, "ENERGY OUTPUT", (x + 16, sy + 18), 10, theme.MUTED, True)
            pygame.draw.rect(surface, (24, 43, 60), (x + 16, sy + 39, self.WIDTH - 32, 8), border_radius=4)
            pygame.draw.rect(surface, theme.CYAN, (x + 16, sy + 39, int((self.WIDTH - 32) * .78), 8), border_radius=4)
            theme.label(surface, "78%", (x + self.WIDTH - 48, sy + 55), 11, theme.CYAN, True)
        else:
            theme.label(surface, "РОЗДІЛ У РОЗРОБЦІ", (x + 16, y + 91), 12, theme.GOLD, True)
            lines = ["Інтерфейс розділу активний.",
                     "Ігрові механіки будуть",
                     "підключені на наступних",
                     "етапах розробки."]
            for i, line in enumerate(lines):
                theme.label(surface, line, (x + 16, y + 125 + i * 23), 12, theme.MUTED)
            theme.panel(surface, pygame.Rect(x + 16, y + 245, self.WIDTH - 32, 62),
                        fill=(10, 27, 44), border=theme.BORDER, radius=5)
            pygame.draw.circle(surface, theme.GOLD, (x + 29, y + 274), 4)
            theme.label(surface, "MODULE STATUS", (x + 42, y + 254), 8, theme.MUTED, True)
            theme.label(surface, "IN DEVELOPMENT", (x + 42, y + 271), 10, theme.GOLD, True)

```

### `ui/bottom_bar.py`
```python
"""Bottom event feed and notification strip."""
import pygame
from ui import theme

class BottomBar:
    HEIGHT = 78

    def __init__(self):
        self.messages = [
            ("13:42", "Станція Atlas-01 працює у штатному режимі.", theme.GREEN),
            ("13:39", "Сканування сектору завершено.", theme.CYAN),
            ("13:31", "Енергетичні резерви стабільні.", theme.GOLD),
        ]

    def push(self, message, color=None):
        self.messages.insert(0, ("NOW", message, color or theme.CYAN))
        self.messages = self.messages[:5]

    def draw(self, surface):
        w, h = surface.get_size()
        rect = pygame.Rect(12, h - self.HEIGHT - 10, w - 24, self.HEIGHT)
        theme.panel(surface, rect, fill=(7, 17, 32), border=theme.BORDER_BRIGHT)
        theme.label(surface, "EVENT LOG", (rect.x + 15, rect.y + 9), 9, theme.MUTED, True)
        pygame.draw.line(surface, theme.BORDER, (rect.x + 14, rect.y + 27),
                         (rect.right - 14, rect.y + 27), 1)
        available = max(1, (w - 80) // 3)
        for i, (stamp, message, color) in enumerate(self.messages[:3]):
            x = rect.x + 15 + i * available
            if i:
                pygame.draw.line(surface, (24, 49, 70), (x - 10, rect.y + 36),
                                 (x - 10, rect.bottom - 10), 1)
            pygame.draw.circle(surface, color, (x + 4, rect.y + 49), 3)
            theme.label(surface, stamp, (x + 14, rect.y + 42), 9, color, True)
            theme.label(surface, theme.fit_text(message, max(16, available // 9)),
                        (x + 62, rect.y + 41), 10, theme.TEXT)

```

### `graphics/station_sprites.py`
```python
"""Procedural pixel-art sprite factory for the central space station.

Each factory returns an independent transparent sprite. These placeholders can
later be replaced with PNG assets while keeping the station assembly API.
"""
import pygame


def _surface(size):
    return pygame.Surface(size, pygame.SRCALPHA)


def make_core():
    s = _surface((190, 132))
    # Rear silhouette and layered armor.
    pygame.draw.rect(s, (20, 31, 49), (20, 25, 150, 82))
    pygame.draw.rect(s, (75, 94, 116), (27, 20, 136, 91))
    pygame.draw.rect(s, (35, 51, 72), (35, 13, 120, 105))
    pygame.draw.rect(s, (115, 133, 150), (48, 18, 94, 91))
    pygame.draw.rect(s, (54, 73, 96), (55, 10, 80, 105))
    # Command bridge housing.
    pygame.draw.rect(s, (26, 43, 64), (57, 2, 76, 48))
    pygame.draw.rect(s, (100, 124, 145), (63, 0, 64, 43))
    pygame.draw.rect(s, (34, 55, 80), (69, 5, 52, 32))
    pygame.draw.rect(s, (74, 183, 220), (73, 9, 44, 22))
    pygame.draw.rect(s, (175, 235, 255), (78, 11, 8, 3))
    # Blue illuminated bridge windows.
    for x in (42, 60, 132, 150):
        pygame.draw.rect(s, (12, 27, 43), (x, 57, 12, 22))
        pygame.draw.rect(s, (49, 160, 205), (x + 2, 59, 8, 17))
        pygame.draw.rect(s, (157, 229, 255), (x + 2, 60, 2, 5))
    # Hull plating, vents and warning marks.
    for x in (34, 154):
        pygame.draw.rect(s, (139, 154, 166), (x, 35, 5, 35))
        pygame.draw.rect(s, (18, 27, 41), (x + 1, 83, 4, 17))
    for x in range(62, 130, 12):
        pygame.draw.rect(s, (24, 36, 52), (x, 91, 7, 5))
        pygame.draw.rect(s, (173, 187, 194), (x, 89, 7, 2))
    pygame.draw.rect(s, (220, 164, 66), (25, 104, 18, 4))
    pygame.draw.rect(s, (220, 164, 66), (147, 104, 18, 4))
    # Hard pixel highlights.
    pygame.draw.line(s, (202, 218, 225), (50, 19), (139, 19), 2)
    pygame.draw.line(s, (145, 166, 184), (39, 112), (151, 112), 2)
    # Extra pixel-art surface detail: armor seams, rivets and status lamps.
    for x in (31, 46, 144, 159):
        pygame.draw.rect(s, (28, 43, 59), (x, 29, 5, 4))
        pygame.draw.rect(s, (184, 201, 211), (x + 1, 30, 2, 2))
    for x in range(58, 134, 12):
        pygame.draw.line(s, (105, 126, 145), (x, 75), (x + 6, 75), 1)
        pygame.draw.rect(s, (19, 32, 48), (x, 80, 7, 5))
    # Amber hazard chevrons on the lower service deck.
    for x in (48, 132):
        pygame.draw.line(s, (238, 178, 76), (x, 101), (x + 7, 106), 2)
        pygame.draw.line(s, (238, 178, 76), (x + 7, 106), (x + 14, 101), 2)
    # Cool reactor glow and paired docking indicators.
    pygame.draw.rect(s, (18, 57, 79), (72, 35, 46, 2))
    pygame.draw.rect(s, (102, 225, 250), (75, 36, 40, 2))
    for x in (18, 166):
        pygame.draw.circle(s, (27, 54, 73), (x, 83), 5)
        pygame.draw.circle(s, (80, 210, 237), (x, 83), 2)
    return s


def make_truss():
    s = _surface((520, 34))
    pygame.draw.rect(s, (24, 37, 53), (0, 10, 520, 15))
    pygame.draw.rect(s, (100, 121, 139), (0, 9, 520, 5))
    pygame.draw.rect(s, (48, 68, 88), (0, 19, 520, 5))
    for x in range(8, 520, 24):
        pygame.draw.line(s, (145, 163, 174), (x, 10), (x + 15, 23), 2)
        pygame.draw.line(s, (57, 81, 103), (x + 15, 23), (x + 24, 10), 2)
        pygame.draw.rect(s, (189, 203, 208), (x, 7, 4, 4))
    return s


def make_solar_panel():
    s = _surface((150, 100))
    # Support arm.
    pygame.draw.rect(s, (107, 127, 145), (69, 43, 12, 55))
    pygame.draw.rect(s, (35, 53, 73), (72, 45, 6, 53))
    # Panel frame and individual photovoltaic cells.
    pygame.draw.rect(s, (156, 174, 183), (4, 3, 142, 70), 3)
    pygame.draw.rect(s, (15, 39, 72), (8, 7, 134, 62))
    for x in range(12, 143, 18):
        pygame.draw.rect(s, (31, 87, 139), (x, 10, 14, 56))
        pygame.draw.line(s, (79, 153, 202), (x + 2, 12), (x + 2, 63), 1)
    for y in (26, 46):
        pygame.draw.line(s, (119, 183, 216), (8, y), (142, y), 1)
    pygame.draw.rect(s, (193, 215, 221), (4, 3, 142, 3))
    return s


def make_docking_bay():
    s = _surface((124, 90))
    pygame.draw.rect(s, (22, 35, 52), (12, 9, 100, 69))
    pygame.draw.rect(s, (94, 113, 132), (19, 4, 86, 68))
    pygame.draw.rect(s, (36, 54, 75), (27, 10, 70, 55))
    pygame.draw.rect(s, (12, 23, 38), (39, 19, 46, 42))
    pygame.draw.rect(s, (55, 119, 151), (44, 23, 36, 34), 3)
    pygame.draw.rect(s, (14, 31, 48), (51, 30, 22, 21))
    pygame.draw.rect(s, (83, 197, 226), (55, 33, 14, 15))
    pygame.draw.rect(s, (194, 214, 218), (20, 68, 84, 5))
    for x in (25, 94):
        pygame.draw.rect(s, (224, 169, 71), (x, 56, 6, 8))
    return s


def make_antenna():
    s = _surface((76, 116))
    pygame.draw.rect(s, (78, 99, 117), (35, 48, 6, 66))
    pygame.draw.rect(s, (143, 160, 169), (31, 44, 14, 6))
    # Dish and feed arm.
    pygame.draw.arc(s, (170, 190, 202), pygame.Rect(5, 3, 62, 57),
                    0.35, 2.8, 4)
    pygame.draw.line(s, (125, 149, 166), (14, 22), (52, 50), 3)
    pygame.draw.circle(s, (77, 187, 224), (15, 22), 4)
    pygame.draw.circle(s, (199, 242, 255), (15, 22), 2)
    pygame.draw.rect(s, (221, 171, 76), (29, 67, 18, 4))
    return s


def make_engine():
    s = _surface((72, 64))
    pygame.draw.rect(s, (29, 43, 61), (5, 8, 62, 48))
    pygame.draw.rect(s, (104, 124, 143), (10, 4, 52, 40))
    pygame.draw.rect(s, (30, 48, 69), (16, 9, 40, 34))
    pygame.draw.rect(s, (13, 24, 39), (21, 15, 30, 25))
    pygame.draw.rect(s, (62, 164, 206), (25, 18, 22, 18))
    pygame.draw.rect(s, (177, 238, 255), (30, 20, 12, 13))
    pygame.draw.rect(s, (153, 171, 180), (3, 43, 66, 7))
    return s


def make_radiator():
    s = _surface((72, 62))
    pygame.draw.rect(s, (73, 91, 108), (30, 4, 12, 54))
    pygame.draw.rect(s, (24, 42, 59), (5, 9, 62, 44))
    for y in range(13, 52, 7):
        pygame.draw.rect(s, (118, 143, 157), (8, y, 56, 3))
        pygame.draw.line(s, (40, 70, 91), (8, y + 3), (64, y + 3), 1)
    return s


def make_building_sprite(kind):
    """Create a distinct pixel-art module sprite for a constructed building."""
    palettes = {
        "solar": ((20, 54, 88), (66, 170, 224), (174, 226, 245)),
        "smelter": ((65, 53, 43), (205, 123, 61), (255, 197, 112)),
        "crystal": ((39, 62, 82), (74, 195, 224), (191, 250, 255)),
        "fuel": ((62, 47, 76), (172, 115, 222), (226, 193, 255)),
        "hangar": ((38, 54, 70), (116, 153, 177), (191, 219, 231)),
        "lab": ((37, 57, 79), (86, 169, 213), (186, 231, 255)),
        "warehouse": ((57, 67, 78), (135, 157, 170), (211, 223, 226)),
        "habitat": ((43, 67, 65), (90, 174, 143), (185, 239, 208)),
        "defense": ((67, 45, 52), (199, 87, 91), (255, 178, 151)),
    }
    dark, main, light = palettes.get(kind, palettes["hangar"])
    s = _surface((132, 104))
    # Common docking collar and reinforced hull.
    pygame.draw.rect(s, (18, 29, 43), (8, 30, 116, 64))
    pygame.draw.rect(s, (82, 104, 121), (13, 25, 106, 63))
    pygame.draw.rect(s, dark, (19, 31, 94, 48))
    pygame.draw.rect(s, main, (25, 36, 82, 37))
    pygame.draw.rect(s, light, (29, 36, 74, 4))
    pygame.draw.rect(s, (24, 38, 53), (36, 48, 60, 20))
    if kind == "solar":
        for x in range(4, 128, 12):
            pygame.draw.rect(s, dark, (x, 5, 9, 22))
            pygame.draw.line(s, light, (x+2, 7), (x+2, 24), 1)
        pygame.draw.rect(s, light, (62, 27, 8, 14))
    elif kind == "smelter":
        for x in (39, 72, 96):
            pygame.draw.rect(s, (35, 40, 49), (x, 13, 12, 24))
            pygame.draw.rect(s, main, (x+3, 7, 6, 8))
        pygame.draw.polygon(s, light, [(53, 52), (66, 37), (79, 52), (66, 65)])
    elif kind == "crystal":
        pygame.draw.polygon(s, light, [(65, 7), (80, 31), (70, 51), (53, 31)])
        pygame.draw.polygon(s, main, [(65, 14), (73, 31), (67, 43), (59, 30)])
        pygame.draw.line(s, light, (65, 15), (65, 42), 2)
    elif kind == "fuel":
        for x in (40, 65, 90):
            pygame.draw.rect(s, dark, (x, 7, 17, 42), border_radius=4)
            pygame.draw.rect(s, light, (x+4, 13, 9, 24), border_radius=3)
            pygame.draw.rect(s, main, (x+2, 3, 13, 5))
    elif kind == "hangar":
        pygame.draw.rect(s, (13, 25, 40), (37, 37, 58, 38))
        pygame.draw.rect(s, light, (42, 42, 48, 28), 2)
        pygame.draw.polygon(s, main, [(66, 46), (78, 64), (54, 64)])
    elif kind == "lab":
        pygame.draw.rect(s, light, (54, 7, 25, 23), 2)
        pygame.draw.line(s, light, (66, 9), (66, 27), 2)
        pygame.draw.circle(s, main, (66, 18), 6)
        pygame.draw.rect(s, (12, 27, 42), (47, 49, 39, 16))
    elif kind == "warehouse":
        for x in (34, 55, 76, 97):
            pygame.draw.rect(s, light, (x, 43, 15, 24), 2)
            pygame.draw.line(s, light, (x+2, 49), (x+13, 49), 1)
    elif kind == "habitat":
        for x in (34, 58, 82):
            pygame.draw.rect(s, dark, (x, 8, 18, 30))
            pygame.draw.rect(s, light, (x+3, 12, 12, 10))
            pygame.draw.rect(s, main, (x+3, 25, 12, 8))
    elif kind == "defense":
        pygame.draw.rect(s, dark, (57, 7, 18, 32))
        pygame.draw.rect(s, light, (63, 0, 6, 18))
        pygame.draw.line(s, light, (66, 12), (39, 2), 4)
        pygame.draw.line(s, light, (66, 12), (93, 2), 4)
        pygame.draw.circle(s, main, (66, 20), 8)
    # Docking pylons, windows and status lamps.
    pygame.draw.rect(s, (155, 174, 184), (5, 72, 122, 5))
    for x in (31, 51, 81, 101):
        pygame.draw.rect(s, light, (x, 57, 7, 5))
    pygame.draw.rect(s, (83, 221, 177), (111, 32, 5, 5))
    return s

```

### `tests/test_ui_visual_upgrade.py`
```python
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def class_methods(relative_path, class_name):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


class UIVisualUpgradeRegressionTests(unittest.TestCase):
    def test_top_bar_keeps_resource_event_and_draw_api(self):
        methods = class_methods("ui/top_bar.py", "TopBar")
        self.assertTrue({"handle_event", "draw", "tooltip_text"} <= methods)

    def test_sidebar_keeps_navigation_and_hover_api(self):
        methods = class_methods("ui/sidebar.py", "Sidebar")
        self.assertTrue({"handle_event", "draw", "update"} <= methods)

    def test_right_and_bottom_panels_keep_draw_api(self):
        self.assertIn("draw", class_methods("ui/right_panel.py", "RightPanel"))
        self.assertIn("draw", class_methods("ui/bottom_bar.py", "BottomBar"))

    def test_resource_glyphs_cover_all_six_resource_types(self):
        source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
        for resource in ("metal", "energy", "crystals", "fuel", "credits", "science"):
            self.assertIn(f'kind == "{resource}"', source)

    def test_build_panel_and_hud_navigation_routes_remain(self):
        build_methods = class_methods("ui/build_panel.py", "BuildPanel")
        hud_methods = class_methods("ui/hud.py", "HUD")
        self.assertTrue({"open", "close", "handle_event", "draw"} <= build_methods)
        self.assertTrue({"handle_event", "draw", "update"} <= hud_methods)

    def test_station_core_sprite_factory_remains(self):
        source = (ROOT / "graphics" / "station_sprites.py").read_text(encoding="utf-8")
        self.assertIn("def make_core():", source)
        self.assertIn("Extra pixel-art surface detail", source)


if __name__ == "__main__":
    unittest.main()

```
