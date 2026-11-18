# Space Empire — повний технічний аудит

## Підсумок

- Перевірено Python-файлів: **77**; JSON-файлів: **13**.
- AST/SyntaxError: **0**; помилки JSON: **0**; невирішені локальні імпорти: **0**.
- `compileall`: PASS.
- Автоматичні тести: **122/122 PASS**.
- Графічний запуск: **НЕ ВИКОНАНО** — `pygame`/`pygame-ce` відсутній; встановлення з PyPI неможливе через відсутність мережі.

## 1. Знайдені проблеми та першопричина

1. У HUD не було ізоляції винятків під час обробки подій і промальовування панелей. Будь-який виняток у панелі міг вийти до головного циклу `Game.run()` і завершити процес.
2. Будівельна панель припускала, що каталог завжди має хоча б одну доступну споруду та що `selected_id` завжди відповідає доступному визначенню. Для порожнього/неузгодженого набору це створювало шлях до `KeyError`.
3. Панель кампанії припускала, що в менеджері завжди є хоча б один розділ кампанії. `current_chapter()` індексував останній елемент списку без перевірки порожнього списку.
4. **Точну першопричину конкретного аварійного закриття «Будівництва»/«Кампанії» підтвердити не вдалося:** у повідомленні користувача немає traceback, а графічний runtime недоступний у середовищі. Не буду вигадувати тип винятку чи стверджувати, що відтворив збій.

## 2. Що виправлено

- `ui/hud.py`: додано ізольовану обробку подій і малювання для кожної панелі та базових елементів HUD. Помилка вимикає лише проблемну панель, записується в `saves/ui_errors.log` разом із traceback і повідомляється в журналі подій; головний процес продовжує роботу.
- `ui/build_panel.py`: перевірка доступних споруд і коректний стан-повідомлення, якщо каталог порожній; невалідний вибір замінюється першою доступною спорудою.
- `campaign/campaign_manager.py`: `current_chapter()` безпечно повертає `None`, якщо список глав порожній.
- `ui/campaign_panel.py`: відображає контрольоване повідомлення при відсутніх даних глави замість звернення до `None`.
- `tests/test_release_package.py`: додано перевірки захисту HUD, будівельної панелі, кампанії та відповідності розділів меню правилам прогресії.

## 3. Системи, що перевірені

- Нова гра/прогресія: окремі модульні тести стартового стану, нульових ресурсів, аварійного збору, одноразових нагород, відкриття механік.
- Економіка: отримання/витрачання, виробництво, місткість, delta time та обмеження ресурсів.
- Будівництво: каталог, ціна, старт/завершення, апгрейди, ефекти, перевірка ресурсів.
- Видобуток і флот: цикли кораблів, доставка, паливо, завдання, апгрейди.
- Технології: залежності, дослідження, бонуси та збереження.
- Галактика/колонії: відкриття систем, експедиції, колонізація, трансфери.
- Торгівля/автоматизація: ринок, маршрути, резервування, правила й рецепти.
- Кампанія/прогресія: місії, події, умови, винагороди, блокування, snapshot/restore.
- Save/load: контрольна сума, backup, відновлення, офлайн-прогрес, захист від повторних нагород.
- Навігація: усі 13 пунктів sidebar зіставлено з `SECTION_REQUIREMENTS`.

## 4. Результати тестів

- 122/122 unittest — PASS.
- `compileall` — PASS.
- AST parsing: 77/77 Python-файлів — PASS.
- JSON parsing: 13/13 — PASS.
- Локальні модульні імпорти: невирішених локальних залежностей не знайдено статичним аналізом.
- Перевірка ZIP integrity — буде виконана після пакування.

## 5. Обмеження перевірки

Не перевірено фактичні кліки, рендеринг Pygame, швидке перемикання кнопок у живому вікні, аудіо, FPS та Windows executable. `pygame` не встановлений; pip install не спрацював через недоступність мережі. Тести підтверджують логіку менеджерів і статичні гарантії UI, але не замінюють GUI smoke test.

## 6. Статус

- Нова гра: логіка старту покрита тестами; повний GUI запуск не підтверджений.
- Будівництво/Кампанія: додано захист від помилок окремих панелей і відсутніх даних; фактичне відкриття в Pygame не підтверджене.
- Якщо помилка панелі повториться, traceback буде записано в `saves/ui_errors.log`. Саме цей лог дозволить встановити конкретну першопричину на машині, де Pygame доступний.
- Продовжувати розробку можна обережно на рівні логіки та модулів; перед релізом обов'язковий GUI smoke test на Windows/Pygame.

