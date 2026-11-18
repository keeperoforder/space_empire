"""Fleet command UI: roster, ship cards, production, upgrades and task groups."""
import pygame
from ui import theme
from fleet.spaceship import SHIP_TYPES

class FleetPanel:
    def __init__(self, manager, event_log):
        self.manager, self.event_log = manager, event_log
        self.visible = False
        self.selected_ship_id = manager.ships[0].id if manager.ships else None
        self.selected_ids = set()
        self.ship_rows, self.build_rows, self.upgrade_rows = {}, {}, {}
        self.group_rect = pygame.Rect(0,0,0,0)
        self.task_rect = pygame.Rect(0,0,0,0)
        self.close_rect = pygame.Rect(0,0,0,0)
        self.panel_rect = pygame.Rect(0,0,0,0)
        self.build_type = "transport"

    def open(self): self.visible = True
    def close(self): self.visible = False

    def handle_event(self, event):
        if not self.visible or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        if self.close_rect.collidepoint(pos):
            self.close(); return True
        for sid, rect in self.ship_rows.items():
            if rect.collidepoint(pos):
                self.selected_ship_id = sid
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    if sid in self.selected_ids: self.selected_ids.remove(sid)
                    else: self.selected_ids.add(sid)
                else:
                    self.selected_ids = {sid}
                return True
        for kind, rect in self.build_rows.items():
            if rect.collidepoint(pos):
                ok, msg = self.manager.build_ship(kind)
                self.event_log.push(msg, theme.GREEN if ok else theme.RED)
                return True
        if self.group_rect.collidepoint(pos):
            ids = list(self.selected_ids) or ([self.selected_ship_id] if self.selected_ship_id else [])
            ok, result = self.manager.create_group("Оперативна група", ids)
            self.event_log.push("Групу створено." if ok else result, theme.GREEN if ok else theme.RED)
            return True
        if self.task_rect.collidepoint(pos):
            group = next((g for g in self.manager.groups.values()
                          if set(g["ship_ids"]) == (self.selected_ids or {self.selected_ship_id})), None)
            if group:
                ok, msg = self.manager.dispatch_group(group["id"], "explore", 520, -360,
                                                      "Сектор E-7", 35)
            elif self.selected_ship_id:
                ok, msg = self.manager.assign_task(self.selected_ship_id, "explore", 520, -360,
                                                    "Сектор E-7", 35)
            else:
                ok, msg = False, "Оберіть корабель."
            self.event_log.push(msg, theme.GREEN if ok else theme.RED)
            return True
        for stat, rect in self.upgrade_rows.items():
            if rect.collidepoint(pos) and self.selected_ship_id:
                ok, msg = self.manager.upgrade_ship(self.selected_ship_id, stat)
                self.event_log.push(msg, theme.GREEN if ok else theme.RED)
                return True
        return self.panel_rect.collidepoint(pos)

    def draw(self, surface):
        if not self.visible: return
        w,h = surface.get_size()
        x,y = 220,86
        pw,ph = 510,min(730,h-180)
        self.panel_rect=pygame.Rect(x,y,pw,ph)
        theme.panel(surface,self.panel_rect,fill=(7,17,32),border=theme.CYAN_DIM)
        theme.label(surface,"КОСМІЧНИЙ ФЛОТ",(x+16,y+13),15,theme.CYAN,True)
        theme.label(surface,"SHIPYARD • COMMAND • LOGISTICS",(x+16,y+35),9,theme.MUTED,True)
        self.close_rect=pygame.Rect(x+pw-38,y+10,25,24)
        pygame.draw.rect(surface,theme.PANEL_HOVER,self.close_rect,border_radius=4)
        theme.label(surface,"×",(self.close_rect.x+8,self.close_rect.y+2),16,theme.TEXT)
        yy=y+62
        theme.label(surface,f"СКЛАД ФЛОТУ: {len(self.manager.ships)} КОРАБЛІВ",(x+15,yy),10,theme.MUTED,True)
        yy+=20
        self.ship_rows={}
        for ship in self.manager.ships[:9]:
            rect=pygame.Rect(x+13,yy,pw-26,25); self.ship_rows[ship.id]=rect
            if ship.id in self.selected_ids or ship.id==self.selected_ship_id:
                pygame.draw.rect(surface,(17,53,77),rect,border_radius=4)
            spec=SHIP_TYPES[ship.ship_type]
            theme.label(surface,f"{ship.name}  •  {spec['role']}",(rect.x+7,rect.y+5),9,theme.TEXT)
            theme.label(surface,f"{ship.status.upper()}  L{ship.level}",(rect.right-105,rect.y+5),8,
                        theme.GREEN if ship.status=="ready" else theme.GOLD)
            yy+=28
        selected=next((s for s in self.manager.ships if s.id==self.selected_ship_id),None)
        yy+=3
        if selected:
            theme.label(surface,f"КАРТКА: {selected.name}",(x+15,yy),10,theme.CYAN,True); yy+=17
            theme.label(surface,f"Тип: {SHIP_TYPES[selected.ship_type]['name']}  |  Завдання: {selected.task}",(x+15,yy),9); yy+=15
            theme.label(surface,f"Корпус: {selected.hull:.0f}/{selected.max_hull:.0f}  |  Швидкість: {selected.speed:.0f}",(x+15,yy),9); yy+=15
            theme.label(surface,f"Вантаж: {selected.cargo_capacity:.0f}  |  Обслуговування: {SHIP_TYPES[selected.ship_type]['maintenance']:.2f} кр/с",(x+15,yy),9,theme.MUTED); yy+=18
        self.upgrade_rows={}
        for stat,label in (("speed","ШВИДКІСТЬ"),("hull","КОРПУС"),("cargo","ВАНТАЖ")):
            rect=pygame.Rect(x+14,yy,105,23); self.upgrade_rows[stat]=rect
            pygame.draw.rect(surface,(29,48,69),rect,border_radius=4)
            theme.label(surface,label,(rect.x+8,rect.y+6),8,theme.TEXT,True)
            yy+=26
        yy+=3
        theme.label(surface,"ВИРОБНИЦТВО (ПОТРІБЕН ПОБУДОВАНИЙ АНГАР)",(x+15,yy),9,theme.MUTED,True); yy+=17
        self.build_rows={}
        for kind,spec in SHIP_TYPES.items():
            rect=pygame.Rect(x+14,yy,pw-28,21); self.build_rows[kind]=rect
            pygame.draw.rect(surface,(15,37,57),rect,border_radius=3)
            theme.label(surface,f"+ {spec['name']}  •  {spec['build_time']} с",(rect.x+7,rect.y+4),8,theme.TEXT)
            theme.label(surface,f"{spec['cost']['metal']} M",(rect.right-60,rect.y+4),8,theme.GREEN)
            yy+=23
        if self.manager.constructions:
            pr=self.manager.constructions[0]
            pct=100*pr["elapsed"]/pr["duration"]
            theme.label(surface,f"ВИРОБНИЦТВО: {SHIP_TYPES[pr['ship_type']]['name']} {pct:.0f}%",(x+15,y+ph-62),9,theme.GOLD,True)
        self.group_rect=pygame.Rect(x+14,y+ph-37,205,25)
        self.task_rect=pygame.Rect(x+230,y+ph-37,265,25)
        for rect,label in ((self.group_rect,"СТВОРИТИ ГРУПУ (CTRL+CLICK)"),(self.task_rect,"ВІДПРАВИТИ НА РОЗВІДКУ")):
            pygame.draw.rect(surface,(30,64,83),rect,border_radius=4)
            theme.label(surface,label,(rect.x+7,rect.y+7),8,theme.TEXT,True)
