"""Fleet management panel: ship selection, asteroid assignment and upgrades."""
import pygame
from ui import theme


class MiningPanel:
    def __init__(self, manager, event_log):
        self.manager = manager
        self.event_log = event_log
        self.visible = False
        self.selected_ship_id = manager.ships[0].id if manager.ships else None
        self.selected_asteroid_id = next(iter(manager.asteroids))
        self.ship_rows = {}
        self.asteroid_rows = {}
        self.assign_rect = pygame.Rect(0,0,0,0)
        self.build_rect = pygame.Rect(0,0,0,0)
        self.upgrade_rects = {}
        self.close_rect = pygame.Rect(0,0,0,0)
        self.panel_rect = pygame.Rect(0,0,0,0)

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False

    def handle_event(self, event):
        if not self.visible or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        if self.close_rect.collidepoint(pos):
            self.close()
            return True
        for ship_id, rect in self.ship_rows.items():
            if rect.collidepoint(pos):
                self.selected_ship_id = ship_id
                return True
        for asteroid_id, rect in self.asteroid_rows.items():
            if rect.collidepoint(pos):
                self.selected_asteroid_id = asteroid_id
                return True
        if self.assign_rect.collidepoint(pos) and self.selected_ship_id:
            ok, message = self.manager.assign_ship(self.selected_ship_id, self.selected_asteroid_id)
            self.event_log.push(message, theme.GREEN if ok else theme.RED)
            return True
        if self.build_rect.collidepoint(pos):
            ok, message = self.manager.build_ship()
            self.event_log.push(message, theme.GREEN if ok else theme.RED)
            if ok:
                self.selected_ship_id = self.manager.ships[-1].id
            return True
        for upgrade, rect in self.upgrade_rects.items():
            if rect.collidepoint(pos) and self.selected_ship_id:
                ok, message = self.manager.upgrade_ship(self.selected_ship_id, upgrade)
                self.event_log.push(message, theme.GREEN if ok else theme.RED)
                return True
        return self.panel_rect.collidepoint(pos)

    def draw(self, surface):
        if not self.visible:
            return
        w,h = surface.get_size()
        x,y = 220,86
        ph = min(720,h-180)
        self.panel_rect = pygame.Rect(x,y,440,ph)
        theme.panel(surface,self.panel_rect,fill=(7,17,32),border=theme.CYAN_DIM)
        theme.label(surface,"ГІРНИЧИЙ ФЛОТ",(x+16,y+13),15,theme.CYAN,True)
        theme.label(surface,"AUTOMATED MINING OPERATIONS",(x+16,y+35),9,theme.MUTED,True)
        self.close_rect=pygame.Rect(x+402,y+10,25,24)
        pygame.draw.rect(surface,theme.PANEL_HOVER,self.close_rect,border_radius=4)
        theme.label(surface,"×",(x+410,y+12),16,theme.TEXT)
        yy=y+68
        theme.label(surface,f"КОРАБЛІ: {len(self.manager.ships)}",(x+16,yy),10,theme.MUTED,True)
        yy+=22
        self.ship_rows.clear()
        for ship in self.manager.ships[:5]:
            rect=pygame.Rect(x+14,yy,412,30)
            self.ship_rows[ship.id]=rect
            if ship.id==self.selected_ship_id:
                pygame.draw.rect(surface,(17,53,77),rect,border_radius=4)
                pygame.draw.rect(surface,theme.CYAN_DIM,rect,1,border_radius=4)
            target_name = self.manager.asteroids[ship.assigned_target_id].name.replace("Астероїд ", "")
            theme.label(surface,f"{ship.id}  •  {ship.task.upper()}  → {target_name}",
                        (rect.x+8,rect.y+5),9,theme.TEXT,ship.id==self.selected_ship_id)
            theme.label(surface,f"{ship.cargo:.0f}/{ship.cargo_capacity:.0f}",
                        (rect.right-86,rect.y+5),10,theme.GREEN)
            yy+=34

        self.build_rect=pygame.Rect(x+14,yy+2,196,28)
        pygame.draw.rect(surface,(18,75,91),self.build_rect,border_radius=4)
        theme.label(surface,"+ ПОБУДУВАТИ КОРАБЕЛЬ",(self.build_rect.x+8,self.build_rect.y+8),9,theme.TEXT,True)
        selected=next((s for s in self.manager.ships if s.id==self.selected_ship_id),None)
        if selected:
            theme.label(surface,f"ШВИДКІСТЬ {selected.speed:.0f}  •  ВИДОБУТОК {selected.mining_rate:.1f}/с",
                        (x+16,yy+42),9,theme.MUTED)
            theme.label(surface,f"ВАНТАЖ {selected.cargo:.1f}/{selected.cargo_capacity:.0f}  •  ЗАВДАННЯ {selected.task}",
                        (x+16,yy+58),9,theme.MUTED)
        yy+=80
        theme.label(surface,"АСТЕРОЇД ДЛЯ ПРИЗНАЧЕННЯ",(x+16,yy),10,theme.MUTED,True)
        yy+=19
        self.asteroid_rows.clear()
        for asteroid in self.manager.asteroids.values():
            rect=pygame.Rect(x+14,yy,412,26)
            self.asteroid_rows[asteroid.id]=rect
            if asteroid.id==self.selected_asteroid_id:
                pygame.draw.rect(surface,(16,48,67),rect,border_radius=4)
            theme.label(surface,asteroid.name,(rect.x+8,rect.y+6),9,theme.TEXT)
            theme.label(surface,f"{asteroid.reserve:.0f} руди",(rect.right-90,rect.y+6),9,theme.GREEN)
            yy+=29
        self.assign_rect=pygame.Rect(x+14,yy+2,196,27)
        pygame.draw.rect(surface,(48,57,85),self.assign_rect,border_radius=4)
        theme.label(surface,"ПРИЗНАЧИТИ КОРАБЕЛЬ",(self.assign_rect.x+9,self.assign_rect.y+8),9,theme.TEXT,True)
        yy+=42
        theme.label(surface,"ПОКРАЩЕННЯ ОБРАНОГО КОРАБЛЯ",(x+16,yy),9,theme.MUTED,True)
        yy+=20
        self.upgrade_rects={}
        for upgrade,label in (("speed","Швидкість"),("capacity","Місткість"),("mining","Видобуток")):
            rect=pygame.Rect(x+14,yy,126,28)
            self.upgrade_rects[upgrade]=rect
            pygame.draw.rect(surface,(29,48,69),rect,border_radius=4)
            pygame.draw.rect(surface,theme.BORDER,rect,1,border_radius=4)
            theme.label(surface,label,(rect.x+10,rect.y+8),9,theme.TEXT)
            yy+=33
        theme.label(surface,"Вартість корабля: 140 металу, 25 палива, 90 кредитів",
                    (x+16,y+ph-27),8,theme.MUTED)
