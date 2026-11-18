# Space Empire — виправлення AttributeError у конструкторі

## Точна першопричина

`ui/build_panel.py` викликав `self._cost_text(cost)` під час промальовування картки споруди, але в класі `BuildPanel` методу `_cost_text` не існувало. Через це кожна спроба намалювати деталі вибраної споруди завершувалася `AttributeError`, а `PanelGuard` показував червону діагностичну панель.

Це відповідає обрізаному повідомленню в журналі: `AttributeError: 'Buil...`.

## Виправлення

- Додано `BuildPanel._cost_text()` для відображення вартості ресурсів.
- Форматтер показує метал, енергію, кристали, паливо, кредити та науку; невідомі ресурси не губляться.
- Порожня вартість показується як «Безкоштовно».
- Логіка будівництва, ціни в каталозі, прогресія, дизайн панелі та `BuildingManager` не переписувалися.
- Додано три регресійні тести, включно з відображенням повної ціни сонячної панелі.

## Перевірки

- `compileall`: PASS.
- Автоматичні тести: 139/139 PASS.
- Python AST: 82/82 PASS.
- JSON: 13/13 PASS.
- ZIP integrity: PASS.
- Pygame у середовищі відсутній: реальне відкриття вікна та кліки в GUI не перевірені.

## Повний код змінених файлів

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
        pygame.draw.rect(surface, (18,75,91), self.build_rect, border_radius=5)
        pygame.draw.rect(surface, theme.CYAN_DIM, self.build_rect, 1, border_radius=5)
        pygame.draw.rect(surface, (57,58,83), self.upgrade_rect, border_radius=5)
        pygame.draw.rect(surface, theme.PURPLE, self.upgrade_rect, 1, border_radius=5)
        theme.label(surface, "ПОБУДУВАТИ", (self.build_rect.x+20,self.build_rect.y+9), 10, theme.TEXT, True)
        theme.label(surface, "ПОКРАЩИТИ", (self.upgrade_rect.x+18,self.upgrade_rect.y+9), 10, theme.TEXT, True)

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

### `tests/test_build_panel_costs.py`
```python
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildPanelCostFormatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "ui" / "build_panel.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        panel = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "BuildPanel")
        method = next(node for node in panel.body
                      if isinstance(node, ast.FunctionDef) and node.name == "_cost_text")
        module = ast.Module(body=[method], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {}
        exec(compile(module, "build_panel_cost_formatter", "exec"), namespace)
        cls.format_cost = staticmethod(namespace["_cost_text"])

    def test_solar_array_cost_is_renderable(self):
        rendered = self.format_cost({
            "metal": 90, "energy": 20, "crystals": 8,
            "fuel": 5, "credits": 35
        })
        self.assertEqual(rendered, "МЕТ 90 • ЕН 20 • КР 8 • ПАЛ 5 • КРЕД 35")

    def test_empty_cost_is_explicit(self):
        self.assertEqual(self.format_cost({}), "Безкоштовно")

    def test_unknown_resource_is_not_dropped(self):
        self.assertEqual(self.format_cost({"rare_alloy": 2}), "RARE_ALLOY 2")


if __name__ == "__main__":
    unittest.main()

```
