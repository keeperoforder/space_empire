"""Player market and interplanetary route configuration."""
import pygame
from ui import theme

class TradePanel:
    RESOURCES=("metal","energy","crystals","fuel","credits","science")
    def __init__(self,manager,colonies,fleet,event_log):
        self.manager,self.colonies,self.fleet,self.log=manager,colonies,fleet,event_log
        self.visible=False;self.resource_index=0;self.quantity=100.0;self.source_index=0;self.dest_index=1;self.ship_index=0
        self.buttons={}
    def open(self):self.visible=True
    def close(self):self.visible=False
    def _options(self):
        planets=[p for p in self.colonies.planets.values() if p["id"] in self.colonies.colonies]
        ships=[s for s in self.fleet.ships if s.ship_type=="transport"]
        return planets,ships
    def _act(self,key):
        planets,ships=self._options();resource=self.RESOURCES[self.resource_index]
        if key=="buy":ok,msg=self.manager.buy(resource,self.quantity)
        elif key=="sell":ok,msg=self.manager.sell(resource,self.quantity)
        elif key=="resource":self.resource_index=(self.resource_index+1)%len(self.RESOURCES);return
        elif key=="source" and planets:self.source_index=(self.source_index+1)%len(planets);return
        elif key=="dest" and planets:self.dest_index=(self.dest_index+1)%len(planets);return
        elif key=="ship" and ships:self.ship_index=(self.ship_index+1)%len(ships);return
        elif key=="quantity":self.quantity=100 if self.quantity>=500 else self.quantity+100;return
        elif key=="create":
            if len(planets)<2 or not ships:ok,msg=False,"Потрібні дві колонії та транспортний корабель."
            else:
                a=planets[self.source_index%len(planets)];b=planets[self.dest_index%len(planets)]
                ship=ships[self.ship_index%len(ships)]
                ok,msg=self.manager.create_route(a["id"],b["id"],resource,self.quantity,ship.id,interval=180)
        elif key.startswith("toggle_route:"):
            route_id=key.split(":",1)[1]
            route=next((r for r in self.manager.routes if r["id"]==route_id),None)
            if route:ok,msg=self.manager.toggle_route(route_id,not route["enabled"])
            else:return
        elif key.startswith("remove_route:"):
            route_id=key.split(":",1)[1]
            ok,msg=self.manager.remove_route(route_id)
        else:return
        self.log.push(msg,theme.GREEN if ok else theme.RED)
    def handle_event(self,event):
        if not self.visible or event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1:return False
        for key,rect in self.buttons.items():
            if rect.collidepoint(event.pos):self._act(key);return True
        return False
    def _button(self,surface,key,label,rect):
        self.buttons[key]=rect;pygame.draw.rect(surface,(16,49,69),rect,border_radius=4)
        pygame.draw.rect(surface,theme.BORDER_BRIGHT,rect,1,border_radius=4)
        theme.label(surface,label,(rect.x+8,rect.y+8),10,theme.TEXT,True)
    def draw(self,surface):
        if not self.visible:return
        w,h=surface.get_size();shade=pygame.Surface((w,h),pygame.SRCALPHA);shade.fill((3,8,18,235));surface.blit(shade,(0,0))
        panel=pygame.Rect(220,86,min(790,w-245),min(h-175,650));theme.panel(surface,panel,fill=(8,18,33))
        theme.label(surface,"ТОРГОВЕЛЬНИЙ ЦЕНТР",(panel.x+18,panel.y+14),16,theme.CYAN,True)
        theme.label(surface,"Ринок станції та автоматичні міжпланетні маршрути",(panel.x+18,panel.y+38),10,theme.MUTED)
        self.buttons={}
        y=panel.y+76
        theme.label(surface,"СТАНЦІЙНИЙ РИНОК",(panel.x+18,y),12,theme.CYAN,True);y+=28
        resource=self.RESOURCES[self.resource_index]
        self._button(surface,"resource",f"Ресурс: {resource}",pygame.Rect(panel.x+18,y,180,32))
        self._button(surface,"quantity",f"Кількість: {self.quantity:g}",pygame.Rect(panel.x+210,y,150,32))
        self._button(surface,"buy","Купити",pygame.Rect(panel.x+370,y,105,32))
        self._button(surface,"sell","Продати",pygame.Rect(panel.x+485,y,105,32))
        theme.label(surface,f"Ціна купівлі: {self.manager.prices[resource]:g} кр. / од.  •  ціна продажу: {self.manager.prices[resource]*.82:g} кр. / од.",
                    (panel.x+18,y+42),10,theme.MUTED)
        y+=82
        theme.label(surface,"МІЖПЛАНЕТНИЙ МАРШРУТ",(panel.x+18,y),12,theme.CYAN,True);y+=27
        planets,ships=self._options()
        if planets:
            a=planets[self.source_index%len(planets)];b=planets[self.dest_index%len(planets)]
            self._button(surface,"source",f"Звідки: {a['name']}",pygame.Rect(panel.x+18,y,220,32))
            self._button(surface,"dest",f"Куди: {b['name']}",pygame.Rect(panel.x+250,y,220,32))
        else:
            theme.label(surface,"Спочатку заснуйте щонайменше дві колонії.",(panel.x+18,y),11,theme.MUTED)
        y+=40
        if ships:self._button(surface,"ship",f"Корабель: {ships[self.ship_index%len(ships)].name}",pygame.Rect(panel.x+18,y,220,32))
        else:theme.label(surface,"Немає транспортних кораблів.",(panel.x+18,y),10,theme.MUTED)
        self._button(surface,"create","Створити маршрут",pygame.Rect(panel.x+250,y,170,32))
        y+=52
        theme.label(surface,"АКТИВНІ МАРШРУТИ",(panel.x+18,y),12,theme.CYAN,True);y+=25
        for route in self.manager.routes[:7]:
            a=self.colonies.colonies.get(route["source"],{}).get("name",route["source"])
            b=self.colonies.colonies.get(route["destination"],{}).get("name",route["destination"])
            state="В дорозі" if route["in_flight"] else ("Активний" if route["enabled"] else "Вимкнений")
            theme.label(surface,f"{route['id']}  {a} → {b}  {route['quantity']:g} {route['resource']}  •  {state}",
                        (panel.x+20,y+7),9,theme.TEXT)
            self._button(surface,"toggle_route:"+route["id"],"ON / OFF",
                         pygame.Rect(panel.right-190,y,78,24))
            self._button(surface,"remove_route:"+route["id"],"Видалити",
                         pygame.Rect(panel.right-104,y,86,24))
            y+=28
        theme.label(surface,"Маршрути враховують вантажомісткість, склад призначення, паливо та готовність корабля.",
                    (panel.x+18,panel.bottom-30),9,theme.MUTED)