## 7. Повний код змінених файлів

### `ui/hud.py`

```python
"""HUD composition, input routing and adaptive layout."""
import pygame
import traceback
from pathlib import Path
from ui.top_bar import TopBar
from ui.sidebar import Sidebar
from ui.right_panel import RightPanel
from ui.bottom_bar import BottomBar
from ui.tooltip import Tooltip
from ui.build_panel import BuildPanel
from ui.mining_panel import MiningPanel
from ui.fleet_panel import FleetPanel
from ui.research_panel import ResearchPanel
from ui.offline_report import OfflineReport
from ui.galaxy_panel import GalaxyPanel
from ui.colony_panel import ColonyPanel
from ui.automation_panel import AutomationPanel
from ui.trade_panel import TradePanel
from ui.campaign_panel import CampaignPanel
from ui.settings_panel import SettingsPanel
from ui.progression_panel import ProgressionPanel


class HUD:
    def __init__(self, resource_manager, building_manager, station, mining_manager, fleet_manager=None, technology_manager=None, offline_report=None, galaxy_manager=None, colony_manager=None, automation_manager=None, trade_manager=None, campaign_manager=None, game=None, progression=None):
        self.top = TopBar(resource_manager, progression)
        self.sidebar = Sidebar(progression, None)
        self.right = RightPanel()
        self.bottom = BottomBar()
        self.tooltip = Tooltip()
        self.current_section = "Огляд"
        self.build_panel = BuildPanel(building_manager, resource_manager, self.bottom, progression)
        self.station = station
        self.mining_panel = MiningPanel(mining_manager, self.bottom)
        self.fleet_panel = FleetPanel(fleet_manager, self.bottom) if fleet_manager else None
        self.research_panel = ResearchPanel(technology_manager, self.bottom) if technology_manager else None
        self.offline_report = OfflineReport(offline_report) if offline_report else None
        self.galaxy_panel = GalaxyPanel(galaxy_manager, fleet_manager, self.bottom) if galaxy_manager and fleet_manager else None
        self.colony_panel = ColonyPanel(colony_manager, fleet_manager, self.bottom) if colony_manager and fleet_manager else None
        self.automation_panel = AutomationPanel(automation_manager, self.bottom) if automation_manager else None
        self.trade_panel = TradePanel(trade_manager, colony_manager, fleet_manager, self.bottom) if trade_manager and colony_manager and fleet_manager else None
        self.campaign_panel = CampaignPanel(campaign_manager, self.bottom) if campaign_manager else None
        self.settings_panel = SettingsPanel(game, self.bottom) if game else None
        self.progression_panel = ProgressionPanel(progression, self.bottom) if progression else None
        self.sidebar.event_log = self.bottom
        if self.progression_panel and progression.intro_seen:
            self.progression_panel.visible = False

    def _report_ui_error(self, component, exc):
        message = f"Помилка інтерфейсу ({component}): {type(exc).__name__}: {exc}"
        try:
            self.bottom.push(message)
        except Exception:
            pass
        try:
            log_path = Path(__file__).resolve().parent.parent / "saves" / "ui_errors.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write("\\n" + message + "\\n")
                stream.write(traceback.format_exc())
                stream.write("\\n")
        except OSError:
            pass

    def _safe_panel_event(self, panel, event, component):
        if panel is None or not getattr(panel, "visible", False):
            return False
        try:
            return bool(panel.handle_event(event))
        except Exception as exc:
            panel.visible = False
            self._report_ui_error(component, exc)
            return True

    def _safe_panel_draw(self, panel, surface, component):
        if panel is None:
            return
        try:
            panel.draw(surface)
        except Exception as exc:
            panel.visible = False
            self._report_ui_error(component, exc)

    def handle_event(self, event):
        event_panels = (
            (self.progression_panel, "Прогрес"),
            (self.settings_panel, "Налаштування"),
            (self.campaign_panel, "Кампанія"),
            (self.automation_panel, "Автоматизація"),
            (self.trade_panel, "Торгівля"),
            (self.colony_panel, "Планети"),
            (self.galaxy_panel, "Галактична карта"),
            (self.offline_report, "Офлайн-звіт"),
            (self.build_panel, "Будівництво"),
            (self.mining_panel, "Видобуток"),
            (self.fleet_panel, "Флот"),
            (self.research_panel, "Дослідження"),
        )
        for panel, name in event_panels:
            if self._safe_panel_event(panel, event, name):
                return "__ui__"

        try:
            self.top.handle_event(event, self.tooltip)
            selected = self.sidebar.handle_event(event, self.tooltip)
        except Exception as exc:
            self._report_ui_error("Навігація", exc)
            return "__ui__"
        if selected:
            if self.progression_panel:
                state, reason = self.progression_panel.progression.section_state(selected)
                if state == "LOCKED":
                    self.bottom.push(f"РОЗДІЛ ЗАБЛОКОВАНО: {selected}. Умова відкриття: {reason}")
                    self.sidebar.active = self.current_section
                    return "__ui__"
            self.current_section = selected
            self.right.set_section(selected)
            panel_routes = (
                (self.galaxy_panel, "Галактична карта"),
                (self.colony_panel, "Планети"),
                (self.automation_panel, "Автоматизація"),
                (self.trade_panel, "Торгівля"),
                (self.campaign_panel, "Кампанія"),
                (self.settings_panel, "Налаштування"),
            )
            for panel, section in panel_routes:
                if panel:
                    if selected == section:
                        panel.open()
                    else:
                        panel.close()
            if self.progression_panel:
                if selected == "Прогрес":
                    self.progression_panel.open()
                elif not self.progression_panel.visible:
                    self.progression_panel.close()
            if selected == "Будівництво":
                self.build_panel.open()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.close()
            elif selected == "Видобуток":
                self.mining_panel.open()
                self.build_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.close()
            elif selected == "Флот":
                self.build_panel.close()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.open()
                if self.research_panel: self.research_panel.close()
            elif selected == "Дослідження":
                self.build_panel.close()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.open()
            else:
                self.build_panel.close()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.close()
            self.bottom.push(f"Відкрито розділ: {selected}")
            return selected
        if event.type == pygame.MOUSEMOTION and self.sidebar.hovered is None:
            if not any(r.collidepoint(event.pos) for r in self.top.resource_rects.values()):
                self.tooltip.text = None
        return None

    def update(self, dt):
        self.right.update(dt)
        self.sidebar.update(dt)

    def draw(self, surface, station_selected):
        for component, callback in (
            ("Верхня панель", lambda: self.top.draw(surface)),
            ("Бічне меню", lambda: self.sidebar.draw(surface)),
            ("Права панель", lambda: self.right.draw(surface, station_selected)),
            ("Журнал подій", lambda: self.bottom.draw(surface)),
        ):
            try:
                callback()
            except Exception as exc:
                self._report_ui_error(component, exc)
        self._safe_panel_draw(self.build_panel, surface, "Будівництво")
        self._safe_panel_draw(self.mining_panel, surface, "Видобуток")
        self._safe_panel_draw(self.fleet_panel, surface, "Флот")
        self._safe_panel_draw(self.research_panel, surface, "Дослідження")
        try:
            self.tooltip.draw(surface)
        except Exception as exc:
            self._report_ui_error("Підказки", exc)
        self._safe_panel_draw(self.galaxy_panel, surface, "Галактична карта")
        self._safe_panel_draw(self.colony_panel, surface, "Планети")
        self._safe_panel_draw(self.automation_panel, surface, "Автоматизація")
        self._safe_panel_draw(self.trade_panel, surface, "Торгівля")
        self._safe_panel_draw(self.campaign_panel, surface, "Кампанія")
        self._safe_panel_draw(self.settings_panel, surface, "Налаштування")
        self._safe_panel_draw(self.offline_report, surface, "Офлайн-звіт")
        self._safe_panel_draw(self.progression_panel, surface, "Прогрес")

```

