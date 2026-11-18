"""PNG-backed fleet rendering with cached sprites and animated engine overlays."""
import math
import pygame
from graphics.asset_library import scaled_sprite


class FleetVisuals:
    def __init__(self, manager):
        self.manager = manager
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt

    def draw(self, surface, camera):
        for ship in self.manager.ships:
            if ship.ship_type == "miner":
                continue
            x, y = camera.world_to_screen((ship.x, ship.y), surface.get_size())
            scale = max(0.48, min(1.5, camera.zoom))
            pulse = 0.7 + 0.3 * math.sin(self.elapsed * 5 + len(ship.id))
            sprite = scaled_sprite("ships", ship.ship_type + ".png",
                                   (max(12, int(92*scale)), max(8, int(46*scale))))
            surface.blit(sprite, sprite.get_rect(center=(x, y)))
            # Small animated reactor bloom and engine plume exhaust trail.
            ex = x - int(34*scale)
            engine_radius = max(2, int((4 + pulse*3)*scale))
            radius = engine_radius
            pygame.draw.circle(surface, (24, 95, 150), (ex, y), radius+2)
            pygame.draw.circle(surface, (95, 218, 255), (ex, y), radius)
            if ship.status in ("outbound", "returning"):
                tail = int((18 + pulse*9)*scale)
                pygame.draw.line(surface, (35,112,174), (ex,y),
                                 (ex-tail,y), max(2,int(4*scale)))
                pygame.draw.line(surface, (155,230,255), (ex,y),
                                 (ex-tail//2,y), max(1,int(2*scale)))
