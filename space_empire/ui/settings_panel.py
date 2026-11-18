"""In-game settings overlay for display and audio controls."""
import pygame
import json
import os
import sys
from pathlib import Path
from ui import theme
class SettingsPanel:
    def __init__(self,game,bottom):
        self.game,self.bottom=game,bottom
        self.visible=False
        self.rects={}
    def open(self): self.visible=True
    def close(self): self.visible=False
    def _persist(self, key, value):
        if getattr(sys,"frozen",False):
            path=Path(os.environ.get("APPDATA",Path.home()/"AppData"/"Roaming"))/"SpaceEmpire"/"settings.json"
        else:
            path=Path(__file__).resolve().parent.parent/"saves"/"settings.json"
        try: data=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,ValueError): data={}
        data[key]=value
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(".tmp")
        temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        temp.replace(path)
    def handle_event(self,event):
        if not self.visible: return False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            self.close(); return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for key,rect in self.rects.items():
                if rect.collidepoint(event.pos):
                    if key=="fullscreen":
                        self.game.toggle_fullscreen(); self._persist("fullscreen",self.game.is_fullscreen)
                    elif key=="music" and getattr(self.game,"audio_manager",None):
                        a=self.game.audio_manager; a.set_music(not a.music_enabled); self._persist("music",a.music_enabled)
                    elif key=="sound" and getattr(self.game,"audio_manager",None):
                        a=self.game.audio_manager; a.enabled=not a.enabled; self._persist("sound",a.enabled)
                    elif key=="save_exit":
                        self.game.safe_save(); self.game.running=False
                    elif key=="close": self.close()
                    return True
            return True
        return event.type in (pygame.MOUSEMOTION,pygame.MOUSEWHEEL)
    def draw(self,surface):
        if not self.visible: return
        w,h=surface.get_size()
        shade=pygame.Surface((w,h),pygame.SRCALPHA); shade.fill((1,5,15,190)); surface.blit(shade,(0,0))
        panel=pygame.Rect(max(18,w//2-240),max(80,h//2-205),min(480,w-36),410)
        theme.panel(surface,panel,fill=(7,17,32)); theme.label(surface,"НАЛАШТУВАННЯ",(panel.x+24,panel.y+22),22,theme.CYAN,True)
        audio=getattr(self.game,"audio_manager",None)
        rows=[
            ("fullscreen","Повноекранний режим: "+("УВІМК." if self.game.is_fullscreen else "ВИМК.")),
            ("music","Музика: "+("УВІМК." if audio and audio.music_enabled else "ВИМК.")),
            ("sound","Звукові ефекти: "+("УВІМК." if audio and audio.enabled else "ВИМК.")),
            ("save_exit","Зберегти та вийти"),
            ("close","Повернутися до гри"),
        ]
        self.rects={}
        for i,(key,label) in enumerate(rows):
            r=pygame.Rect(panel.x+24,panel.y+76+i*59,panel.width-48,46); self.rects[key]=r
            pygame.draw.rect(surface,(14,42,62),r,border_radius=6); pygame.draw.rect(surface,theme.BORDER_BRIGHT,r,1,border_radius=6)
            theme.label(surface,label,(r.x+13,r.y+13),14,theme.TEXT,True)
        theme.label(surface,"Esc — закрити це вікно",(panel.x+24,panel.bottom-27),10,theme.MUTED)
