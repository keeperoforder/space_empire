"""Campaign journal with the active tutorial objective and quick navigation."""
import pygame
from ui import theme


class CampaignPanel:
    def __init__(self, manager, bottom, progression=None, on_build=None):
        self.manager, self.bottom = manager, bottom
        self.progression = progression
        self.on_build = on_build
        self.visible = False
        self.scroll = 0
        self.choice_rects = []
        self.close_rect = pygame.Rect(0, 0, 1, 1)
        self.build_rect = pygame.Rect(0, 0, 1, 1)

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 32)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.build_rect.collidepoint(event.pos):
                if self.on_build:
                    self.on_build()
                self.close()
                self.bottom.push("Відкрито конструктор станції.")
                return True
            if self.manager.active_event:
                for rect, cid in self.choice_rects:
                    if rect.collidepoint(event.pos):
                        ok, msg = self.manager.choose_event(cid)
                        self.bottom.push(msg)
                        return True
            if self.close_rect.collidepoint(event.pos):
                self.close()
            return True
        return False

    def _wrap(self, surface, text, rect, color, size=14, limit=4):
        font = pygame.font.SysFont("segoeui", size)
        words, lines, line = str(text).split(), [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if font.size(candidate)[0] > rect.width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for i, value in enumerate(lines[:limit]):
            surface.blit(font.render(value, True, color), (rect.x, rect.y + i * (size + 4)))

    def draw(self, surface):
        if not self.visible:
            return
        w, h = surface.get_size()
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((1, 5, 15, 215))
        surface.blit(shade, (0, 0))
        panel = pygame.Rect(220, 86, w - 500, h - 176)
        theme.panel(surface, panel, fill=(7, 17, 32))
        pygame.draw.rect(surface, theme.BORDER_BRIGHT, panel, 1, border_radius=9)
        title = "КОСМІЧНА ПОДІЯ" if self.manager.active_event else "СЮЖЕТНА КАМПАНІЯ"
        theme.label(surface, title, (panel.x + 24, panel.y + 17), 19, theme.CYAN, True)
        self.close_rect = pygame.Rect(panel.right - 42, panel.y + 12, 30, 30)
        theme.label(surface, "×", (self.close_rect.x + 8, self.close_rect.y), 24, theme.TEXT, True)

        # The tutorial progression is the source of truth for the opening campaign.
        if self.progression is not None and not self.manager.active_event:
            stage = self.progression.current_task()
            if stage is None:
                theme.label(surface, "Початкову кампанію завершено.",
                            (panel.x + 24, panel.y + 80), 22, theme.GREEN, True)
                theme.label(surface, "Усі базові механіки імперії відкриті.",
                            (panel.x + 24, panel.y + 120), 14, theme.MUTED)
                self.build_rect = pygame.Rect(0, 0, 1, 1)
                return
            task_title = ("Відновити енергосистему станції"
                          if stage.get("id") == "power" else stage.get("title", "Активне завдання"))
            theme.label(surface, f"АКТИВНЕ ЗАВДАННЯ • ЕТАП {self.progression.stage_index + 1:02d}/10",
                        (panel.x + 24, panel.y + 67), 11, theme.GREEN, True)
            theme.label(surface, task_title, (panel.x + 24, panel.y + 100),
                        24, theme.TEXT, True)
            self._wrap(surface, stage.get("description", ""),
                       pygame.Rect(panel.x + 24, panel.y + 145, panel.width - 48, 76),
                       theme.MUTED, 15, 4)
            objective = stage.get("objective", {})
            theme.label(surface, objective.get("label", task_title),
                        (panel.x + 24, panel.y + 240), 16, theme.CYAN, True)
            if stage.get("id") == "power":
                hint = "Підказка: натисніть «Будівництво», виберіть «Сонячна панель» і натисніть «Побудувати»."
            else:
                hint = "Підказка: виконайте ціль у відповідному розділі станції."
            self._wrap(surface, hint,
                       pygame.Rect(panel.x + 24, panel.y + 278, panel.width - 48, 54),
                       theme.GOLD, 13, 3)
            progress = self.progression._last_objective_progress
            target = objective.get("count", objective.get("target", 1))
            theme.label(surface, f"Прогрес: {progress} / {target}",
                        (panel.x + 24, panel.y + 340), 12, theme.GREEN)
            self.build_rect = pygame.Rect(panel.x + 24, panel.bottom - 66, 270, 40)
            pygame.draw.rect(surface, (12, 67, 91), self.build_rect, border_radius=5)
            pygame.draw.rect(surface, theme.CYAN, self.build_rect, 1, border_radius=5)
            theme.label(surface, "ПЕРЕЙТИ ДО БУДІВНИЦТВА",
                        (self.build_rect.x + 13, self.build_rect.y + 13), 10, theme.TEXT, True)
            return

        self.build_rect = pygame.Rect(0, 0, 1, 1)
        if self.manager.active_event:
            e = self.manager.active_event
            art = pygame.Rect(panel.x + 24, panel.y + 60, 245, 190)
            pygame.draw.rect(surface, (10, 35, 57), art, border_radius=8)
            pygame.draw.rect(surface, theme.CYAN, art, 1, border_radius=8)
            cx, cy = art.center
            for r in (34, 57, 80):
                pygame.draw.circle(surface, (31, 105, 140), (cx, cy), r, 1)
            if e["illustration"] in ("ship", "asteroid", "artifact"):
                pygame.draw.polygon(surface, (110, 137, 154),
                    [(cx-55,cy),(cx-18,cy-40),(cx+43,cy-25),(cx+55,cy+15),(cx,cy+43)])
                pygame.draw.circle(surface, theme.CYAN, (cx+12,cy-4), 7)
            else:
                for r in range(20, 75, 12):
                    pygame.draw.arc(surface, theme.CYAN, (cx-r,cy-r,2*r,2*r), .2, 2.8, 2)
            theme.label(surface, e["category"].upper(), (art.x+12,art.bottom-23), 10, theme.CYAN, True)
            theme.label(surface, e["title"], (art.right+22,art.y+5), 21, theme.TEXT, True)
            self._wrap(surface,e["description"],pygame.Rect(art.right+22,art.y+42,panel.right-art.right-55,110),theme.MUTED,15,5)
            self.choice_rects = []
            y = art.bottom + 22
            for choice in e["choices"]:
                rect = pygame.Rect(panel.x+24,y,panel.width-48,62)
                pygame.draw.rect(surface,(13,39,59),rect,border_radius=6)
                pygame.draw.rect(surface,theme.BORDER,rect,1,border_radius=6)
                theme.label(surface,choice["label"],(rect.x+13,rect.y+7),14,theme.CYAN,True)
                self._wrap(surface,choice["description"],pygame.Rect(rect.x+13,rect.y+30,rect.width-26,26),theme.MUTED,11,1)
                self.choice_rects.append((rect,choice["id"]))
                y += 71
            return

        ch = self.manager.current_chapter()
        if not ch:
            theme.label(surface, "Дані кампанії поки недоступні.",
                        (panel.x + 24, panel.y + 70), 14, theme.MUTED)
            return
        theme.label(surface,ch["title"],(panel.x+24,panel.y+56),22,theme.TEXT,True)
        self._wrap(surface,ch.get("story", ""),pygame.Rect(panel.x+24,panel.y+91,panel.width-48,60),theme.MUTED,14,4)
        area=pygame.Rect(panel.x+18,panel.y+160,panel.width-36,panel.height-176)
        clip=surface.get_clip()
        surface.set_clip(area)
        y=area.y-self.scroll
        for chapter in self.manager.chapters:
            complete=all(self.manager.missions[x]["status"]=="completed" for x in chapter["missions"])
            theme.label(surface,("✓ " if complete else "◇ ")+chapter["title"],(area.x+8,y),14,theme.GREEN if complete else theme.CYAN,True)
            y+=25
            for mid in chapter["missions"]:
                mission=self.manager.missions[mid]
                color=theme.GREEN if mission["status"]=="completed" else theme.TEXT if mission["status"]=="available" else theme.MUTED
                theme.label(surface,mission["title"],(area.x+25,y),12,color,mission["status"]=="available")
                target=max(1,mission["objective"].get("amount",1))
                progress=min(1,float(mission.get("progress",0))/target)
                bar=pygame.Rect(area.x+260,y+3,180,7)
                pygame.draw.rect(surface,(25,43,60),bar,border_radius=3)
                pygame.draw.rect(surface,theme.CYAN,(bar.x,bar.y,int(bar.width*progress),7),border_radius=3)
                status={"completed":"ВИКОНАНО","available":"АКТИВНА","locked":"ЗАБЛОКОВАНА"}[mission["status"]]
                theme.label(surface,status,(bar.right+12,y),10,color,True)
                y+=17
                objective=mission["objective"]
                condition=f"Умова: {objective.get('key',objective.get('type','ціль'))} — {objective.get('amount',1)}"
                self._wrap(surface,mission.get("description",condition),pygame.Rect(area.x+25,y,area.width-55,28),theme.MUTED,10,1)
                reward_text="Нагорода: "+", ".join(f"{k} +{v}" for k,v in mission.get("rewards",{}).items())
                theme.label(surface,reward_text,(area.x+25,y+13),9,theme.CYAN if mission["status"]!="locked" else theme.MUTED)
                y+=31
            y+=10
        surface.set_clip(clip)
