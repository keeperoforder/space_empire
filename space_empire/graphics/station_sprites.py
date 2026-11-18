"""PNG-backed transparent sprite factory for modular station assembly.

The public factory API remains stable; high-resolution artwork is loaded from
assets/sprites/station and assets/sprites/buildings.
"""
import pygame
from graphics.asset_library import load_sprite, scaled_sprite


def _surface(size):
    return pygame.Surface(size, pygame.SRCALPHA)


def make_core():
    return scaled_sprite("station", "core.png", (380, 268))
    # Rear silhouette and layered armor.
    pygame.draw.rect(s, (20, 31, 49), (20, 25, 150, 82))
    pygame.draw.rect(s, (75, 94, 116), (27, 20, 136, 91))
    pygame.draw.rect(s, (35, 51, 72), (35, 13, 120, 105))
    pygame.draw.rect(s, (115, 133, 150), (48, 18, 94, 91))
    pygame.draw.rect(s, (54, 73, 96), (55, 10, 80, 105))
    # Command bridge housing.
    pygame.draw.rect(s, (26, 43, 64), (57, 2, 76, 48))
    pygame.draw.rect(s, (100, 124, 145), (63, 0, 64, 43))
    pygame.draw.rect(s, (34, 55, 80), (69, 5, 52, 32))
    pygame.draw.rect(s, (74, 183, 220), (73, 9, 44, 22))
    pygame.draw.rect(s, (175, 235, 255), (78, 11, 8, 3))
    # Blue illuminated bridge windows.
    for x in (42, 60, 132, 150):
        pygame.draw.rect(s, (12, 27, 43), (x, 57, 12, 22))
        pygame.draw.rect(s, (49, 160, 205), (x + 2, 59, 8, 17))
        pygame.draw.rect(s, (157, 229, 255), (x + 2, 60, 2, 5))
    # Hull plating, vents and warning marks.
    for x in (34, 154):
        pygame.draw.rect(s, (139, 154, 166), (x, 35, 5, 35))
        pygame.draw.rect(s, (18, 27, 41), (x + 1, 83, 4, 17))
    for x in range(62, 130, 12):
        pygame.draw.rect(s, (24, 36, 52), (x, 91, 7, 5))
        pygame.draw.rect(s, (173, 187, 194), (x, 89, 7, 2))
    pygame.draw.rect(s, (220, 164, 66), (25, 104, 18, 4))
    pygame.draw.rect(s, (220, 164, 66), (147, 104, 18, 4))
    # Hard pixel highlights.
    pygame.draw.line(s, (202, 218, 225), (50, 19), (139, 19), 2)
    pygame.draw.line(s, (145, 166, 184), (39, 112), (151, 112), 2)
    # Extra pixel-art surface detail: armor seams, rivets and status lamps.
    for x in (31, 46, 144, 159):
        pygame.draw.rect(s, (28, 43, 59), (x, 29, 5, 4))
        pygame.draw.rect(s, (184, 201, 211), (x + 1, 30, 2, 2))
    for x in range(58, 134, 12):
        pygame.draw.line(s, (105, 126, 145), (x, 75), (x + 6, 75), 1)
        pygame.draw.rect(s, (19, 32, 48), (x, 80, 7, 5))
    # Amber hazard chevrons on the lower service deck.
    for x in (48, 132):
        pygame.draw.line(s, (238, 178, 76), (x, 101), (x + 7, 106), 2)
        pygame.draw.line(s, (238, 178, 76), (x + 7, 106), (x + 14, 101), 2)
    # Cool reactor glow and paired docking indicators.
    pygame.draw.rect(s, (18, 57, 79), (72, 35, 46, 2))
    pygame.draw.rect(s, (102, 225, 250), (75, 36, 40, 2))
    for x in (18, 166):
        pygame.draw.circle(s, (27, 54, 73), (x, 83), 5)
        pygame.draw.circle(s, (80, 210, 237), (x, 83), 2)
    return s


def make_truss():
    s = _surface((520, 34))
    pygame.draw.rect(s, (24, 37, 53), (0, 10, 520, 15))
    pygame.draw.rect(s, (100, 121, 139), (0, 9, 520, 5))
    pygame.draw.rect(s, (48, 68, 88), (0, 19, 520, 5))
    for x in range(8, 520, 24):
        pygame.draw.line(s, (145, 163, 174), (x, 10), (x + 15, 23), 2)
        pygame.draw.line(s, (57, 81, 103), (x + 15, 23), (x + 24, 10), 2)
        pygame.draw.rect(s, (189, 203, 208), (x, 7, 4, 4))
    return s


