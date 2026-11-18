"""Interactive galaxy navigation screen with pan, zoom, routes and scout expeditions."""
import math
import pygame
from ui import theme


class GalaxyPanel:
    def __init__(self, galaxy, fleet, bottom):
        self.galaxy, self.fleet, self.bottom = galaxy, fleet, bottom
        self.visible = False
        self.zoom = 0.30
        self.pan = pygame.Vector2(0, 0)
        self.dragging = False
        self.drag_origin = None
        self.pan_origin = None
        self.route_mode = False
        self.route_start = None
        self.route_end = None
        self.map_rect = pygame.Rect(220, 90, 900, 650)
        self.route_button = pygame.Rect(0, 0, 170, 36)
        self.expedition_button = pygame.Rect(0, 0, 190, 36)
        self.center_button = pygame.Rect(0, 0, 90, 36)
        self._screen_size = (1600, 900)

    def open(self):
        self.visible = True
    def close(self):
        self.visible = False
        self.dragging = False

    def _layout(self, surface):
        w, h = surface.get_size()
        self._screen_size = (w, h)
        self.map_rect = pygame.Rect(220, 88, max(360, w-520), max(280, h-190))
        bx, by = self.map_rect.x+18, self.map_rect.y+16
        self.route_button = pygame.Rect(bx, by, 170, 36)
        self.expedition_button = pygame.Rect(bx+180, by, 190, 36)
        self.center_button = pygame.Rect(bx+380, by, 90, 36)

    def _to_screen(self, system):
        center = pygame.Vector2(self.map_rect.center)
        p = pygame.Vector2(system["x"], system["y"])
        return center + (p + self.pan) * self.zoom

    def _hit_system(self, pos):
        nearest, nearest_dist = None, 20
        for system in self.galaxy.systems.values():
            point = self._to_screen(system)
            d = math.hypot(point.x-pos[0], point.y-pos[1])
            if d < nearest_dist:
                nearest, nearest_dist = system, d
        return nearest

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEWHEEL:
            if self.map_rect.collidepoint(pygame.mouse.get_pos()):
                old = self.zoom
                self.zoom = max(0.18, min(1.35, self.zoom * (1.12 if event.y > 0 else 1/1.12)))
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2):
            pos = event.pos
            if self.route_button.collidepoint(pos):
                target = self.galaxy.get_system(self.galaxy.selected_system)
                origins = [s for s in self.galaxy.systems.values() if s["discovered"] and
                           s["id"] in target["neighbors"]]
                if origins and not target["discovered"]:
                    ok, msg = self.galaxy.plot_route(origins[0]["id"], target["id"])
                elif target["discovered"]:
                    neighbors = [n for n in target["neighbors"] if self.galaxy.systems[n]["accessible"]]
                    ok, msg = (self.galaxy.plot_route(target["id"], neighbors[0]) if neighbors
                               else (False, "Немає доступної сусідньої системи для маршруту."))
                else:
                    ok, msg = False, "Спочатку виберіть сусідню до дослідженої систему."
                self.bottom.push(msg)
                return True
            if self.expedition_button.collidepoint(pos):
                target_id = self.galaxy.selected_system
                ok, msg = self.galaxy.launch_expedition(self.fleet, target_id)
                self.bottom.push(msg)
                return True
            if self.center_button.collidepoint(pos):
                self.pan.update(0, 0)
                self.zoom = 0.30
                return True
            if self.map_rect.collidepoint(pos):
                hit = self._hit_system(pos)
                if event.button == 1 and hit:
                    self.galaxy.selected_system = hit["id"]
                    return True
                if event.button == 2 or (event.button == 1 and not hit):
                    self.dragging = True
                    self.drag_origin = pygame.Vector2(pos)
                    self.pan_origin = self.pan.copy()
                    return True
            return False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            delta = (pygame.Vector2(event.pos)-self.drag_origin)/max(0.01,self.zoom)
            self.pan = self.pan_origin + delta
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button in (1,2) and self.dragging:
            self.dragging = False
            return True
        return False

    def update(self, dt):
        self.galaxy.update(self.fleet)
        for message in self.galaxy.take_events():
            self.bottom.push(message)

    def draw(self, surface):
        if not self.visible:
            return
        self._layout(surface)
        w, h = surface.get_size()
        pygame.draw.rect(surface, (4, 9, 22), self.map_rect, border_radius=8)
        pygame.draw.rect(surface, theme.BORDER_BRIGHT, self.map_rect, 1, border_radius=8)
        clip = surface.get_clip()
        surface.set_clip(self.map_rect)
        # Subtle grid and nebula-like glow.
        grid_step = max(42, int(100*self.zoom))
        start_x = self.map_rect.left + int(self.pan.x*self.zoom) % grid_step
        start_y = self.map_rect.top + int(self.pan.y*self.zoom) % grid_step
        for x in range(start_x, self.map_rect.right, grid_step):
            pygame.draw.line(surface, (12, 28, 48), (x,self.map_rect.top), (x,self.map_rect.bottom), 1)
        for y in range(start_y, self.map_rect.bottom, grid_step):
            pygame.draw.line(surface, (12, 28, 48), (self.map_rect.left,y), (self.map_rect.right,y), 1)
        # Trade routes and player-plotted routes.
        for a_id,b_id in self.galaxy.trade_routes:
            a,b=self.galaxy.systems[a_id],self.galaxy.systems[b_id]
            pygame.draw.line(surface,(70,125,145),self._to_screen(a),self._to_screen(b),2)
        for route in self.galaxy.plotted_routes:
            a,b=self.galaxy.systems[route["from"]],self.galaxy.systems[route["to"]]
            p1,p2=self._to_screen(a),self._to_screen(b)
            delta=p2-p1
            length=max(1,delta.length())
            direction=delta/length
            for d in range(0,int(length),18):
                pygame.draw.line(surface,theme.CYAN,p1+direction*d,p1+direction*min(d+9,length),2)
        # Known connections appear faintly, including paths into the frontier.
        for system in self.galaxy.systems.values():
            for neighbor_id in system["neighbors"]:
                if system["id"] < neighbor_id:
                    other=self.galaxy.systems[neighbor_id]
                    if system["discovered"] or other["discovered"]:
                        pygame.draw.line(surface,(24,54,75),self._to_screen(system),self._to_screen(other),1)
        # System markers.
        selected=self.galaxy.get_system(self.galaxy.selected_system)
        for system in self.galaxy.systems.values():
            p=self._to_screen(system)
            if not self.map_rect.inflate(80,80).collidepoint(p):
                continue
            if not system["accessible"]:
                pygame.draw.circle(surface,(40,52,69),p,5)
                pygame.draw.circle(surface,(65,80,101),p,8,1)
                continue
            color={"yellow":(255,220,130),"blue":(125,185,255),"red":(255,140,135),
                   "white":(220,235,255),"orange":(255,175,105)}.get(system["star_color"],theme.CYAN)
            if system["discovered"]:
                pygame.draw.circle(surface,color,p, max(5,int(8*self.zoom)),0)
                pygame.draw.circle(surface,(255,255,255),p,max(8,int(13*self.zoom)),1)
            else:
                pygame.draw.circle(surface,(95,135,160),p,6,1)
                pygame.draw.circle(surface,(75,105,130),p,2)
            if system["id"]==selected["id"]:
                pygame.draw.circle(surface,theme.CYAN,p,18,2)
                pygame.draw.circle(surface,theme.CYAN,p,23,1)
            name=system["name"] if system["discovered"] else "???"
            surface.blit(theme.font(12,True).render(name,True,
                theme.TEXT if system["discovered"] else theme.MUTED),(p.x+12,p.y-7))
            # Object count hints for discovered systems.
            if system["discovered"]:
                count=sum(1 for obj in system["objects"] if obj["revealed"])
                surface.blit(theme.font(10).render(f"{count} об'єкт.",True,theme.MUTED),(p.x+12,p.y+8))
                object_colors = {"Планета":(95,170,220), "Астероїдне поле":(180,165,125),
                                 "Покинута станція":(190,145,225), "Невідомий об'єкт":(235,105,130)}
                for oi,obj in enumerate(system["objects"]):
                    if obj["revealed"]:
                        angle=(oi/max(1,len(system["objects"])))*math.tau
                        orbit=max(20,int(25*self.zoom))
                        marker=(int(p.x+math.cos(angle)*orbit),int(p.y+math.sin(angle)*orbit))
                        pygame.draw.circle(surface,object_colors.get(obj["type"],theme.MUTED),marker,3)
        surface.set_clip(clip)
        # Map controls.
        for rect,text in ((self.route_button,"Прокласти маршрут"),
                          (self.expedition_button,"Відправити розвідку"),
                          (self.center_button,"Центр")):
            pygame.draw.rect(surface,(14,43,65),rect,border_radius=5)
            pygame.draw.rect(surface,theme.BORDER_BRIGHT,rect,1,border_radius=5)
            rendered=theme.font(12,True).render(text,True,theme.TEXT)
            surface.blit(rendered,rendered.get_rect(center=rect.center))
        theme.label(surface,"ГАЛАКТИЧНА КАРТА",(self.map_rect.x+18,self.map_rect.y+62),18,theme.CYAN,True)
        theme.label(surface,"Колесо миші — масштаб • перетягування — переміщення",(self.map_rect.x+18,self.map_rect.bottom-25),11,theme.MUTED)
        # Detail pane.
        info=pygame.Rect(w-286,88,274,h-190)
        theme.panel(surface,info,fill=(8,18,34),border=theme.BORDER)
        x,y=info.x+16,info.y+16
        theme.label(surface,"СИСТЕМА",(x,y),11,theme.MUTED,True)
        theme.label(surface,selected["name"] if selected["discovered"] else "Невідома система",(x,y+24),20,theme.CYAN,True)
        state="ДОСЛІДЖЕНА" if selected["discovered"] else ("ДОСТУПНА" if selected["accessible"] else "ЗАБЛОКОВАНА")
        state_color=theme.GREEN if selected["discovered"] else (theme.GOLD if selected["accessible"] else theme.RED)
        theme.label(surface,state,(x,y+55),11,state_color,True)
        theme.label(surface,f"Координати: {selected['x']}, {selected['y']}",(x,y+82),11,theme.MUTED)
        yy=y+116
        theme.label(surface,"ОБ'ЄКТИ СИСТЕМИ",(x,yy),11,theme.CYAN,True); yy+=24
        if selected["discovered"]:
            for obj in selected["objects"]:
                if obj["revealed"]:
                    theme.label(surface,f"• {obj['type']}: {obj['name']}",(x,yy),11,theme.TEXT)
                    yy+=20
        else:
            theme.label(surface,"Сканування не виконано.",(x,yy),11,theme.MUTED); yy+=22
            theme.label(surface,"Об'єкти приховані до",(x,yy),11,theme.MUTED); yy+=18
            theme.label(surface,"повернення експедиції.",(x,yy),11,theme.MUTED)
        yy=max(yy+16,y+270)
        theme.label(surface,"ЕКСПЕДИЦІЯ",(x,yy),11,theme.CYAN,True); yy+=22
        scout=self.galaxy.available_scouts(self.fleet)
        if not selected["discovered"] and selected["accessible"] and scout:
            ship=scout[0]
            scan_time=(45+ self.galaxy.route_distance("sol",selected["id"])*0.025) / getattr(self.fleet, "technology_bonuses", {}).get("fleet_mission_speed_multiplier",1.0)
            total=self.galaxy.route_time("sol",selected["id"],ship.speed,scan_time)
            theme.label(surface,f"Корабель: {ship.name}",(x,yy),11,theme.TEXT); yy+=20
            theme.label(surface,f"Час повного циклу: {int(total)} с",(x,yy),11,theme.GREEN); yy+=20
            theme.label(surface,"Потрібне паливо резервується",(x,yy),10,theme.MUTED); yy+=15
        elif not scout:
            theme.label(surface,"Немає вільного розвідника.",(x,yy),11,theme.GOLD)
        else:
            theme.label(surface,"Система вже відкрита.",(x,yy),11,theme.MUTED)
        yy+=22
        active=list(self.galaxy.expeditions.values())
        theme.label(surface,f"Активні експедиції: {len(active)}",(x,yy),11,theme.TEXT)
        yy+=22
        theme.label(surface,f"Відкрито систем: {sum(1 for s in self.galaxy.systems.values() if s['discovered'])}/20",(x,yy),11,theme.GREEN)
