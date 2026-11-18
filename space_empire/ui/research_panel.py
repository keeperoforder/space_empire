"""Scrollable, zoomable technology tree and research details."""
import pygame
from ui import theme
from graphics.asset_library import scaled_sprite

STATE_LABELS = {
    "locked": "ЗАБЛОКОВАНО", "available": "ДОСТУПНО",
    "researching": "ДОСЛІДЖУЄТЬСЯ", "completed": "ДОСЛІДЖЕНО"
}
STATE_COLORS = {"locked": theme.MUTED, "available": theme.CYAN,
                "researching": theme.GOLD, "completed": theme.GREEN}

class ResearchPanel:
    def __init__(self, manager, event_log):
        self.manager, self.event_log = manager, event_log
        self.visible = False
        self.selected_id = next((t["id"] for t in manager.technologies.values()
                                 if t["state"] == "available"), next(iter(manager.technologies)))
        self.zoom = 0.82
        self.scroll_x = 0.0
        self.scroll_y = 0.0
        self.tree_rect = pygame.Rect(0,0,0,0)
        self.detail_rect = pygame.Rect(0,0,0,0)
        self.research_rect = pygame.Rect(0,0,0,0)
        self.close_rect = pygame.Rect(0,0,0,0)
        self.zoom_in_rect = pygame.Rect(0,0,0,0)
        self.zoom_out_rect = pygame.Rect(0,0,0,0)
        self.dragging = False
        self.drag_last = None

    def open(self): self.visible = True
    def close(self): self.visible = False

    def _bounds(self):
        return 1700*self.zoom, 760*self.zoom

    def _node_rect(self, tech):
        x = self.tree_rect.x + int(tech["x"]*self.zoom-self.scroll_x)
        y = self.tree_rect.y + int(tech["y"]*self.zoom-self.scroll_y)
        w,h = int(174*self.zoom),int(76*self.zoom)
        return pygame.Rect(x,y,max(112,w),max(54,h))

    def handle_event(self,event):
        if not self.visible: return False
        if event.type == pygame.MOUSEWHEEL:
            if self.tree_rect.collidepoint(pygame.mouse.get_pos()):
                mods=pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    old=self.zoom
                    self.zoom=max(0.55,min(1.25,self.zoom+event.y*0.06))
                    factor=self.zoom/old
                    self.scroll_x*=factor; self.scroll_y*=factor
                elif mods & pygame.KMOD_SHIFT:
                    self.scroll_x=max(0.0,self.scroll_x-event.y*95)
                else:
                    self.scroll_y=max(0.0,self.scroll_y-event.y*85)
                self._clamp_scroll()
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos=event.pos
            if self.close_rect.collidepoint(pos):
                self.close(); return True
            if self.zoom_in_rect.collidepoint(pos):
                self.zoom=min(1.25,self.zoom+0.08); self._clamp_scroll(); return True
            if self.zoom_out_rect.collidepoint(pos):
                self.zoom=max(0.55,self.zoom-0.08); self._clamp_scroll(); return True
            if self.research_rect.collidepoint(pos):
                if self.selected_id:
                    ok,msg=self.manager.start_research(self.selected_id)
                    self.event_log.push(msg,theme.GREEN if ok else theme.RED)
                return True
            if self.tree_rect.collidepoint(pos):
                for tech in self.manager.technologies.values():
                    if self._node_rect(tech).collidepoint(pos):
                        self.selected_id=tech["id"]
                        return True
                self.dragging=True; self.drag_last=pos
                return True
            if self.detail_rect.collidepoint(pos): return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging=False; self.drag_last=None
        if event.type == pygame.MOUSEMOTION and self.dragging:
            if self.drag_last:
                dx=event.pos[0]-self.drag_last[0]; dy=event.pos[1]-self.drag_last[1]
                self.scroll_x=max(0.0,self.scroll_x-dx)
                self.scroll_y=max(0.0,self.scroll_y-dy)
                self.drag_last=event.pos
                self._clamp_scroll()
            return True
        return False

    def _clamp_scroll(self):
        bw,bh=self._bounds()
        self.scroll_x=max(0.0,min(self.scroll_x,max(0.0,bw-self.tree_rect.width+40)))
        self.scroll_y=max(0.0,min(self.scroll_y,max(0.0,bh-self.tree_rect.height+40)))

    def draw(self,surface):
        if not self.visible: return
        sw,sh=surface.get_size()
        x,y=210,82
        w=max(520,sw-230); h=max(400,sh-174)
        outer=pygame.Rect(x,y,min(w,sw-x-10),min(h,sh-y-86))
        theme.panel(surface,outer,fill=(6,15,29),border=theme.CYAN_DIM)
        theme.label(surface,"ТЕХНОЛОГІЧНЕ ДЕРЕВО",(outer.x+15,outer.y+12),15,theme.CYAN,True)
        theme.label(surface,"7 ГІЛОК • ДОСЛІДЖЕННЯ • ПОСТІЙНІ БОНУСИ",(outer.x+15,outer.y+35),9,theme.MUTED,True)
        self.close_rect=pygame.Rect(outer.right-34,outer.y+9,24,22)
        pygame.draw.rect(surface,theme.PANEL_HOVER,self.close_rect,border_radius=4)
        theme.label(surface,"×",(self.close_rect.x+7,self.close_rect.y+1),16,theme.TEXT)
        self.zoom_out_rect=pygame.Rect(outer.right-115,outer.y+10,25,22)
        self.zoom_in_rect=pygame.Rect(outer.right-84,outer.y+10,25,22)
        for rect,label in ((self.zoom_out_rect,"−"),(self.zoom_in_rect,"+")):
            pygame.draw.rect(surface,(23,48,70),rect,border_radius=4)
            theme.label(surface,label,(rect.x+8,rect.y+2),14,theme.TEXT)
        self.detail_rect=pygame.Rect(outer.right-268,outer.y+56,252,outer.height-70)
        self.tree_rect=pygame.Rect(outer.x+12,outer.y+56,outer.width-292,outer.height-70)
        pygame.draw.rect(surface,(5,12,24),self.tree_rect,border_radius=5)
        pygame.draw.rect(surface,theme.BORDER,self.tree_rect,1,border_radius=5)
        old_clip=surface.get_clip()
        surface.set_clip(self.tree_rect)
        # Branch headers keep the seven research disciplines visually distinct.
        for index, branch in enumerate(self.manager.branches):
            bx=self.tree_rect.x+int((170+index*250)*self.zoom-self.scroll_x)
            by=self.tree_rect.y+int(92*self.zoom-self.scroll_y)
            theme.label(surface,branch["icon"]+"  "+branch["name"],(bx,by),
                        max(8,int(10*self.zoom)),branch["color"],True)
        # Branch connectors: prerequisites define graph edges, not fixed sequences.
        for tech in self.manager.technologies.values():
            target=self._node_rect(tech)
            for req in tech["prerequisites"]:
                parent=self.manager.get(req)
                source=self._node_rect(parent)
                start=(source.right,source.centery)
                end=(target.left,target.centery)
                color=theme.GREEN if parent["state"]=="completed" else theme.BORDER
                pygame.draw.line(surface,color,start,end,max(1,int(2*self.zoom)))
        for tech in self.manager.technologies.values():
            rect=self._node_rect(tech)
            if not self.tree_rect.colliderect(rect): continue
            color=STATE_COLORS[tech["state"]]
            fill=(13,29,48) if tech["state"]!="locked" else (10,20,34)
            pygame.draw.rect(surface,fill,rect,border_radius=6)
            pygame.draw.rect(surface,color if tech["id"]==self.selected_id else (37,67,91),
                             rect,2 if tech["id"]==self.selected_id else 1,border_radius=6)
            icon_size=max(16,int(28*self.zoom))
            try:
                tech_icon=scaled_sprite("icons",tech["id"]+".png",(icon_size,icon_size))
                surface.blit(tech_icon,(rect.x+5,rect.y+5))
            except (FileNotFoundError, pygame.error):
                theme.label(surface,tech["icon"],(rect.x+7,rect.y+6),icon_size,tech["branch_color"],True)
            max_chars=max(12,int(22*self.zoom))
            theme.label(surface,theme.fit_text(tech["name"],max_chars),
                        (rect.x+31,rect.y+8),max(8,int(10*self.zoom)),theme.TEXT,True)
            theme.label(surface,f"{tech['science_cost']} SCI",(rect.x+8,rect.y+rect.height-18),
                        max(7,int(9*self.zoom)),theme.MUTED)
            state=STATE_LABELS[tech["state"]]
            theme.label(surface,state,(rect.x+8,rect.y+rect.height-31),
                        max(6,int(7*self.zoom)),color,True)
        surface.set_clip(old_clip)
        # Detail card.
        pygame.draw.rect(surface,(9,22,39),self.detail_rect,border_radius=6)
        pygame.draw.rect(surface,theme.BORDER,self.detail_rect,1,border_radius=6)
        tech=self.manager.get(self.selected_id)
        dx,dy=self.detail_rect.x+12,self.detail_rect.y+12
        theme.label(surface,"ОБРАНА ТЕХНОЛОГІЯ",(dx,dy),9,theme.MUTED,True); dy+=22
        try:
            selected_icon=scaled_sprite("icons",tech["id"]+".png",(48,48))
            surface.blit(selected_icon,(dx,dy))
        except (FileNotFoundError, pygame.error):
            theme.label(surface,tech["icon"],(dx,dy),23,tech["branch_color"],True)
        dy+=54
        for line in self._wrap(tech["name"],29):
            theme.label(surface,line,(dx,dy),12,theme.TEXT,True); dy+=16
        dy+=7
        theme.label(surface,tech["branch"],(dx,dy),9,tech["branch_color"],True); dy+=21
        for line in self._wrap(tech["description"],34):
            theme.label(surface,line,(dx,dy),9,theme.MUTED); dy+=14
        dy+=9
        theme.label(surface,f"Вартість: {tech['science_cost']} науки",(dx,dy),9,theme.GOLD); dy+=17
        theme.label(surface,f"Час: {tech['research_time']:.0f} с",(dx,dy),9,theme.MUTED); dy+=17
        theme.label(surface,f"Стан: {STATE_LABELS[tech['state']]}",(dx,dy),9,
                    STATE_COLORS[tech["state"]],True); dy+=22
        theme.label(surface,"ПОПЕРЕДНІ ВИМОГИ",(dx,dy),8,theme.MUTED,True); dy+=15
        if tech["prerequisites"]:
            for req in tech["prerequisites"]:
                parent=self.manager.get(req)
                theme.label(surface,"• "+parent["name"],(dx,dy),8,
                            theme.GREEN if parent["state"]=="completed" else theme.MUTED); dy+=13
        else:
            theme.label(surface,"Немає",(dx,dy),8,theme.MUTED); dy+=13
        dy+=7
        theme.label(surface,"БОНУСИ",(dx,dy),8,theme.MUTED,True); dy+=15
        for key,value in tech["bonuses"].items():
            label=self._bonus_label(key,value)
            for line in self._wrap(label,34):
                theme.label(surface,line,(dx,dy),8,theme.GREEN); dy+=12
        self.research_rect=pygame.Rect(dx,self.detail_rect.bottom-39,self.detail_rect.width-24,27)
        enabled=tech["state"]=="available" and self.manager.active_research is None
        pygame.draw.rect(surface,(20,75,92) if enabled else (31,43,57),
                         self.research_rect,border_radius=4)
        button_text="ПОЧАТИ ДОСЛІДЖЕННЯ" if enabled else (
            "ДОСЛІДЖУЄТЬСЯ" if tech["state"]=="researching" else
            "ЗАВЕРШЕНО" if tech["state"]=="completed" else "ЗАБЛОКОВАНО")
        theme.label(surface,button_text,(self.research_rect.x+8,self.research_rect.y+8),9,
                    theme.TEXT if enabled else theme.MUTED,True)
        progress=self.manager.progress()
        if progress:
            p=self.manager.get(progress["technology_id"])
            bar=pygame.Rect(self.detail_rect.x+12,self.detail_rect.bottom-60,self.detail_rect.width-24,7)
            pygame.draw.rect(surface,(30,48,65),bar,border_radius=3)
            pygame.draw.rect(surface,theme.GOLD,(bar.x,bar.y,int(bar.width*progress["ratio"]),bar.height),border_radius=3)
            theme.label(surface,f"{p['name']}: {progress['ratio']*100:.0f}%",
                        (bar.x,bar.y-17),8,theme.GOLD)
        # Scroll indicators.
        bw,bh=self._bounds()
        theme.label(surface,"Колесо: вертикаль • Shift+колесо: горизонталь • Ctrl+колесо: масштаб",
                    (self.tree_rect.x+8,self.tree_rect.bottom-17),7,theme.MUTED)

    @staticmethod
    def _wrap(text,max_chars):
        words=str(text).split()
        lines=[]; line=""
        for word in words:
            candidate=(line+" "+word).strip()
            if len(candidate)>max_chars and line:
                lines.append(line); line=word
            else: line=candidate
        if line: lines.append(line)
        return lines

    @staticmethod
    def _bonus_label(key,value):
        labels={
          "energy_production_multiplier":"Виробництво енергії",
          "energy_capacity_multiplier":"Місткість енергії",
          "energy_consumption_multiplier":"Споживання енергії",
          "mining_rate_multiplier":"Швидкість видобутку",
          "mining_fuel_multiplier":"Паливо шахтарів",
          "construction_time_multiplier":"Час будівництва",
          "building_cost_multiplier":"Вартість споруд",
          "storage_capacity_multiplier":"Місткість складів",
          "ship_hull_multiplier":"Міцність корпусу",
          "maintenance_multiplier":"Вартість обслуговування",
          "ship_speed_multiplier":"Швидкість кораблів",
          "ship_fuel_multiplier":"Паливо флоту",
          "ship_cargo_multiplier":"Вантажомісткість флоту",
          "habitation_bonus_multiplier":"Житлові модулі",
          "colonization_bonus_multiplier":"Колонізаційні системи",
          "fleet_mission_speed_multiplier":"Швидкість місій",
          "research_speed_multiplier":"Швидкість досліджень",
          "combat_readiness":"Підготовка бойових систем"
        }
        if key.endswith("_multiplier"):
            delta=(float(value)-1)*100
            return f"{labels.get(key,key)}: {delta:+.0f}%"
        return f"{labels.get(key,key)}: {value}"