def make_solar_panel():
    return scaled_sprite("station", "solar_panel.png", (300, 200))
    # Support arm.
    pygame.draw.rect(s, (107, 127, 145), (69, 43, 12, 55))
    pygame.draw.rect(s, (35, 53, 73), (72, 45, 6, 53))
    # Panel frame and individual photovoltaic cells.
    pygame.draw.rect(s, (156, 174, 183), (4, 3, 142, 70), 3)
    pygame.draw.rect(s, (15, 39, 72), (8, 7, 134, 62))
    for x in range(12, 143, 18):
        pygame.draw.rect(s, (31, 87, 139), (x, 10, 14, 56))
        pygame.draw.line(s, (79, 153, 202), (x + 2, 12), (x + 2, 63), 1)
    for y in (26, 46):
        pygame.draw.line(s, (119, 183, 216), (8, y), (142, y), 1)
    pygame.draw.rect(s, (193, 215, 221), (4, 3, 142, 3))
    return s


def make_docking_bay():
    return scaled_sprite("station", "docking_bay.png", (248, 180))
    pygame.draw.rect(s, (22, 35, 52), (12, 9, 100, 69))
    pygame.draw.rect(s, (94, 113, 132), (19, 4, 86, 68))
    pygame.draw.rect(s, (36, 54, 75), (27, 10, 70, 55))
    pygame.draw.rect(s, (12, 23, 38), (39, 19, 46, 42))
    pygame.draw.rect(s, (55, 119, 151), (44, 23, 36, 34), 3)
    pygame.draw.rect(s, (14, 31, 48), (51, 30, 22, 21))
    pygame.draw.rect(s, (83, 197, 226), (55, 33, 14, 15))
    pygame.draw.rect(s, (194, 214, 218), (20, 68, 84, 5))
    for x in (25, 94):
        pygame.draw.rect(s, (224, 169, 71), (x, 56, 6, 8))
    return s


def make_antenna():
    return scaled_sprite("station", "antenna.png", (152, 232))
    pygame.draw.rect(s, (78, 99, 117), (35, 48, 6, 66))
    pygame.draw.rect(s, (143, 160, 169), (31, 44, 14, 6))
    # Dish and feed arm.
    pygame.draw.arc(s, (170, 190, 202), pygame.Rect(5, 3, 62, 57),
                    0.35, 2.8, 4)
    pygame.draw.line(s, (125, 149, 166), (14, 22), (52, 50), 3)
    pygame.draw.circle(s, (77, 187, 224), (15, 22), 4)
    pygame.draw.circle(s, (199, 242, 255), (15, 22), 2)
    pygame.draw.rect(s, (221, 171, 76), (29, 67, 18, 4))
    return s


def make_engine():
    return scaled_sprite("station", "engine.png", (144, 128))
    pygame.draw.rect(s, (29, 43, 61), (5, 8, 62, 48))
    pygame.draw.rect(s, (104, 124, 143), (10, 4, 52, 40))
    pygame.draw.rect(s, (30, 48, 69), (16, 9, 40, 34))
    pygame.draw.rect(s, (13, 24, 39), (21, 15, 30, 25))
    pygame.draw.rect(s, (62, 164, 206), (25, 18, 22, 18))
    pygame.draw.rect(s, (177, 238, 255), (30, 20, 12, 13))
    pygame.draw.rect(s, (153, 171, 180), (3, 43, 66, 7))
    return s


def make_radiator():
    return scaled_sprite("station", "radiator.png", (144, 124))
    pygame.draw.rect(s, (73, 91, 108), (30, 4, 12, 54))
    pygame.draw.rect(s, (24, 42, 59), (5, 9, 62, 44))
    for y in range(13, 52, 7):
        pygame.draw.rect(s, (118, 143, 157), (8, y, 56, 3))
        pygame.draw.line(s, (40, 70, 91), (8, y + 3), (64, y + 3), 1)
    return s


