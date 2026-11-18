"""Bottom event feed and notification strip."""
import pygame
from ui import theme

class BottomBar:
    HEIGHT = 78

    def __init__(self):
        self.messages = [
            ("13:42", "Станція Atlas-01 працює у штатному режимі.", theme.GREEN),
            ("13:39", "Сканування сектору завершено.", theme.CYAN),
            ("13:31", "Енергетичні резерви стабільні.", theme.GOLD),
        ]

    def push(self, message, color=None):
        self.messages.insert(0, ("NOW", message, color or theme.CYAN))
        self.messages = self.messages[:5]

    def draw(self, surface):
        w, h = surface.get_size()
        rect = pygame.Rect(12, h - self.HEIGHT - 10, w - 24, self.HEIGHT)
        theme.panel(surface, rect, fill=(7, 17, 32), border=theme.BORDER_BRIGHT)
        theme.label(surface, "EVENT LOG", (rect.x + 15, rect.y + 9), 9, theme.MUTED, True)
        pygame.draw.line(surface, theme.BORDER, (rect.x + 14, rect.y + 27),
                         (rect.right - 14, rect.y + 27), 1)
        available = max(1, (w - 80) // 3)
        for i, (stamp, message, color) in enumerate(self.messages[:3]):
            x = rect.x + 15 + i * available
            if i:
                pygame.draw.line(surface, (24, 49, 70), (x - 10, rect.y + 36),
                                 (x - 10, rect.bottom - 10), 1)
            pygame.draw.circle(surface, color, (x + 4, rect.y + 49), 3)
            theme.label(surface, stamp, (x + 14, rect.y + 42), 9, color, True)
            theme.label(surface, theme.fit_text(message, max(16, available // 9)),
                        (x + 62, rect.y + 41), 10, theme.TEXT)
