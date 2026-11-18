"""Readable progression-aware navigation with distinct vector symbols."""
import math
import pygame
from ui import theme


class Sidebar:
    WIDTH = 220
    ITEMS = [
        ("overview", "Огляд"), ("build", "Будівництво"), ("fleet", "Флот"),
        ("mining", "Видобуток"), ("research", "Дослідження"), ("planets", "Планети"),
        ("galaxy", "Галактична карта"), ("trade", "Торгівля"),
        ("automation", "Автоматизація"), ("campaign", "Кампанія"),
        ("progress", "Прогрес"), ("defense", "Оборона"),
        ("settings", "Налаштування"),
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
        self.scroll_offset = 0
        self._item_step = 40
        self._list_rect = pygame.Rect(0, 0, 0, 0)
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
        dt = max(0.0, float(dt))
        self._pulse_clock += dt
        for name in list(self._pulse):
            self._pulse[name] = max(0.0, self._pulse[name] - dt)
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

    def _max_scroll(self):
        visible = max(1, self._list_rect.height // max(1, self._item_step))
        return max(0, len(self.ITEMS) - visible)

    def handle_event(self, event, tooltip):
        if event.type == pygame.MOUSEWHEEL:
            if self._list_rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset = max(0, min(self._max_scroll(),
                                                 self.scroll_offset - event.y))
                return None
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

    @staticmethod
    def _draw_icon(surface, kind, center, color):
        """Small semantic vector icons; independent of font glyph coverage."""
        x, y = center
        if kind == "overview":
            pygame.draw.circle(surface, color, (x, y), 8, 2)
            pygame.draw.circle(surface, color, (x, y), 2)
            pygame.draw.line(surface, color, (x, y-11), (x, y-6), 2)
            pygame.draw.line(surface, color, (x+6, y+6), (x+10, y+10), 2)
        elif kind == "build":
            pygame.draw.rect(surface, color, (x-8, y-7, 16, 14), 2, border_radius=2)
            pygame.draw.line(surface, color, (x-8, y-2), (x+8, y-2), 2)
            pygame.draw.line(surface, color, (x, y-7), (x, y+7), 2)
        elif kind == "fleet":
            pygame.draw.polygon(surface, color, [(x, y-10), (x+8, y+7), (x, y+4), (x-8, y+7)], 2)
            pygame.draw.line(surface, color, (x, y+4), (x, y+10), 2)
        elif kind == "mining":
            pygame.draw.line(surface, color, (x-8, y+8), (x+7, y-7), 3)
            pygame.draw.line(surface, color, (x+2, y-9), (x+9, y-2), 3)
            pygame.draw.line(surface, color, (x-9, y+8), (x-3, y+8), 2)
        elif kind == "research":
            pygame.draw.circle(surface, color, (x, y), 8, 2)
            pygame.draw.circle(surface, color, (x, y), 2)
            for dx, dy in ((0,-11),(11,0),(0,11),(-11,0)):
                pygame.draw.line(surface, color, (x+dx//2, y+dy//2), (x+dx, y+dy), 2)
        elif kind == "planets":
            pygame.draw.circle(surface, color, (x, y), 8, 2)
            pygame.draw.ellipse(surface, color, (x-12, y-4, 24, 9), 1)
        elif kind == "galaxy":
            pygame.draw.circle(surface, color, (x, y), 2)
            pygame.draw.ellipse(surface, color, (x-11, y-5, 22, 10), 2)
            pygame.draw.ellipse(surface, color, (x-5, y-11, 10, 22), 1)
        elif kind == "trade":
            pygame.draw.line(surface, color, (x-10, y-5), (x+8, y-5), 2)
            pygame.draw.polygon(surface, color, [(x+8,y-9),(x+12,y-5),(x+8,y-1)])
            pygame.draw.line(surface, color, (x+10, y+5), (x-8, y+5), 2)
            pygame.draw.polygon(surface, color, [(x-8,y+1),(x-12,y+5),(x-8,y+9)])
        elif kind == "automation":
            pygame.draw.circle(surface, color, (x, y), 5, 2)
            for a in range(0, 360, 45):
                r1, r2 = 7, 11
                p1 = (x+int(math.cos(math.radians(a))*r1), y+int(math.sin(math.radians(a))*r1))
                p2 = (x+int(math.cos(math.radians(a))*r2), y+int(math.sin(math.radians(a))*r2))
                pygame.draw.line(surface, color, p1, p2, 2)
        elif kind == "campaign":
            pygame.draw.polygon(surface, color, [(x-7,y+10),(x-7,y-10),(x+8,y-6),(x+8,y+5)], 2)
            pygame.draw.line(surface, color, (x-7,y-10), (x-7,y+11), 2)
        elif kind == "progress":
            pygame.draw.line(surface, color, (x-9,y+9), (x-9,y-8), 2)
            pygame.draw.line(surface, color, (x-9,y+9), (x+10,y+9), 2)
            pygame.draw.lines(surface, color, False, [(x-6,y+4),(x-1,y),(x+3,y+2),(x+9,y-7)], 2)
        elif kind == "defense":
            pygame.draw.polygon(surface, color, [(x,y-11),(x+9,y-7),(x+7,y+5),(x,y+11),(x-7,y+5),(x-9,y-7)], 2)
            pygame.draw.line(surface, color, (x,y-5), (x,y+5), 2)
        elif kind == "settings":
            pygame.draw.circle(surface, color, (x,y), 8, 2)
            pygame.draw.circle(surface, color, (x,y), 3, 2)
            for a in range(0,360,60):
                p1=(x+int(math.cos(math.radians(a))*9),y+int(math.sin(math.radians(a))*9))
                p2=(x+int(math.cos(math.radians(a))*12),y+int(math.sin(math.radians(a))*12))
                pygame.draw.line(surface,color,p1,p2,2)

    def draw(self, surface):
        x, y = 12, 86
        h = surface.get_height()
        panel_h = max(360, h - 190)
        rect = pygame.Rect(x, y, self.WIDTH, panel_h)
        theme.panel(surface, rect, fill=(8, 18, 33))
        theme.label(surface, "НАВІГАЦІЯ", (x + 16, y + 13), 13, theme.TEXT, True)
        self.rects.clear()
        list_top = y + 39
        footer_h = 39
        self._list_rect = pygame.Rect(x+5, list_top, self.WIDTH-10,
                                      max(80, panel_h-48-footer_h))
        available_h = self._list_rect.height
        self._item_step = max(31, min(45, available_h // min(len(self.ITEMS), 13)))
        visible_count = max(1, available_h // self._item_step)
        self.scroll_offset = max(0, min(self._max_scroll(), self.scroll_offset))
        for index in range(self.scroll_offset, min(len(self.ITEMS), self.scroll_offset+visible_count)):
            kind, name = self.ITEMS[index]
            item_y = list_top + (index-self.scroll_offset)*self._item_step
            r = pygame.Rect(x+7, item_y, self.WIDTH-14, self._item_step-3)
            self.rects[name] = r
            state, _ = self._state(name)
            locked, completed = state == "LOCKED", state == "COMPLETED"
            pulse = self._pulse.get(name, 0.0)
            if name == self.active:
                pygame.draw.rect(surface, (18, 61, 88), r, border_radius=7)
                pygame.draw.rect(surface, theme.CYAN, (r.x, r.y+5, 4, r.height-10), border_radius=2)
                pygame.draw.rect(surface, theme.BORDER_BRIGHT, r, 1, border_radius=7)
            elif pulse > 0:
                alpha = int(65 + 80*(0.5+0.5*math.sin(self._pulse_clock*7)))
                glow = pygame.Surface((r.width,r.height), pygame.SRCALPHA)
                glow.fill((35,190,220,alpha)); surface.blit(glow,r.topleft)
                pygame.draw.rect(surface,theme.CYAN,r,1,border_radius=7)
            elif self.hovered == name:
                pygame.draw.rect(surface,(15,39,59),r,border_radius=7)
                pygame.draw.rect(surface,(58,125,157),r,1,border_radius=7)
            if locked:
                icon_color, label_color = (125,145,164), (164,181,197)
            elif completed:
                icon_color, label_color = theme.GREEN, theme.GREEN
            else:
                icon_color = theme.CYAN if name == self.active or pulse > 0 else (115,190,215)
                label_color = theme.TEXT if name == self.active or pulse > 0 else (202,220,235)
            icon_box = pygame.Rect(r.x+8,r.y+5,31,r.height-10)
            pygame.draw.rect(surface,(11,34,53),icon_box,border_radius=5)
            icon_assets = {"overview":"overview", "build":"construction", "fleet":"ship",
                           "mining":"mining", "research":"research", "planets":"planet",
                           "galaxy":"galaxy", "trade":"trade", "automation":"automation",
                           "campaign":"campaign", "progress":"progress", "defense":"defense",
                           "settings":"settings"}
            self._draw_icon(surface, kind, icon_box.center, icon_color)
            theme.label(surface,name,(r.x+48,r.y+max(5,(r.height-17)//2)),
                        15,label_color,name == self.active or completed)
            if locked:
                lx,ly=r.right-20,r.y+max(5,(r.height-17)//2)
                pygame.draw.arc(surface,(145,165,184),(lx+3,ly,10,10),0,math.pi,2)
                pygame.draw.rect(surface,(145,165,184),(lx,ly+6,16,12),border_radius=2)
                pygame.draw.circle(surface,(30,44,59),(lx+8,ly+11),1)
            elif completed:
                theme.label(surface,"✓",(r.right-23,r.y+5),15,theme.GREEN,True)
        bottom = pygame.Rect(x+9,y+panel_h-38,self.WIDTH-18,27)
        pygame.draw.line(surface,theme.BORDER,(bottom.x+2,bottom.y),(bottom.right-2,bottom.y),1)
        pygame.draw.circle(surface,theme.GREEN,(bottom.x+9,bottom.y+14),3)
        theme.label(surface,"СИСТЕМИ ПРАЦЮЮТЬ",(bottom.x+19,bottom.y+7),10,theme.GREEN,True)
