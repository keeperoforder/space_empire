"""Modal report displayed after applying offline progression."""
import pygame

class OfflineReport:
    def __init__(self, report):
        self.report = report
        self.visible = bool(report and report.get("real_elapsed_seconds", 0) > 0)
        self.close_rect = pygame.Rect(0, 0, 112, 36)

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.visible = False
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect.collidepoint(event.pos):
                self.visible = False
            return True
        return event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP)

    def draw(self, surface):
        if not self.visible:
            return
        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((2, 5, 15, 205))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(0, 0, min(650, w-40), min(560, h-40))
        panel.center = (w//2, h//2)
        pygame.draw.rect(surface, (12, 22, 42), panel, border_radius=12)
        pygame.draw.rect(surface, (55, 150, 205), panel, 2, border_radius=12)
        title_font = pygame.font.SysFont("consolas", 28, bold=True)
        font = pygame.font.SysFont("consolas", 18)
        small = pygame.font.SysFont("consolas", 14)
        def label(text, x, y, color=(220, 235, 248), f=font):
            surface.blit(f.render(text, True, color), (x, y))
        x, y = panel.x+28, panel.y+24
        label("OFFLINE REPORT", x, y, (100, 210, 255), title_font)
        elapsed = int(self.report.get("elapsed_seconds", 0))
        label(f"Час відсутності: {elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}", x, y+48)
        if self.report.get("capped"):
            label("Застосовано ліміт офлайн-прогресу: 8 годин", x, y+76, (255, 190, 105), small)
        label("ЗМІНА РЕСУРСІВ", x, y+116, (100, 210, 255), small)
        names = {"metal":"Метал", "energy":"Енергія", "crystals":"Кристали", "fuel":"Паливо", "credits":"Кредити", "science":"Наука"}
        for i, (key, value) in enumerate(self.report.get("resources", {}).items()):
            yy = y+146+i*34
            color = (115, 225, 170) if value >= 0 else (255, 130, 130)
            label(names.get(key, key), x, yy)
            label(f"{value:+,.1f}", panel.right-170, yy, color)
        events = self.report.get("events", [])
        label("ПОДІЇ", x, y+365, (100, 210, 255), small)
        for i, event in enumerate(events[:3]):
            label(str(event)[:68], x, y+390+i*22, (170, 190, 210), small)
        self.close_rect = pygame.Rect(panel.right-140, panel.bottom-58, 112, 36)
        pygame.draw.rect(surface, (30, 105, 150), self.close_rect, border_radius=6)
        pygame.draw.rect(surface, (90, 190, 235), self.close_rect, 1, border_radius=6)
        text = small.render("ПРОДОВЖИТИ", True, (240, 248, 255))
        surface.blit(text, text.get_rect(center=self.close_rect.center))
