"""Compact multi-line HUD tooltip."""
import pygame
from ui import theme


class Tooltip:
    def __init__(self):
        self.text = None
        self.position = (0, 0)

    def set(self, text, position):
        self.text = text
        self.position = position

    def draw(self, surface):
        if not self.text:
            return
        font = theme.font(12)
        max_width = min(560, surface.get_width() - 32)
        words = str(self.text).replace(" | ", "\\n").splitlines()
        lines = []
        for segment in words:
            current = ""
            for word in segment.split():
                candidate = f"{current} {word}".strip()
                if current and font.size(candidate)[0] > max_width - 20:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                lines.append(current)
        rendered = [font.render(line, True, theme.TEXT) for line in lines]
        width = min(max_width, max((line.get_width() for line in rendered), default=0)) + 20
        height = sum(line.get_height() for line in rendered) + 14
        x = min(self.position[0] + 16, surface.get_width() - width - 8)
        y = min(self.position[1] + 18, surface.get_height() - height - 8)
        rect = pygame.Rect(max(8, x), max(8, y), width, height)
        theme.panel(surface, rect, fill=(8, 19, 34), border=theme.CYAN_DIM, radius=5)
        cursor_y = rect.y + 7
        for line in rendered:
            surface.blit(line, (rect.x + 10, cursor_y))
            cursor_y += line.get_height()