### `ui/build_panel.py`

```python
"""Interactive construction catalogue, detail view and project progress."""
import pygame
from ui import theme


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
        if self.progression is None:
            return True
        configured = self.progression.balance.get("available_buildings_by_stage", {})
        stage_id = self.progression.stage_id
        allowed = configured.get(stage_id, ["core"])
        return building_id in allowed

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

```

### `campaign/campaign_manager.py`

```python
"""JSON-driven campaign missions and random story events."""
import copy, json, random
from pathlib import Path

class CampaignManager:
    def __init__(self,economy,buildings,mining,fleet,technology,galaxy,colonies,data_path=None,rng=None,enabled=True):
        self.economy,self.buildings,self.mining=economy,buildings,mining
        self.fleet,self.technology,self.galaxy,self.colonies=fleet,technology,galaxy,colonies
        path=Path(data_path) if data_path else Path(__file__).with_name("campaign.json")
        self.data=json.loads(path.read_text(encoding="utf-8"))
        self.chapters=self.data["chapters"]
        self.missions={m["id"]:copy.deepcopy(m) for m in self.data["missions"]}
        self.event_definitions=self.data["events"]
        self.rng=rng or random.Random()
        self.flags=set(); self.active_event=None; self.timer=float(self.data["event_settings"]["first_event_delay"])
        self.events=[]
        self.enabled=bool(enabled)
        if self.enabled:
            self._recalculate()

    def _progress(self,o):
        t=o["type"]
        if t=="resource": return self.economy.get(o["key"]).amount
        if t=="building": return sum(len(v) for k,v in self.buildings.owned.items() if k==o["key"])
        if t=="mined": return getattr(self.mining,"delivered_total",0)
        if t=="ship": return sum(s.ship_type==o["key"] for s in self.fleet.ships)
        if t=="fleet": return len(self.fleet.ships)
        if t=="systems": return sum(bool(s.get("discovered")) for s in self.galaxy.systems.values())
        if t=="colonies": return len(getattr(self.colonies,"colonies",[]))
        if t=="colony_level":
            rows=getattr(self.colonies,"colonies",{})
            values=rows.values() if isinstance(rows,dict) else rows
            return max([int(c.get("development",c.get("level",1))) for c in values] or [0])
        if t=="flag": return int(o["key"] in self.flags)
        if t=="tech_count": return sum(v.get("state")=="completed" for v in self.technology.technologies.values())
        if t=="tech_keyword":
            return int(any(v.get("state")=="completed" and any(k in (key+" "+str(v.get("name",""))).lower() for k in o["keys"]) for key,v in self.technology.technologies.items()))
        return 0

    def _recalculate(self):
        if not self.enabled:
            return
        for chapter in self.chapters:
            previous=all(all(self.missions[mid]["status"]=="completed" for mid in c["missions"]) for c in self.chapters[:self.chapters.index(chapter)])
            for mid in chapter["missions"]:
                m=self.missions[mid]
                if m.get("status")=="completed": continue
                earlier=chapter["missions"][:chapter["missions"].index(mid)]
                m["status"]="available" if previous and all(self.missions[x]["status"]=="completed" for x in earlier) else "locked"
                m["progress"]=self._progress(m["objective"])
                if m["status"]=="available" and m["progress"]>=m["objective"].get("amount",1):
                    m["status"]="completed"
                    for key,value in m.get("rewards",{}).items(): self.economy.add(key,value)
                    self.events.append("Місію завершено: "+m["title"]+". Нагороди нараховано.")
        # Refresh next mission statuses after completion cascade.
        for chapter in self.chapters:
            previous=all(all(self.missions[mid]["status"]=="completed" for mid in c["missions"]) for c in self.chapters[:self.chapters.index(chapter)])
            for i,mid in enumerate(chapter["missions"]):
                m=self.missions[mid]
                if m["status"]!="completed":
                    m["status"]="available" if previous and all(self.missions[x]["status"]=="completed" for x in chapter["missions"][:i]) else "locked"

    def current_chapter(self):
        if not self.chapters:
            return None
        return next((c for c in self.chapters
                     if not all(self.missions[x]["status"] == "completed"
                                for x in c.get("missions", [])
                                if x in self.missions)), self.chapters[-1])

    def update(self,dt):
        if not self.enabled:
            return
        self._recalculate()
        if self.active_event: return
        self.timer-=max(0,float(dt))
        if self.timer<=0:
            self.trigger_event()
            cfg=self.data["event_settings"]
            self.timer=self.rng.uniform(cfg["minimum_interval"],cfg["maximum_interval"])

    def trigger_event(self,event_id=None):
        if self.active_event: return False
        event=next((x for x in self.event_definitions if x["id"]==event_id),None) if event_id else self.rng.choice(self.event_definitions)
        if not event: return False
        self.active_event=copy.deepcopy(event)
        self.events.append("Космічна подія: "+event["title"])
        return True

    def choose_event(self,choice_id):
        if not self.active_event: return False,"Немає активної події."
        choice=next((x for x in self.active_event["choices"] if x["id"]==choice_id),None)
        if not choice: return False,"Невідомий варіант."
        costs=choice.get("costs",{})
        if not self.economy.can_afford(costs): return False,"Недостатньо ресурсів."
        if costs and not self.economy.spend(costs): return False,"Не вдалося списати ресурси."
        for key,value in choice.get("effects",{}).items():
            self.economy.add(key,value) if value>=0 else setattr(self.economy.get(key),"amount",max(0,self.economy.get(key).amount+value))
        self.flags.update(choice.get("flags",[]))
        self.events.append("Рішення: "+self.active_event["title"]+" — "+choice["label"])
        self.active_event=None; self._recalculate()
        return True,"Рішення виконано."

    def snapshot(self):
        return {"missions":copy.deepcopy(self.missions),"flags":sorted(self.flags),"active_event":copy.deepcopy(self.active_event),"timer":self.timer,"rng_state":self.rng.getstate(),"enabled":self.enabled}

    def restore(self,state):
        self.enabled=bool(state.get("enabled", True))
        for key,value in state.get("missions",{}).items():
            if key in self.missions: self.missions[key].update({k:copy.deepcopy(value[k]) for k in ("status","progress") if k in value})
        self.flags=set(state.get("flags",[])); self.active_event=copy.deepcopy(state.get("active_event"))
        self.timer=max(0,float(state.get("timer",self.timer)))
        try:
            if state.get("rng_state"): self.rng.setstate(state["rng_state"])
        except (TypeError,ValueError): pass
        self._recalculate()

    def take_events(self):
        result,self.events=self.events[:],[]
        return result

```

