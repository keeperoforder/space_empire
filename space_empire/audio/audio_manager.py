"""Optional procedural game audio; safely degrades when no audio device exists."""
from pathlib import Path
import pygame

class AudioManager:
    def __init__(self, asset_root=None):
        self.root=Path(asset_root) if asset_root else Path(__file__).resolve().parent.parent/"assets"/"audio"
        self.enabled=True
        self.music_enabled=True
        self.volume=0.35
        self.ready=False
        self.click=None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.click=pygame.mixer.Sound(str(self.root/"ui_click.wav"))
            self.click.set_volume(self.volume)
            pygame.mixer.music.load(str(self.root/"ambient_loop.wav"))
            pygame.mixer.music.set_volume(self.volume*0.45)
            pygame.mixer.music.play(-1)
            self.ready=True
        except (pygame.error, OSError):
            self.ready=False
    def play_click(self):
        if self.ready and self.enabled and self.click:
            try: self.click.play()
            except pygame.error: pass
    def set_volume(self,value):
        self.volume=max(0.0,min(1.0,float(value)))
        if self.ready:
            self.click.set_volume(self.volume)
            pygame.mixer.music.set_volume(self.volume*0.45)
    def set_music(self,enabled):
        self.music_enabled=bool(enabled)
        if not self.ready: return
        try:
            if self.music_enabled and not pygame.mixer.music.get_busy(): pygame.mixer.music.play(-1)
            elif not self.music_enabled: pygame.mixer.music.stop()
        except pygame.error: pass
    def close(self):
        if self.ready:
            try: pygame.mixer.music.stop()
            except pygame.error: pass
