"""Shared visual language and layout constants for the Space Empire HUD."""
import pygame

BG = (5, 10, 22)
PANEL = (8, 18, 34)
PANEL_ALT = (12, 27, 47)
PANEL_HOVER = (20, 45, 70)
BORDER = (39, 88, 121)
BORDER_BRIGHT = (63, 180, 224)
CYAN = (75, 218, 250)
CYAN_DIM = (42, 123, 161)
TEXT = (218, 234, 247)
MUTED = (158, 184, 205)
GREEN = (89, 222, 164)
GOLD = (244, 190, 91)
RED = (245, 105, 113)
PURPLE = (177, 145, 255)

def panel(surface, rect, fill=PANEL, border=BORDER, radius=8, width=1):
    """Unified layered console panel used by every game window."""
    shadow = rect.move(0, 3)
    pygame.draw.rect(surface, (2, 6, 14), shadow, border_radius=radius + 2)
    pygame.draw.rect(surface, (10, 25, 42), rect.inflate(2, 2),
                     border_radius=radius + 1)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)
    if rect.width > 28 and rect.height > 28:
        # Restrained top rail and corner markers unify the visual language.
        pygame.draw.line(surface, (29, 65, 91),
                         (rect.x + 12, rect.y + 2),
                         (rect.right - 12, rect.y + 2), 1)
        pygame.draw.line(surface, CYAN_DIM,
                         (rect.x + 10, rect.y + 1),
                         (rect.x + min(72, rect.width // 3), rect.y + 1), 2)
        corner = min(9, rect.width // 8, rect.height // 8)
        for cx, cy, sx, sy in (
            (rect.left + 2, rect.top + 2, 1, 1),
            (rect.right - 3, rect.top + 2, -1, 1),
            (rect.left + 2, rect.bottom - 3, 1, -1),
            (rect.right - 3, rect.bottom - 3, -1, -1),
        ):
            pygame.draw.line(surface, (75, 145, 177), (cx, cy),
                             (cx + sx * corner, cy), 1)
            pygame.draw.line(surface, (75, 145, 177), (cx, cy),
                             (cx, cy + sy * corner), 1)


def section_header(surface, title, subtitle, rect, accent=CYAN):
    """Consistent title block for modal panels and management screens."""
    x, y = rect.topleft
    pygame.draw.rect(surface, (12, 34, 53),
                     pygame.Rect(x, y, rect.width, 42), border_radius=6)
    pygame.draw.rect(surface, accent,
                     pygame.Rect(x, y + 3, 3, 30), border_radius=1)
    label(surface, title, (x + 14, y + 5), 17, TEXT, True)
    if subtitle:
        label(surface, subtitle, (x + 15, y + 25), 9, MUTED)


def action_button(surface, rect, text, state="normal", accent=CYAN, font_size=11):
    """Shared button painter; state: normal, hover, disabled, danger, success."""
    palette = {
        "normal": ((14, 43, 64), accent, TEXT),
        "hover": ((22, 65, 91), (125, 225, 255), (245, 252, 255)),
        "disabled": ((24, 34, 47), BORDER, MUTED),
        "danger": ((65, 28, 39), RED, TEXT),
        "success": ((15, 61, 53), GREEN, TEXT),
    }
    fill, edge, ink = palette.get(state, palette["normal"])
    pygame.draw.rect(surface, (3, 8, 17), rect.move(0, 2), border_radius=5)
    pygame.draw.rect(surface, fill, rect, border_radius=5)
    pygame.draw.rect(surface, edge, rect, 1, border_radius=5)
    label(surface, text, (rect.x + 10, rect.y + max(4, (rect.height-font_size)//2)),
          font_size, ink, True)


def info_card(surface, rect, title, value, accent=CYAN, detail=None):
    """Compact reusable metric card."""
    panel(surface, rect, fill=PANEL_ALT, border=BORDER, radius=6)
    label(surface, title, (rect.x + 9, rect.y + 7), 9, MUTED, True)
    label(surface, value, (rect.x + 9, rect.y + 23), 15, accent, True)
    if detail:
        label(surface, detail, (rect.x + 9, rect.bottom - 17), 8, MUTED)


def resource_glyph(surface, center, color, kind, radius=11):
    """Small crisp vector glyphs used by the resource strip."""
    x, y = center
    pygame.draw.circle(surface, (12, 31, 49), (x, y), radius + 3)
    pygame.draw.circle(surface, color, (x, y), radius, 1)
    if kind == "metal":
        pygame.draw.line(surface, color, (x-5, y-4), (x+4, y-4), 2)
        pygame.draw.line(surface, color, (x-5, y), (x+5, y), 2)
        pygame.draw.line(surface, color, (x-3, y+4), (x+4, y+4), 2)
    elif kind == "energy":
        pygame.draw.polygon(surface, color, [(x+1,y-8),(x-5,y+1),(x-1,y+1),(x-3,y+8),(x+6,y-3),(x+2,y-3)])
    elif kind == "crystals":
        pygame.draw.polygon(surface, color, [(x,y-8),(x+6,y-1),(x+3,y+7),(x-4,y+6),(x-7,y-1)], 2)
        pygame.draw.line(surface, color, (x,y-7), (x,y+6), 1)
    elif kind == "fuel":
        pygame.draw.polygon(surface, color, [(x,y-8),(x+5,y),(x+4,y+5),(x,y+8),(x-4,y+5),(x-5,y)])
        pygame.draw.line(surface, color, (x,y-3), (x+2,y+2), 2)
    elif kind == "credits":
        pygame.draw.circle(surface, color, (x,y), 6, 2)
        pygame.draw.line(surface, color, (x-3,y), (x+3,y), 1)
        pygame.draw.line(surface, color, (x,y-4), (x,y+4), 1)
    elif kind == "science":
        pygame.draw.circle(surface, color, (x,y), 2)
        pygame.draw.ellipse(surface, color, (x-8,y-3,16,6), 1)
        pygame.draw.ellipse(surface, color, (x-3,y-8,6,16), 1)

def font(size, bold=False):
    return pygame.font.SysFont("segoeui", max(10, int(size)), bold=bold)

def label(surface, text, pos, size=15, color=TEXT, bold=False):
    surface.blit(font(size, bold).render(str(text), True, color), pos)

def fit_text(text, max_chars):
    text = str(text)
    return text if len(text) <= max_chars else text[:max(1, max_chars - 1)] + "…"
