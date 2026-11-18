"""Cached, richly shaded 2D planets and moons with animated atmospheric accents."""
from __future__ import annotations
import math
import random
import pygame
from graphics.asset_library import scaled_sprite


class CelestialBody:
    _sprite_cache = {}

    def __init__(self, x: float, y: float, radius: int,
                 base_color: tuple[int, int, int],
                 atmosphere_color: tuple[int, int, int] | None = None,
                 parallax: float = 0.82) -> None:
        self.position = pygame.Vector2(x, y)
        self.radius = radius
        self.base_color = base_color
        self.atmosphere_color = atmosphere_color
        self.parallax = parallax
        # Select the texture before draw() attempts to load it from the asset library.
        self._planet_asset = self._choose_planet_asset()
        self._sprite = self._get_sprite()

    def _choose_planet_asset(self):
        r, g, b = self.base_color
        if self.radius < 42:
            return "moon.png"
        if r > g * 1.18:
            return "desert.png"
        if b > r * 1.22:
            return "ice.png"
        if g > r * 1.15:
            return "temperate.png"
        return "lava.png"

    def _get_sprite(self):
        key = (self.radius, self.base_color, self.atmosphere_color)
        cached = self._sprite_cache.get(key)
        if cached is not None:
            return cached
        r = max(8, int(self.radius))
        pad = max(8, r // 5)
        size = (r + pad) * 2
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        rng = random.Random(hash(key) & 0xffffffff)
        # Atmospheric bloom is baked once; the thin rim is animated at draw time.
        if self.atmosphere_color:
            for ring in range(5, 0, -1):
                rr = r + pad * ring / 5
                alpha = 5 + (6-ring)*3
                pygame.draw.circle(sprite, (*self.atmosphere_color, alpha),
                                   (cx,cy), int(rr))
        pygame.draw.circle(sprite, self.base_color, (cx,cy), r)
        # Procedural continents / mineral bands clipped to the spherical silhouette.
        mask = pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
        mc = (r+1,r+1)
        for i in range(max(7,r//3)):
            ox=rng.randint(-r+2,r-2); oy=rng.randint(-r+2,r-2)
            rr=rng.randint(max(2,r//14),max(3,r//5))
            col=tuple(max(0,min(255,int(c*rng.uniform(.72,1.22)))) for c in self.base_color)
            pygame.draw.ellipse(mask,(*col, rng.randint(45,105)),
                                (mc[0]+ox-rr,mc[1]+oy-rr//2,rr*2,rr))
        # Cloud wisps and polar caps.
        for i in range(max(3,r//12)):
            yy=rng.randint(-r//2,r//2)
            pygame.draw.arc(mask,(210,225,238,35),
                pygame.Rect(1,r+yy-r//5,r*2,r//2),math.pi,math.tau,max(1,r//35))
        sphere=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
        pygame.draw.circle(sphere,(255,255,255,255),mc,r)
        mask.blit(sphere,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        sprite.blit(mask,(pad-1,pad-1))
        # Directional terminator and specular edge, both clipped by circle.
        shade=pygame.Surface(sphere.get_size(),pygame.SRCALPHA)
        for i in range(r):
            alpha=int(150*(i/r)**1.7)
            pygame.draw.line(shade,(3,8,20,alpha),(r+1+i,1),(r+1+i,r*2),1)
        shade.blit(sphere,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        sprite.blit(shade,(pad-1,pad-1))
        pygame.draw.arc(sprite,(205,231,255,180),
                        pygame.Rect(pad,pad,r*2,r*2),math.radians(205),
                        math.radians(305),max(1,r//28))
        # Small craters give rocky worlds a readable surface scale.
        for i in range(max(4,r//9)):
            ox=rng.randint(-r//2,r//2); oy=rng.randint(-r//2,r//2)
            cr=rng.randint(2,max(2,r//13))
            if ox*ox+oy*oy < (r-cr)**2:
                pygame.draw.circle(sprite,(15,22,36,55),(cx+ox,cy+oy),cr)
                pygame.draw.arc(sprite,(225,225,220,75),
                    pygame.Rect(cx+ox-cr,cy+oy-cr,cr*2,cr*2),
                    math.pi*.95,math.pi*1.8,1)
        self._sprite_cache[key]=sprite
        return sprite

    def draw(self, surface: pygame.Surface, camera, elapsed: float) -> None:
        px,py=camera.world_to_screen(self.position,surface.get_size(),self.parallax)
        radius=max(2,int(self.radius*camera.zoom))
        if px+radius<0 or py+radius<0 or px-radius>=surface.get_width() or py-radius>=surface.get_height():
            return
        zoom=max(.35,min(2.2,camera.zoom))
        target=(max(2,int((self.radius*2+44)*zoom)),
                max(2,int((self.radius*2+44)*zoom)))
        try:
            sprite=scaled_sprite("planets",self._planet_asset,target)
        except (FileNotFoundError, pygame.error):
            old_target=(max(2,int(self._sprite.get_width()*zoom)),
                        max(2,int(self._sprite.get_height()*zoom)))
            sprite=self._sprite if old_target==self._sprite.get_size() else pygame.transform.smoothscale(self._sprite,old_target)
        surface.blit(sprite,sprite.get_rect(center=(px,py)))
        # Time-based surface-band drift preserves the earlier axial animation cue.
        if radius >= 14:
            phase = (elapsed * 0.22 + self.position.x * 0.001) % math.tau
            band_y = py + int(math.sin(phase) * radius * 0.34)
            pygame.draw.arc(surface, tuple(min(255,int(c*1.18+12)) for c in self.base_color),
                            pygame.Rect(px-radius,band_y-radius//5,radius*2,max(2,radius//3)),
                            math.pi, math.tau, max(1,radius//28))
        if self.atmosphere_color:
            pulse=.75+.25*math.sin(elapsed*1.1+self.radius)
            rr=radius+max(2,int(4*zoom))
            pygame.draw.circle(surface,(*self.atmosphere_color,), (px,py),rr,
                               max(1,int((1+pulse)*zoom)))
            # Limb glint moves slowly to suggest rotation.
            angle=elapsed * 0.16+self.radius
            gx=px+int(math.cos(angle)*radius*.93)
            gy=py+int(math.sin(angle)*radius*.93)
            pygame.draw.circle(surface,(220,242,255),(gx,gy),max(1,int(2*zoom)))


class Planet(CelestialBody):
    """Textured procedural planet."""


class CelestialSystem:
    def __init__(self) -> None:
        self.objects = [
            Planet(-570,-260,118,(74,91,145),(88,135,210),.72),
            Planet(640,280,76,(151,91,73),(220,125,83),.88),
            Planet(350,-510,48,(78,139,135),(74,190,180),.78),
            Planet(-1050,390,35,(130,112,157),(151,115,205),.68),
        ]

    def add(self, body): self.objects.append(body)
    def remove(self, body): self.objects.remove(body)
    def draw(self,surface,camera,elapsed):
        for body in self.objects: body.draw(surface,camera,elapsed)