### `ui/campaign_panel.py`

```python
"""Campaign journal and modal narrative choices."""
import pygame
from ui import theme
class CampaignPanel:
    def __init__(self,manager,bottom):
        self.manager,self.bottom=manager,bottom
        self.visible=False; self.scroll=0; self.choice_rects=[]; self.close_rect=pygame.Rect(0,0,1,1)
    def open(self): self.visible=True
    def close(self): self.visible=False
    def handle_event(self,event):
        if not self.visible: return False
        if event.type==pygame.MOUSEWHEEL: self.scroll=max(0,self.scroll-event.y*32); return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if self.manager.active_event:
                for rect,cid in self.choice_rects:
                    if rect.collidepoint(event.pos):
                        ok,msg=self.manager.choose_event(cid); self.bottom.push(msg); return True
            if self.close_rect.collidepoint(event.pos): self.close()
            return True
        return False
    def _wrap(self,surface,text,rect,color,size=14,limit=4):
        font=pygame.font.SysFont("segoeui",size); words=str(text).split(); lines=[]; line=""
        for word in words:
            candidate=(line+" "+word).strip()
            if font.size(candidate)[0]>rect.width and line: lines.append(line); line=word
            else: line=candidate
        if line: lines.append(line)
        for i,line in enumerate(lines[:limit]): surface.blit(font.render(line,True,color),(rect.x,rect.y+i*(size+4)))
    def draw(self,surface):
        if not self.visible: return
        w,h=surface.get_size(); shade=pygame.Surface((w,h),pygame.SRCALPHA); shade.fill((1,5,15,215)); surface.blit(shade,(0,0))
        panel=pygame.Rect(220,86,w-500,h-176); theme.panel(surface,panel,fill=(7,17,32)); pygame.draw.rect(surface,theme.BORDER_BRIGHT,panel,1,border_radius=9)
        title="КОСМІЧНА ПОДІЯ" if self.manager.active_event else "СЮЖЕТНА КАМПАНІЯ"
        theme.label(surface,title,(panel.x+24,panel.y+17),19,theme.CYAN,True)
        self.close_rect=pygame.Rect(panel.right-42,panel.y+12,30,30); theme.label(surface,"×",(self.close_rect.x+8,self.close_rect.y),24,theme.TEXT,True)
        if self.manager.active_event:
            e=self.manager.active_event; art=pygame.Rect(panel.x+24,panel.y+60,245,190)
            pygame.draw.rect(surface,(10,35,57),art,border_radius=8); pygame.draw.rect(surface,theme.CYAN,art,1,border_radius=8)
            cx,cy=art.center
            for r in (34,57,80): pygame.draw.circle(surface,(31,105,140),(cx,cy),r,1)
            if e["illustration"] in ("ship","asteroid","artifact"):
                pygame.draw.polygon(surface,(110,137,154),[(cx-55,cy),(cx-18,cy-40),(cx+43,cy-25),(cx+55,cy+15),(cx,cy+43)])
                pygame.draw.circle(surface,theme.CYAN,(cx+12,cy-4),7)
            else:
                for r in range(20,75,12): pygame.draw.arc(surface,theme.CYAN,(cx-r,cy-r,2*r,2*r),.2,2.8,2)
            theme.label(surface,e["category"].upper(),(art.x+12,art.bottom-23),10,theme.CYAN,True)
            theme.label(surface,e["title"],(art.right+22,art.y+5),21,theme.TEXT,True)
            self._wrap(surface,e["description"],pygame.Rect(art.right+22,art.y+42,panel.right-art.right-55,110),theme.MUTED,15,5)
            self.choice_rects=[]; y=art.bottom+22
            for c in e["choices"]:
                r=pygame.Rect(panel.x+24,y,panel.width-48,62); pygame.draw.rect(surface,(13,39,59),r,border_radius=6); pygame.draw.rect(surface,theme.BORDER,r,1,border_radius=6)
                theme.label(surface,c["label"],(r.x+13,r.y+7),14,theme.CYAN,True)
                self._wrap(surface,c["description"],pygame.Rect(r.x+13,r.y+30,r.width-26,26),theme.MUTED,11,1)
                self.choice_rects.append((r,c["id"])); y+=71
            return
        ch = self.manager.current_chapter()
        if not ch:
            theme.label(surface, "Дані кампанії поки недоступні.",
                        (panel.x + 24, panel.y + 70), 14, theme.MUTED)
            return
        theme.label(surface,ch["title"],(panel.x+24,panel.y+56),22,theme.TEXT,True)
        self._wrap(surface,ch.get("story", ""),pygame.Rect(panel.x+24,panel.y+91,panel.width-48,60),theme.MUTED,14,4)
        area=pygame.Rect(panel.x+18,panel.y+160,panel.width-36,panel.height-176); clip=surface.get_clip(); surface.set_clip(area)
        y=area.y-self.scroll
        for chapter in self.manager.chapters:
            complete=all(self.manager.missions[x]["status"]=="completed" for x in chapter["missions"])
            theme.label(surface,("✓ " if complete else "◇ ")+chapter["title"],(area.x+8,y),14,theme.GREEN if complete else theme.CYAN,True); y+=25
            for mid in chapter["missions"]:
                m=self.manager.missions[mid]; color=theme.GREEN if m["status"]=="completed" else theme.TEXT if m["status"]=="available" else theme.MUTED
                theme.label(surface,m["title"],(area.x+25,y),12,color,m["status"]=="available")
                target=max(1,m["objective"].get("amount",1)); progress=min(1,float(m.get("progress",0))/target)
                bar=pygame.Rect(area.x+260,y+3,180,7); pygame.draw.rect(surface,(25,43,60),bar,border_radius=3); pygame.draw.rect(surface,theme.CYAN,(bar.x,bar.y,int(bar.width*progress),7),border_radius=3)
                status={"completed":"ВИКОНАНО","available":"АКТИВНА","locked":"ЗАБЛОКОВАНА"}[m["status"]]
                theme.label(surface,status,(bar.right+12,y),10,color,True)
                y+=17
                objective=m["objective"]
                condition=f"Умова: {objective.get('key',objective.get('type','ціль'))} — {objective.get('amount',1)}"
                self._wrap(surface,m.get("description",condition),pygame.Rect(area.x+25,y,area.width-55,28),theme.MUTED,10,1)
                reward_text="Нагорода: "+", ".join(f"{k} +{v}" for k,v in m.get("rewards",{}).items())
                theme.label(surface,reward_text,(area.x+25,y+13),9,theme.CYAN if m["status"]!="locked" else theme.MUTED)
                y+=31
            y+=10
        surface.set_clip(clip)

```

