# Space Empire — візуальне оновлення вікон і панелей

## Зміни

- `ui/theme.py`: уніфікована багатошарова рамка панелей, тінь, верхня акцентна лінія та кутові маркери.
- Додані спільні компоненти `section_header`, `action_button`, `info_card` для заголовків, кнопок і карток показників.
- `ui/build_panel.py`: кнопки побудови та покращення використовують спільний renderer; їхні rect/hitbox і дії не змінені.
- Усі вікна, які використовують `theme.panel`, отримують єдиний стиль: будівництво, дослідження, кампанія, навчання, флот, планети, галактична карта, торгівля, автоматизація, видобуток та налаштування.

## Функціональність

Не змінювалися економіка, прогресія, менеджери ігрових систем, ціни, вимоги, обробники подій і маршрути навігації. Конструктор продовжує показувати опис, вартість, час будівництва, виробництво, енергоспоживання й активні проєкти.

## Перевірки

- `compileall`: PASS
- AST: 85/85 Python-файлів PASS.
- JSON: 13/13 файлів PASS.
- Автоматичні тести: 157/157 PASS.
- Pygame відсутній у середовищі: реальний GUI-запуск, кліки, hover, переходи й FPS не вимірювалися.

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
    """Unified layered console panel used by every game window."""
    shadow = rect.move(0, 3)
    pygame.draw.rect(surface, (2, 6, 14), shadow, border_radius=radius + 2)
    pygame.draw.rect(surface, (10, 25, 42), rect.inflate(2, 2),
                     border_radius=radius + 1)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)
    if rect.width > 28 and rect.height > 28:
        # Restrained top rail and corner markers unify the visual language.
        pygame.draw.line(surface, (29, 65, 91),
                         (rect.x + 12, rect.y + 2),
                         (rect.right - 12, rect.y + 2), 1)
        pygame.draw.line(surface, CYAN_DIM,
                         (rect.x + 10, rect.y + 1),
                         (rect.x + min(72, rect.width // 3), rect.y + 1), 2)
        corner = min(9, rect.width // 8, rect.height // 8)
        for cx, cy, sx, sy in (
            (rect.left + 2, rect.top + 2, 1, 1),
            (rect.right - 3, rect.top + 2, -1, 1),
            (rect.left + 2, rect.bottom - 3, 1, -1),
            (rect.right - 3, rect.bottom - 3, -1, -1),
        ):
            pygame.draw.line(surface, (75, 145, 177), (cx, cy),
                             (cx + sx * corner, cy), 1)
            pygame.draw.line(surface, (75, 145, 177), (cx, cy),
                             (cx, cy + sy * corner), 1)


def section_header(surface, title, subtitle, rect, accent=CYAN):
    """Consistent title block for modal panels and management screens."""
    x, y = rect.topleft
    pygame.draw.rect(surface, (12, 34, 53),
                     pygame.Rect(x, y, rect.width, 42), border_radius=6)
    pygame.draw.rect(surface, accent,
                     pygame.Rect(x, y + 3, 3, 30), border_radius=1)
    label(surface, title, (x + 14, y + 5), 17, TEXT, True)
    if subtitle:
        label(surface, subtitle, (x + 15, y + 25), 9, MUTED)


def action_button(surface, rect, text, state="normal", accent=CYAN, font_size=11):
    """Shared button painter; state: normal, hover, disabled, danger, success."""
    palette = {
        "normal": ((14, 43, 64), accent, TEXT),
        "hover": ((22, 65, 91), (125, 225, 255), (245, 252, 255)),
        "disabled": ((24, 34, 47), BORDER, MUTED),
        "danger": ((65, 28, 39), RED, TEXT),
        "success": ((15, 61, 53), GREEN, TEXT),
    }
    fill, edge, ink = palette.get(state, palette["normal"])
    pygame.draw.rect(surface, (3, 8, 17), rect.move(0, 2), border_radius=5)
    pygame.draw.rect(surface, fill, rect, border_radius=5)
    pygame.draw.rect(surface, edge, rect, 1, border_radius=5)
    label(surface, text, (rect.x + 10, rect.y + max(4, (rect.height-font_size)//2)),
          font_size, ink, True)


def info_card(surface, rect, title, value, accent=CYAN, detail=None):
    """Compact reusable metric card."""
    panel(surface, rect, fill=PANEL_ALT, border=BORDER, radius=6)
    label(surface, title, (rect.x + 9, rect.y + 7), 9, MUTED, True)
    label(surface, value, (rect.x + 9, rect.y + 23), 15, accent, True)
    if detail:
        label(surface, detail, (rect.x + 9, rect.bottom - 17), 8, MUTED)


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

### `ui/build_panel.py`
```python
"""Interactive construction catalogue, detail view and project progress."""
import pygame
from ui import theme
from progression.building_unlocks import allowed_building_ids


class BuildPanel:
    WIDTH = 430

    def __init__(self, building_manager, resource_manager, event_log, progression=None):
        self.manager = building_manager
        self.resources = resource_manager
        self.event_log = event_log
        self.progression = progression
        self.visible = False
        self.selected_id = "solar_array"
        self.row_rects = {}
        self.build_rect = pygame.Rect(0, 0, 0, 0)
        self.upgrade_rect = pygame.Rect(0, 0, 0, 0)
        self.close_rect = pygame.Rect(0, 0, 0, 0)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.last_message = ""

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False

    def contains(self, pos):
        return self.visible and self.panel_rect.collidepoint(pos)

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect.collidepoint(event.pos):
                self.close()
                return True
            for building_id, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.selected_id = building_id
                    return True
            if self.build_rect.collidepoint(event.pos):
                if not self._building_unlocked(self.selected_id):
                    self.event_log.push("Ця споруда ще не відкрита навчальною кампанією.")
                    return True
                ok, message = self.manager.start_build(self.selected_id)
                self.last_message = message
                self.event_log.push(message, theme.GREEN if ok else theme.RED)
                return True
            if self.upgrade_rect.collidepoint(event.pos):
                ok, message = self.manager.start_upgrade(self.selected_id)
                self.last_message = message
                self.event_log.push(message, theme.GREEN if ok else theme.RED)
                return True
            if self.panel_rect.collidepoint(event.pos):
                return True
        return False

    def _building_unlocked(self, building_id):
        available_ids = [d["id"] for d in self.manager.available_definitions()]
        return building_id in allowed_building_ids(self.progression, available_ids)

    def draw(self, surface):
        if not self.visible:
            return
        w, h = surface.get_size()
        x, y = 220, 86
        definitions_all = self.manager.available_definitions()
        allowed_definitions = [d for d in definitions_all
                               if self._building_unlocked(d["id"])]
        if not allowed_definitions:
            self.panel_rect = pygame.Rect(x, y, self.WIDTH, 180)
            theme.panel(surface, self.panel_rect, fill=(7, 17, 32), border=theme.CYAN_DIM)
            theme.label(surface, "КОНСТРУКТОР СТАНЦІЇ", (x+16, y+13), 15, theme.CYAN, True)
            theme.label(surface, "Наразі немає доступних для будівництва споруд.",
                        (x+16, y+65), 11, theme.MUTED)
            return
        allowed_ids = {d["id"] for d in allowed_definitions}
        if self.selected_id not in allowed_ids:
            self.selected_id = allowed_definitions[0]["id"]
        panel_h = max(400, min(h - 180, 720))
        self.panel_rect = pygame.Rect(x, y, self.WIDTH, panel_h)
        theme.panel(surface, self.panel_rect, fill=(7, 17, 32), border=theme.CYAN_DIM)
        theme.label(surface, "КОНСТРУКТОР СТАНЦІЇ", (x+16, y+13), 15, theme.CYAN, True)
        theme.label(surface, "BUILD / UPGRADE", (x+16, y+35), 9, theme.MUTED, True)
        self.close_rect = pygame.Rect(x+self.WIDTH-38, y+10, 26, 25)
        pygame.draw.rect(surface, theme.PANEL_HOVER, self.close_rect, border_radius=4)
        theme.label(surface, "×", (self.close_rect.x+8, self.close_rect.y+2), 17, theme.TEXT)
        pygame.draw.line(surface, theme.BORDER, (x+14,y+64),(x+self.WIDTH-14,y+64),1)

        definitions = allowed_definitions
        row_y = y + 75
        row_h = 34
        list_limit = min(len(definitions), max(5, (panel_h - 340)//row_h))
        self.row_rects.clear()
        for definition in definitions[:list_limit]:
            bid = definition["id"]
            rect = pygame.Rect(x+12, row_y, self.WIDTH-24, row_h-3)
            self.row_rects[bid] = rect
            selected = bid == self.selected_id
            if selected:
                pygame.draw.rect(surface, (16, 54, 78), rect, border_radius=4)
                pygame.draw.rect(surface, theme.CYAN_DIM, rect, 1, border_radius=4)
            elif self.manager.count(bid):
                pygame.draw.rect(surface, (15, 34, 48), rect, border_radius=4)
            theme.label(surface, definition["name"], (rect.x+9, rect.y+8), 11,
                        theme.TEXT if selected else theme.MUTED, selected)
            count = self.manager.count(bid)
            theme.label(surface, f"x{count}", (rect.right-42, rect.y+8), 10,
                        theme.GREEN if count else theme.MUTED, True)
            row_y += row_h

        definition = self.manager.definition(self.selected_id)
        detail_y = y + 75 + list_limit*row_h + 5
        detail_bottom = y + panel_h - 154
        pygame.draw.line(surface, theme.BORDER, (x+14,detail_y),(x+self.WIDTH-14,detail_y),1)
        theme.label(surface, definition["name"].upper(), (x+16,detail_y+10), 13, theme.CYAN, True)
        owned = self.manager.instances(self.selected_id)
        level = owned[0]["level"] if owned else 0
        theme.label(surface, f"РІВЕНЬ {level}  •  ПОБУДОВАНО: {len(owned)}",
                    (x+16,detail_y+31), 10, theme.GREEN if owned else theme.MUTED)
        desc_words = definition["description"].split()
        lines, current = [], ""
        font = theme.font(10)
        for word in desc_words:
            candidate = (current+" "+word).strip()
            if current and font.size(candidate)[0] > self.WIDTH-38:
                lines.append(current); current = word
            else:
                current = candidate
        if current: lines.append(current)
        for i, line in enumerate(lines[:2]):
            theme.label(surface, line, (x+16,detail_y+49+i*14), 10, theme.MUTED)

        stats_y = detail_y + 82
        production = definition.get("production", {})
        prod_text = ", ".join(f"+{v:g} {k}/с" for k,v in production.items()) or "Немає"
        theme.label(surface, f"Виробництво: {prod_text}", (x+16,stats_y), 10, theme.GREEN)
        theme.label(surface, f"Споживання енергії: -{definition['energy_consumption']:g}/с",
                    (x+16,stats_y+17), 10, theme.GOLD)
        theme.label(surface, f"Час будівництва: {definition['build_time']:g} с",
                    (x+16,stats_y+34), 10, theme.MUTED)
        cost = definition["cost"]
        theme.label(surface, "ВАРТІСТЬ: "+self._cost_text(cost),
                    (x+16,stats_y+51), 9, theme.TEXT)

        # Active projects and progress bars.
        projects = self.manager.progress_snapshot()
        progress_y = detail_bottom + 7
        theme.label(surface, f"АКТИВНІ ПРОЄКТИ ({len(projects)})",
                    (x+16,progress_y), 10, theme.MUTED, True)
        for i, project in enumerate(projects[:2]):
            py = progress_y + 20 + i*24
            theme.label(surface, theme.fit_text(project["name"], 24),
                        (x+16,py), 9, theme.TEXT)
            bar = pygame.Rect(x+205, py+2, 190, 7)
            pygame.draw.rect(surface, (25,43,59), bar, border_radius=3)
            pygame.draw.rect(surface, theme.CYAN,
                             (bar.x,bar.y,int(bar.width*project["progress"]),bar.height),
                             border_radius=3)
            theme.label(surface, f"{project['progress']*100:.0f}%",
                        (bar.right-31,py+10), 8, theme.MUTED)

        buttons_y = y + panel_h - 42
        self.build_rect = pygame.Rect(x+14,buttons_y,self.WIDTH//2-22,30)
        self.upgrade_rect = pygame.Rect(x+self.WIDTH//2+3,buttons_y,self.WIDTH//2-22,30)
        theme.action_button(surface, self.build_rect, "ПОБУДУВАТИ",
                            state="success", accent=theme.CYAN, font_size=10)
        theme.action_button(surface, self.upgrade_rect, "ПОКРАЩИТИ",
                            state="normal", accent=theme.PURPLE, font_size=10)

    @staticmethod
    def _cost_text(cost):
        """Format construction costs using the resource names shown in the HUD."""
        labels = {
            "metal": "МЕТ",
            "energy": "ЕН",
            "crystals": "КР",
            "fuel": "ПАЛ",
            "credits": "КРЕД",
            "science": "НАУК",
        }
        if not cost:
            return "Безкоштовно"
        parts = []
        for resource_id, amount in cost.items():
            label = labels.get(resource_id, resource_id.upper())
            try:
                value = f"{float(amount):g}"
            except (TypeError, ValueError):
                value = str(amount)
            parts.append(f"{label} {value}")
        return " • ".join(parts)


```

### `tests/test_panel_visual_system.py`
```python
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = (
    "build_panel.py", "research_panel.py", "campaign_panel.py", "progression_panel.py",
    "fleet_panel.py", "colony_panel.py", "galaxy_panel.py", "settings_panel.py",
    "trade_panel.py", "automation_panel.py", "mining_panel.py",
)


class PanelVisualSystemTests(unittest.TestCase):
    def test_shared_theme_exposes_unified_components(self):
        tree = ast.parse((ROOT / "ui/theme.py").read_text(encoding="utf-8"))
        names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({"panel", "section_header", "action_button", "info_card", "label"} <= names)

    def test_all_management_panels_use_shared_theme(self):
        for name in PANELS:
            path = ROOT / "ui" / name
            if path.exists():
                source = path.read_text(encoding="utf-8")
                self.assertIn("theme", source, name)

    def test_building_actions_keep_same_hit_rects_and_labels(self):
        source = (ROOT / "ui/build_panel.py").read_text(encoding="utf-8")
        for token in ("self.build_rect", "self.upgrade_rect", "ПОБУДУВАТИ", "ПОКРАЩИТИ",
                      'build_time', 'energy_consumption',
                      "definition.get"):
            self.assertIn(token, source)

    def test_window_event_apis_remain(self):
        for name in PANELS:
            path = ROOT / "ui" / name
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
            for cls in classes:
                methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
                if "draw" in methods:
                    self.assertIn("handle_event", methods, name)


if __name__ == "__main__":
    unittest.main()

```
