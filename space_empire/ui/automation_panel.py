"""Interactive automation control panel."""
import pygame
from ui import theme

class AutomationPanel:
    PROCESS_LABELS=[
      ("auto_build","Автоматичне будівництво"),("auto_upgrade","Автопокращення споруд"),
      ("mining","Автокерування видобутком"),("transport","Автотранспортування"),
      ("fuel","Контроль паливного резерву"),("colonies","Автокерування колоніями"),
      ("trade","Автоматичні торговельні маршрути")]
    def __init__(self,manager,event_log):
        self.manager,self.log=manager,event_log;self.visible=False;self.rows={};self.priority_rects={};self.config_rects={}
    def open(self):self.visible=True
    def close(self):self.visible=False
    def handle_event(self,event):
        if not self.visible or event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1:return False
        for key,rect in self.rows.items():
            if rect.collidepoint(event.pos):
                cfg=self.manager.settings[key];self.manager.set_enabled(key,not cfg["enabled"])
                self.log.push(f"Автоматизація «{key}»: {'увімкнена' if cfg['enabled'] else 'вимкнена'}.")
                return True
        for key,rect in self.priority_rects.items():
            if rect.collidepoint(event.pos):
                priorities=self.manager.settings["production_priorities"]
                priorities[key]=priorities[key]%6+1
                return True
        for key,rect in self.config_rects.items():
            if rect.collidepoint(event.pos):
                if key=="fuel":
                    cfg=self.manager.settings["fuel"];cfg["reserve"]=50 if cfg["reserve"]>=200 else cfg["reserve"]+50
                elif key=="transport":
                    cfg=self.manager.settings["transport"];cfg["threshold"]=250 if cfg["threshold"]>=1000 else cfg["threshold"]+250
                elif key=="colonies":
                    cfg=self.manager.settings["colonies"];cfg["development_limit"]=1 if cfg["development_limit"]>=5 else cfg["development_limit"]+1
                elif key=="auto_build":
                    rules=self.manager.settings["auto_build"]["rules"]
                    rules[0]["below"]=100 if rules[0]["below"]>=400 else rules[0]["below"]+50
                elif key=="auto_upgrade":
                    cfg=self.manager.settings["auto_upgrade"];cfg["max_level"]=1 if cfg["max_level"]>=5 else cfg["max_level"]+1
                return True
        return False
    def draw(self,surface):
        if not self.visible:return
        w,h=surface.get_size();shade=pygame.Surface((w,h),pygame.SRCALPHA);shade.fill((3,8,18,235));surface.blit(shade,(0,0))
        panel=pygame.Rect(220,86,min(760,w-245),min(h-175,660));theme.panel(surface,panel,fill=(8,18,33))
        theme.label(surface,"ЦЕНТР АВТОМАТИЗАЦІЇ",(panel.x+18,panel.y+14),16,theme.CYAN,True)
        theme.label(surface,"Незалежні перемикачі процесів • правила перевіряються з урахуванням ресурсів і часу",
                    (panel.x+18,panel.y+39),10,theme.MUTED)
        self.rows={}
        y=panel.y+78
        for key,label in self.PROCESS_LABELS:
            cfg=self.manager.settings[key];r=pygame.Rect(panel.x+18,y,panel.width-36,42);self.rows[key]=r
            pygame.draw.rect(surface,(15,48,67) if cfg["enabled"] else (20,30,43),r,border_radius=5)
            pygame.draw.rect(surface,theme.BORDER_BRIGHT if cfg["enabled"] else theme.BORDER,r,1,border_radius=5)
            theme.label(surface,label,(r.x+12,r.y+12),12,theme.TEXT,True)
            theme.label(surface,"УВІМКНЕНО" if cfg["enabled"] else "ВИМКНЕНО",(r.right-105,r.y+13),10,
                        theme.GREEN if cfg["enabled"] else theme.MUTED,True)
            y+=48
        y+=8
        theme.label(surface,"ПРІОРИТЕТИ ВИРОБНИЦТВА — натисніть ресурс, щоб змінити ранг 1–6",
                    (panel.x+18,y),11,theme.CYAN,True);y+=25
        self.priority_rects={}
        for i,(key,priority) in enumerate(self.manager.settings["production_priorities"].items()):
            col=i%3;row=i//3
            r=pygame.Rect(panel.x+18+col*220,y+row*34,205,28);self.priority_rects[key]=r
            pygame.draw.rect(surface,theme.PANEL_ALT,r,border_radius=4)
            theme.label(surface,f"{key.upper()}   PRIORITY {priority}",(r.x+8,r.y+7),10,theme.TEXT)
        y+=80
        cfg=self.manager.settings
        theme.label(surface,"ПАРАМЕТРИ ПРАВИЛ — натисніть, щоб змінити значення",(panel.x+18,y),11,theme.CYAN,True);y+=24
        self.config_rects={}
        settings=[
            ("fuel",f"Паливний резерв: {cfg['fuel']['reserve']:.0f}"),
            ("transport",f"Поріг транспорту: {cfg['transport']['threshold']:.0f}"),
            ("colonies",f"Ліміт колонії: {cfg['colonies']['development_limit']}"),
            ("auto_build",f"Поріг енергії для будівництва: {cfg['auto_build']['rules'][0]['below']}"),
            ("auto_upgrade",f"Макс. рівень споруд: {cfg['auto_upgrade']['max_level']}")
        ]
        for i,(key,label) in enumerate(settings):
            col=i%2;row=i//2
            r=pygame.Rect(panel.x+18+col*350,y+row*32,330,27);self.config_rects[key]=r
            pygame.draw.rect(surface,theme.PANEL_ALT,r,border_radius=4)
            theme.label(surface,label,(r.x+8,r.y+7),9,theme.TEXT)
