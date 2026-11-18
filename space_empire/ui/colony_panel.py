"""Planetary colony management screen and procedural planet rendering."""
import math
import pygame
from ui import theme

class ColonyPanel:
    def __init__(self, manager, fleet, bottom):
        self.manager,self.fleet,self.bottom=manager,fleet,bottom
        self.visible=False; self.selected=None; self.scroll=0
        self.buttons={}

    def open(self):
        self.visible=True
        if self.selected not in self.manager.planets:self.selected=next(iter(self.manager.planets),None)
    def close(self): self.visible=False

    def handle_event(self,event):
        if not self.visible:return False
        if event.type==pygame.MOUSEWHEEL:
            self.scroll=max(0,self.scroll-event.y*28);return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for pid,rect in self.buttons.get("planets",{}).items():
                if rect.collidepoint(event.pos):self.selected=pid;return True
            for key,rect in self.buttons.items():
                if key=="planets":continue
                if rect.collidepoint(event.pos):
                    p=self.manager.planets.get(self.selected)
                    if key=="colonize":
                        ships=self.manager.available_colonizers()
                        ok,msg=self.manager.colonize(self.selected,ships[0].id if ships else None)
                    elif key=="base":ok,msg=self.manager.build_base(self.selected)
                    elif key=="develop":ok,msg=self.manager.develop(self.selected)
                    elif key.startswith("transport_"):
                        ships=[s for s in self.fleet.ships if s.ship_type=="transport" and s.status=="ready" and s.task=="idle"]
                        ok,msg=self.manager.transfer_to_station(self.selected,ships[0].id,key.split("_",1)[1],100) if ships else (False,"Потрібен вільний транспортний корабель.")
                    else:continue
                    self.bottom.push(msg);return True
        return False

    def _button(self,surface,key,label,rect,enabled=True):
        self.buttons[key]=rect
        pygame.draw.rect(surface,(17,53,77) if enabled else (25,34,47),rect,border_radius=5)
        pygame.draw.rect(surface,theme.BORDER_BRIGHT if enabled else theme.BORDER,rect,1,border_radius=5)
        theme.label(surface,label,(rect.x+10,rect.y+9),12,theme.CYAN if enabled else theme.MUTED,True)

    def _planet(self,surface,rect,p):
        spec=self.manager.types[p["type"]]; cx,cy=rect.center
        radius=min(rect.width,rect.height)//3
        atmosphere=tuple(spec["atmosphere"]); color=tuple(spec["color"])
        pygame.draw.circle(surface,atmosphere,(cx,cy),radius+13)
        pygame.draw.circle(surface,color,(cx,cy),radius)
        # Procedural bands, polar caps, craters and volcanic glow.
        for i in range(4):
            yy=cy-radius//2+i*radius//3
            pygame.draw.arc(surface,tuple(max(0,min(255,c+15)) for c in color),
                            pygame.Rect(cx-radius+5,yy-7,radius*2-10,14),0,math.pi,2)
        if p["type"]=="ice":
            pygame.draw.ellipse(surface,(220,242,250),(cx-radius//2,cy-radius//2,radius, radius//3))
        elif p["type"]=="forest":
            for dx,dy in [(-15,-8),(12,4),(0,18)]:
                pygame.draw.circle(surface,(35,105,65),(cx+dx,cy+dy),max(3,radius//7))
        elif p["type"]=="volcanic":
            pygame.draw.circle(surface,(255,172,70),(cx+radius//3,cy-radius//4),max(4,radius//8))
        elif p["type"]=="gas_giant":
            pygame.draw.ellipse(surface,(130,94,73),(cx-radius-8,cy-radius//3,cx*0+radius*2+16,radius//2),5)
        elif p["type"]=="desert":
            for dx,dy in [(-16,8),(14,-10)]:
                pygame.draw.circle(surface,(235,190,120),(cx+dx,cy+dy),max(3,radius//8))
        pygame.draw.circle(surface,theme.TEXT,(cx,cy),radius,1)

    def draw(self,surface):
        if not self.visible:return
        w,h=surface.get_size()
        overlay=pygame.Surface((w,h),pygame.SRCALPHA);overlay.fill((3,8,18,235));surface.blit(overlay,(0,0))
        theme.panel(surface,pygame.Rect(210,82,w-500,h-170),fill=(8,18,33))
        theme.label(surface,"PLANETARY COLONIES",(232,98),15,theme.CYAN,True)
        self.buttons={"planets":{}}
        left=pygame.Rect(225,130,260,h-235);theme.panel(surface,left,fill=theme.PANEL_ALT)
        self.manager.refresh_discoveries()
        visible=[p for p in self.manager.planets.values() if p["discovered"]]
        y=left.y+12-self.scroll
        for p in visible:
            r=pygame.Rect(left.x+8,y,left.width-16,40)
            self.buttons["planets"][p["id"]]=r
            if p["id"]==self.selected:pygame.draw.rect(surface,(17,53,77),r,border_radius=4)
            theme.label(surface,p["name"],(r.x+8,r.y+5),12,theme.TEXT,True)
            theme.label(surface,self.manager.types[p["type"]]["name"],(r.x+8,r.y+22),10,theme.MUTED)
            y+=44
        p=self.manager.planets.get(self.selected)
        if not p or not p["discovered"]:
            theme.label(surface,"Відкрийте планети через галактичну розвідку.",(520,180),15,theme.MUTED)
            return
        right=pygame.Rect(500,130,w-810,h-235);theme.panel(surface,right,fill=theme.PANEL_ALT)
        self._planet(surface,pygame.Rect(right.x+20,right.y+20,220,190),p)
        spec=self.manager.types[p["type"]]
        x=right.x+260; yy=right.y+18
        theme.label(surface,p["name"],(x,yy),20,theme.TEXT,True);yy+=34
        lines=[f"Тип: {spec['name']}",f"ID: {p['id']}",f"Система: {self.manager.galaxy.systems[p['system_id']]['name']}",
               f"Розмір: {p['size']:.2f}",f"Потенціал колонізації: {p['colonization_potential']*100:.1f}%",
               f"Населення: {p['population']:.0f}",f"Рівень розвитку: {p['development']}"]
        for line in lines:theme.label(surface,line,(x,yy),12,theme.MUTED);yy+=23
        theme.label(surface,"РЕСУРСНІ МОДИФІКАТОРИ",(right.x+22,right.bottom-95),11,theme.CYAN,True)
        theme.label(surface,"  ".join(f"{k}: ×{v:.2f}" for k,v in p["resource_characteristics"].items()),
                    (right.x+22,right.bottom-72),11,theme.TEXT)
        colony=self.manager.colonies.get(p["id"])
        bx=right.x+22; by=right.bottom-43
        if not colony:
            self._button(surface,"colonize","Відправити колонізатор",pygame.Rect(bx,by,190,32),bool(self.manager.available_colonizers()))
        elif not colony["base_built"]:
            self._button(surface,"base","Побудувати базу",pygame.Rect(bx,by,150,32),True)
        else:
            self._button(surface,"develop",f"Розвинути (рівень {colony['base_level']})",pygame.Rect(bx,by,190,32),True)
            self._button(surface,"transport_metal","Перевезти 100 металу",pygame.Rect(bx+200,by,175,32),any(s.ship_type=="transport" and s.status=="ready" and s.task=="idle" for s in self.fleet.ships))
            theme.label(surface,"ЛОКАЛЬНА ЕКОНОМІКА",(right.x+22,right.bottom-128),11,theme.CYAN,True)
            vals="  ".join(f"{k}: {v['amount']:.0f} (+{v['production']:.2f}/с)" for k,v in colony["economy"].items())
            theme.label(surface,vals,(right.x+22,right.bottom-110),10,theme.TEXT)
        theme.label(surface,f"Доступні колонізатори: {len(self.manager.available_colonizers())}",(232,h-83),11,theme.MUTED)
        theme.label(surface,"КОЛОНІЇ: незалежне виробництво та склад ресурсів",(520,h-83),11,theme.GREEN)