### `tests/test_release_package.py`

```python
import ast
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ReleasePackageTests(unittest.TestCase):
    def test_all_json_data_files_parse(self):
        files=list(ROOT.rglob("*.json"))
        self.assertGreaterEqual(len(files),7)
        for path in files:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_game_supports_new_and_continue_modes(self):
        tree=ast.parse((ROOT/"game.py").read_text(encoding="utf-8"))
        game=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Game")
        init=next(n for n in game.body if isinstance(n,ast.FunctionDef) and n.name=="__init__")
        self.assertIn("load_saved",[a.arg for a in init.args.args])

    def test_settings_are_connected_to_hud(self):
        hud=(ROOT/"ui"/"hud.py").read_text(encoding="utf-8")
        self.assertIn("SettingsPanel(game, self.bottom)",hud)
        self.assertIn('(self.settings_panel, "Налаштування")',hud)

    def test_release_assets_and_build_files_exist(self):
        required=[
            "requirements.txt","README.md","launcher.py","SpaceEmpire.spec",
            "build_windows.bat","assets/icons/space_empire.ico",
            "assets/icons/space_empire.png","assets/audio/ambient_loop.wav",
            "assets/audio/ui_click.wav","ui/settings_panel.py"
        ]
        for rel in required:
            with self.subTest(file=rel): self.assertTrue((ROOT/rel).is_file())

    def test_launcher_does_not_shadow_global_config(self):
        tree=ast.parse((ROOT/"launcher.py").read_text(encoding="utf-8"))
        launcher=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_launcher")
        local_config_imports=[
            n for n in ast.walk(launcher)
            if isinstance(n,ast.Import) and any(alias.name=="config" for alias in n.names)
        ]
        self.assertEqual(local_config_imports, [])

    def test_launcher_has_all_required_screens(self):
        text=(ROOT/"launcher.py").read_text(encoding="utf-8")
        for state in ('"splash"','"menu"','"settings"','"loading"'):
            self.assertIn(state,text)


    def test_continue_button_is_conditional_on_valid_save(self):
        launcher = (ROOT / "launcher.py").read_text(encoding="utf-8")
        self.assertIn("def has_continue_save()", launcher)
        self.assertIn("if continue_available:", launcher)
        self.assertIn('labels.append(("continue","Продовжити"))', launcher)

    def test_new_game_requires_confirmation_and_archives_previous_saves(self):
        launcher = (ROOT / "launcher.py").read_text(encoding="utf-8")
        game = (ROOT / "game.py").read_text(encoding="utf-8")
        self.assertIn('state="confirm_new"', launcher)
        self.assertIn('"confirm_yes"', launcher)
        self.assertIn('"confirm_no"', launcher)
        self.assertIn("archive_existing_files", game)
        self.assertNotIn("save_file.unlink", game)


    def test_hud_isolates_panel_event_and_render_failures(self):
        source = (ROOT / "ui" / "hud.py").read_text(encoding="utf-8")
        self.assertIn("def _safe_panel_event", source)
        self.assertIn("def _safe_panel_draw", source)
        self.assertIn("ui_errors.log", source)

    def test_build_panel_handles_empty_or_invalid_unlocked_catalog(self):
        source = (ROOT / "ui" / "build_panel.py").read_text(encoding="utf-8")
        self.assertIn("if not allowed_definitions:", source)
        self.assertIn("if self.selected_id not in allowed_ids:", source)

    def test_campaign_panel_handles_missing_chapter_data(self):
        source = (ROOT / "ui" / "campaign_panel.py").read_text(encoding="utf-8")
        self.assertIn("if not ch:", source)
        manager = (ROOT / "campaign" / "campaign_manager.py").read_text(encoding="utf-8")
        self.assertIn("if not self.chapters:", manager)

    def test_all_sidebar_sections_have_progression_rules(self):
        sidebar = (ROOT / "ui" / "sidebar.py").read_text(encoding="utf-8")
        progression = (ROOT / "progression" / "game_progression.py").read_text(encoding="utf-8")
        names = re.findall(r'\("[^"]+", "([^"]+)"\)', sidebar.split("def __init__", 1)[0])
        rules_text = progression.split("SECTION_REQUIREMENTS =", 1)[1].split("SECTION_COMPLETION =", 1)[0]
        rules = set(re.findall(r'"([^"]+)": \(', rules_text))
        for name in names:
            self.assertIn(name, rules, name)

if __name__=="__main__": unittest.main()

```