def make_building_sprite(kind):
    """Create a distinct pixel-art module sprite for a constructed building."""
    asset_names = {"solar": "solar", "smelter": "smelter", "crystal": "crystal",
                   "fuel": "fuel", "hangar": "hangar", "lab": "lab",
                   "warehouse": "warehouse", "habitat": "habitat", "defense": "defense"}
    if kind in asset_names:
        return scaled_sprite("buildings", asset_names[kind] + ".png", (264, 206))
    palettes = {
        "solar": ((20, 54, 88), (66, 170, 224), (174, 226, 245)),
        "smelter": ((65, 53, 43), (205, 123, 61), (255, 197, 112)),
        "crystal": ((39, 62, 82), (74, 195, 224), (191, 250, 255)),
        "fuel": ((62, 47, 76), (172, 115, 222), (226, 193, 255)),
        "hangar": ((38, 54, 70), (116, 153, 177), (191, 219, 231)),
        "lab": ((37, 57, 79), (86, 169, 213), (186, 231, 255)),
        "warehouse": ((57, 67, 78), (135, 157, 170), (211, 223, 226)),
        "habitat": ((43, 67, 65), (90, 174, 143), (185, 239, 208)),
        "defense": ((67, 45, 52), (199, 87, 91), (255, 178, 151)),
    }
    dark, main, light = palettes.get(kind, palettes["hangar"])
    s = _surface((132, 104))
    # Common docking collar and reinforced hull.
    pygame.draw.rect(s, (18, 29, 43), (8, 30, 116, 64))
    pygame.draw.rect(s, (82, 104, 121), (13, 25, 106, 63))
    pygame.draw.rect(s, dark, (19, 31, 94, 48))
    pygame.draw.rect(s, main, (25, 36, 82, 37))
    pygame.draw.rect(s, light, (29, 36, 74, 4))
    pygame.draw.rect(s, (24, 38, 53), (36, 48, 60, 20))
    if kind == "solar":
        for x in range(4, 128, 12):
            pygame.draw.rect(s, dark, (x, 5, 9, 22))
            pygame.draw.line(s, light, (x+2, 7), (x+2, 24), 1)
        pygame.draw.rect(s, light, (62, 27, 8, 14))
    elif kind == "smelter":
        for x in (39, 72, 96):
            pygame.draw.rect(s, (35, 40, 49), (x, 13, 12, 24))
            pygame.draw.rect(s, main, (x+3, 7, 6, 8))
        pygame.draw.polygon(s, light, [(53, 52), (66, 37), (79, 52), (66, 65)])
    elif kind == "crystal":
        pygame.draw.polygon(s, light, [(65, 7), (80, 31), (70, 51), (53, 31)])
        pygame.draw.polygon(s, main, [(65, 14), (73, 31), (67, 43), (59, 30)])
        pygame.draw.line(s, light, (65, 15), (65, 42), 2)
    elif kind == "fuel":
        for x in (40, 65, 90):
            pygame.draw.rect(s, dark, (x, 7, 17, 42), border_radius=4)
            pygame.draw.rect(s, light, (x+4, 13, 9, 24), border_radius=3)
            pygame.draw.rect(s, main, (x+2, 3, 13, 5))
    elif kind == "hangar":
        pygame.draw.rect(s, (13, 25, 40), (37, 37, 58, 38))
        pygame.draw.rect(s, light, (42, 42, 48, 28), 2)
        pygame.draw.polygon(s, main, [(66, 46), (78, 64), (54, 64)])
    elif kind == "lab":
        pygame.draw.rect(s, light, (54, 7, 25, 23), 2)
        pygame.draw.line(s, light, (66, 9), (66, 27), 2)
        pygame.draw.circle(s, main, (66, 18), 6)
        pygame.draw.rect(s, (12, 27, 42), (47, 49, 39, 16))
    elif kind == "warehouse":
        for x in (34, 55, 76, 97):
            pygame.draw.rect(s, light, (x, 43, 15, 24), 2)
            pygame.draw.line(s, light, (x+2, 49), (x+13, 49), 1)
    elif kind == "habitat":
        for x in (34, 58, 82):
            pygame.draw.rect(s, dark, (x, 8, 18, 30))
            pygame.draw.rect(s, light, (x+3, 12, 12, 10))
            pygame.draw.rect(s, main, (x+3, 25, 12, 8))
    elif kind == "defense":
        pygame.draw.rect(s, dark, (57, 7, 18, 32))
        pygame.draw.rect(s, light, (63, 0, 6, 18))
        pygame.draw.line(s, light, (66, 12), (39, 2), 4)
        pygame.draw.line(s, light, (66, 12), (93, 2), 4)
        pygame.draw.circle(s, main, (66, 20), 8)
    # Docking pylons, windows and status lamps.
    pygame.draw.rect(s, (155, 174, 184), (5, 72, 122, 5))
    for x in (31, 51, 81, 101):
        pygame.draw.rect(s, light, (x, 57, 7, 5))
    pygame.draw.rect(s, (83, 221, 177), (111, 32, 5, 5))
    return s
