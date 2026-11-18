"""Reusable tutorial briefing and single-active-quest panel."""
import pygame
from ui import theme


class ProgressionPanel:
    def __init__(self, progression, bottom):
        self.progression, self.bottom = progression, bottom
        self.visible = True
        self.action_rect = pygame.Rect(0, 0, 1, 1)
        self.dismiss_rect = pygame.Rect(0, 0, 1, 1)
        self.replay_rect = pygame.Rect(0, 0, 1, 1)
        self._replay_text = None

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False
        self.progression.mark_intro_seen()

    def handle_event(self, event):
        if not self.visible or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.action_rect.collidepoint(event.pos):
            ok, message = self.progression.perform_salvage()
            self.bottom.push(message, theme.GREEN if ok else theme.RED)
            for item in self.progression.take_events():
                self.bottom.push(item)
            return True
        if self.replay_rect.collidepoint(event.pos):
            self._replay_text = self.progression.replay_explanation()
            return True
        if self.dismiss_rect.collidepoint(event.pos):
            self.close()
            return True
        return True

    def draw(self, surface):
        if not self.visible:
            return
        w, h = surface.get_size()
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((1, 5, 15, 205))
        surface.blit(shade, (0, 0))
        panel = pygame.Rect(max(180, w // 2 - 350), max(80, h // 2 - 235), 700, 470)
        theme.panel(surface, panel, fill=(7, 17, 32))
        pygame.draw.rect(surface, theme.BORDER_BRIGHT, panel, 1, border_radius=9)
        stage = self.progression.current_task()
        theme.label(surface, "ЦЕНТР НАВЧАННЯ • ПРОТОКОЛ ВІДНОВЛЕННЯ",
                    (panel.x + 24, panel.y + 20), 13, theme.CYAN, True)
        if stage:
            number = self.progression.stage_index + 1
            theme.label(surface, f"ЕТАП {number:02d} / 10", (panel.x + 24, panel.y + 52),
                        10, theme.GREEN, True)
            theme.label(surface, stage["title"], (panel.x + 24, panel.y + 75),
                        26, theme.TEXT, True)
            self._wrapped(surface, stage["description"],
                          pygame.Rect(panel.x + 24, panel.y + 116, panel.width - 48, 76),
                          theme.MUTED, 14, 3)
            objective = stage["objective"]
            theme.label(surface, "ЄДИНЕ АКТИВНЕ ЗАВДАННЯ", (panel.x + 24, panel.y + 207),
                        10, theme.CYAN, True)
            theme.label(surface, objective.get("label", stage["title"]),
                        (panel.x + 24, panel.y + 230), 17, theme.TEXT, True)
            progress = self.progression._last_objective_progress
            target = objective.get("count", objective.get("target", 1))
            if objective["type"] == "buildings":
                progress_text = "Виконати обидві вимоги"
            else:
                progress_text = f"Поточний прогрес: {progress} / {target}"
            theme.label(surface, progress_text, (panel.x + 24, panel.y + 258),
                        11, theme.GREEN)
            mechanics = ", ".join(self.progression.MECHANIC_LABELS.get(x, x)
                                  for x in stage.get("mechanics", []))
            theme.label(surface, "ВІДКРИЄТЬСЯ: " + (mechanics or "—"),
                        (panel.x + 24, panel.y + 286), 10, theme.CYAN)
            reward = stage.get("reward", {})
            reward_text = f"Нагорода: +{reward.get('xp', 0)} XP"
            if reward.get("resources"):
                reward_text += " • ресурси та матеріали для наступного етапу"
            theme.label(surface, reward_text, (panel.x + 24, panel.y + 311),
                        10, theme.GOLD)
            self.replay_rect = pygame.Rect(panel.x + 24, panel.bottom - 66, 190, 38)
            pygame.draw.rect(surface, (13, 31, 48), self.replay_rect, border_radius=5)
            pygame.draw.rect(surface, theme.BORDER, self.replay_rect, 1, border_radius=5)
            theme.label(surface, "ПОВТОРИТИ ПОЯСНЕННЯ",
                        (self.replay_rect.x + 10, self.replay_rect.y + 12), 9, theme.TEXT, True)
            self.action_rect = pygame.Rect(0, 0, 1, 1)
            if stage["id"] == "awakening":
                self.action_rect = pygame.Rect(panel.x + 230, panel.bottom - 66, 270, 38)
                pygame.draw.rect(surface, (12, 67, 91), self.action_rect, border_radius=5)
                pygame.draw.rect(surface, theme.CYAN, self.action_rect, 1, border_radius=5)
                theme.label(surface, "ЗАПУСТИТИ АВАРІЙНИЙ ЗБІР",
                            (self.action_rect.x + 12, self.action_rect.y + 12), 10, theme.TEXT, True)
            elif stage["id"] == "power":
                theme.label(surface, "ПІДКАЗКА: відкрийте «Будівництво» → «Сонячна панель» → «Побудувати».",
                            (panel.x + 230, panel.bottom - 54), 10, theme.GREEN)
            else:
                theme.label(surface, "Виконайте дію у відповідному розділі гри.",
                            (panel.x + 230, panel.bottom - 54), 10, theme.GREEN)
        else:
            theme.label(surface, "Початкову кампанію завершено.",
                        (panel.x + 24, panel.y + 110), 20, theme.GREEN, True)
            theme.label(surface, "Усі базові механіки імперії відкриті.",
                        (panel.x + 24, panel.y + 150), 13, theme.MUTED)
            self.action_rect = self.replay_rect = pygame.Rect(0, 0, 1, 1)
        if self._replay_text:
            self._wrapped(surface, self._replay_text,
                          pygame.Rect(panel.x + 24, panel.y + 350, panel.width - 48, 44),
                          theme.GOLD, 11, 2)
        self.dismiss_rect = pygame.Rect(panel.right - 150, panel.bottom - 66, 126, 38)
        pygame.draw.rect(surface, (13, 31, 48), self.dismiss_rect, border_radius=5)
        pygame.draw.rect(surface, theme.BORDER, self.dismiss_rect, 1, border_radius=5)
        theme.label(surface, "ПРОДОВЖИТИ",
                    (self.dismiss_rect.x + 12, self.dismiss_rect.y + 12), 10, theme.TEXT, True)

    @staticmethod
    def _wrapped(surface, text, rect, color, size, max_lines=4):
        font = pygame.font.SysFont("segoeui", size)
        words, lines, line = str(text).split(), [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if line and font.size(candidate)[0] > rect.width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for index, value in enumerate(lines[:max_lines]):
            surface.blit(font.render(value, True, color), (rect.x, rect.y + index * (size + 4)))
