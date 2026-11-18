"""Cached rocky asteroid sprites and animated mining effects.
    Mineral seams and crater arcs are baked into the transparent PNG variants.
    """
import math, random
import pygame
from graphics.asset_library import scaled_sprite


class MiningVisuals:
    def __init__(self, mining_manager):
        self.manager=mining_manager
        self.elapsed=0.0
        self.asteroid_surfaces={}

    def update(self,dt): self.elapsed+=dt

    def _asteroid_sprite(self, radius, richness):
        key=(radius,int(richness))
        if key in self.asteroid_surfaces: return self.asteroid_surfaces[key]
        rng=random.Random(radius*7919+int(richness)*101)
        pad=max(5,radius//3); size=(radius+pad)*2
        sprite=pygame.Surface((size,size),pygame.SRCALPHA)
        cx=cy=size//2
        count=11
        points=[]
        for i in range(count):
            a=math.tau*i/count
            rr=radius*rng.uniform(.78,1.08)
            points.append((cx+int(math.cos(a)*rr),cy+int(math.sin(a)*rr)))
        pygame.draw.polygon(sprite,(43,57,72),[(x+2,y+3) for x,y in points])
        pygame.draw.polygon(sprite,(94,116,132),points)
        pygame.draw.polygon(sprite,(147,164,175),points, max(1,radius//16))
        for _ in range(max(8,radius//2)):
            ox=rng.randint(-radius//2,radius//2); oy=rng.randint(-radius//2,radius//2)
            cr=rng.randint(2,max(2,radius//9))
            if ox*ox+oy*oy < (radius*.7)**2:
                pygame.draw.circle(sprite,(52,70,85),(cx+ox,cy+oy),cr)
                pygame.draw.arc(sprite,(173,187,193),(cx+ox-cr,cy+oy-cr,cr*2,cr*2),
                                math.pi*1.05,math.pi*1.8,1)
        # Mineral seams.
        for _ in range(3):
            ox=rng.randint(-radius//2,radius//2); oy=rng.randint(-radius//2,radius//2)
            pygame.draw.line(sprite,(108,158,174),(cx+ox,cy+oy),
                             (cx+ox+rng.randint(-7,7),cy+oy+rng.randint(-7,7)),1)
        self.asteroid_surfaces[key]=sprite
        return sprite

    def draw(self,surface,camera,station_position=(0,0)):
        for asteroid in self.manager.asteroids.values():
            x,y=camera.world_to_screen((asteroid.x,asteroid.y),surface.get_size())
            radius=max(5,int((25+5*asteroid.richness)*camera.zoom))
            variant=int(asteroid.richness) % 6
            sprite=scaled_sprite("space",f"asteroid_{variant}.png",
                                 (max(12,radius*2+12),max(12,radius*2+12)))
            surface.blit(sprite,sprite.get_rect(center=(x,y)))
            angle=self.elapsed*.7+asteroid.richness
            gx=x+int(math.cos(angle)*radius*.55); gy=y+int(math.sin(angle)*radius*.55)
            pygame.draw.circle(surface,(190,230,244),(gx,gy),max(1,int(2*camera.zoom)))
            ratio=asteroid.reserve/asteroid.max_reserve if asteroid.max_reserve else 0
            bar=pygame.Rect(x-radius,y+radius+5,radius*2,max(2,int(3*camera.zoom)))
            pygame.draw.rect(surface,(26,42,58),bar,border_radius=2)
            if ratio>0:
                pygame.draw.rect(surface,(86,207,172),
                    (bar.x,bar.y,max(1,int(bar.width*ratio)),bar.height),border_radius=2)
        for ship in self.manager.ships:
            x,y=camera.world_to_screen((ship.x,ship.y),surface.get_size())
            scale=max(.55,camera.zoom)
            if ship.task in ("outbound","returning"):
                target=self.manager.asteroids[ship.target_id]
                dx,dy=((target.x-ship.x,target.y-ship.y) if ship.task=="outbound" else (-ship.x,-ship.y))
                length=math.hypot(dx,dy) or 1
                tail=(int(x-dx/length*22*scale),int(y-dy/length*22*scale))
                pygame.draw.line(surface,(40,130,190),(x,y),tail,max(2,int(4*scale)))
                pygame.draw.line(surface,(110,220,255),(x,y),tail,max(1,int(scale)))
            pulse=.65+.35*math.sin(self.elapsed*8+len(ship.id))
            color=(int(100+70*pulse),int(195+40*pulse),255)
            if ship.task == "mining" and ship.target_id in self.manager.asteroids:
                asteroid=self.manager.asteroids[ship.target_id]
                ax,ay=camera.world_to_screen((asteroid.x,asteroid.y),surface.get_size())
                beam_color=(int(45+65*pulse),int(150+75*pulse),255)
                pygame.draw.line(surface, beam_color, (x,y),(ax,ay),
                                 max(1,int(1+pulse*2)))
                pygame.draw.circle(surface,(155,235,255),(ax,ay),max(2,int(3*pulse*scale)))
            miner_sprite=scaled_sprite("ships","miner.png",
                                       (max(16,int(74*scale)),max(8,int(37*scale))))
            surface.blit(miner_sprite,miner_sprite.get_rect(center=(x,y)))
