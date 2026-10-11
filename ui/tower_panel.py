# ui/tower_panel.py
"""Click-through tower sheet and class-level selection modal."""
import pygame
from entities.class_progression import CLASSES, CLASS_ORDER


class TowerPanel:
    def __init__(self, screen_size):
        self.screen_w, self.screen_h = screen_size
        self.rect = pygame.Rect(0, 0, min(560, self.screen_w - 24), min(560, self.screen_h - 24))
        self.rect.center = (self.screen_w // 2, self.screen_h // 2)
        self.font = pygame.font.SysFont(None, 25)
        self.small = pygame.font.SysFont(None, 20)
        self.title = pygame.font.SysFont(None, 32)
        self.class_buttons = []
        self.close_rect = pygame.Rect(self.rect.right - 38, self.rect.top + 10, 28, 28)

    def _text(self, surface, text, pos, font=None, color=(235, 235, 235)):
        font = font or self.font
        surface.blit(font.render(str(text), True, color), pos)

    def draw(self, screen, tower):
        shade = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 165))
        screen.blit(shade, (0, 0))

        panel = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel.fill((28, 32, 43, 248))
        screen.blit(panel, self.rect.topleft)
        pygame.draw.rect(screen, (190, 190, 205), self.rect, 2, border_radius=10)

        self._text(screen, f"Персонаж — уровень {tower.level}",
                   (self.rect.x + 18, self.rect.y + 14), self.title, (255, 220, 120))
        if not tower.pending_class_choices:
            pygame.draw.rect(screen, (65, 65, 75), self.close_rect, border_radius=5)
            self._text(screen, "X", (self.close_rect.x + 9, self.close_rect.y + 5), self.font)
        else:
            self._text(screen, "Выберите класс для нового уровня", (self.rect.x + 18, self.rect.y + 48),
                       self.font, (120, 255, 140))

        y = self.rect.y + (76 if tower.pending_class_choices else 54)
        line_h = 25
        stats = "  ".join(f"{key} {value} ({tower.mods[key]:+d})" for key, value in tower.stats.items())
        self._text(screen, "Характеристики:", (self.rect.x + 18, y), self.font, (150, 200, 255))
        self._text(screen, stats, (self.rect.x + 18, y + line_h), self.small)
        self._text(screen, f"Урон: {tower.damage}    Меткость: +{tower.attack_bonus}    "
                            f"Крит: {tower.crit_chance}% x{tower.crit_multiplier}",
                   (self.rect.x + 18, y + line_h * 2), self.small)
        self._text(screen, f"Дальность: {tower.range}    Перезарядка: {tower.cooldown_time:.2f}с    "
                            f"Радиус области: {tower.splash_radius}",
                   (self.rect.x + 18, y + line_h * 3), self.small)
        self._text(screen, f"Опыт: {tower.xp}/{tower.xp_to_next}    "
                            f"До выбора класса: {tower.pending_class_choices}",
                   (self.rect.x + 18, y + line_h * 4), self.small, (255, 220, 120))

        class_y = y + line_h * 5 + 8
        self._text(screen, "Мультикласс:", (self.rect.x + 18, class_y), self.font, (150, 200, 255))
        class_y += line_h
        if tower.class_levels:
            class_entries = [f"{CLASSES[class_id]['name']} {level}"
                             for class_id, level in tower.class_levels.items()]
            # Wrap into at most three compact rows so broad multiclass builds fit.
            per_row = 4
            for start in range(0, len(class_entries), per_row):
                self._text(screen, "  |  ".join(class_entries[start:start + per_row]),
                           (self.rect.x + 18, class_y), self.small)
                class_y += 19

        feature_y = self.rect.y + 292
        self._text(screen, "Открытые способности:", (self.rect.x + 18, feature_y), self.font,
                   (150, 200, 255))
        features = tower.skills or ["Пока нет; способности открываются с уровнями классов."]
        for i, skill in enumerate(features[:3]):
            self._text(screen, f"• {skill}", (self.rect.x + 18, feature_y + 25 + i * 21), self.small)

        self.class_buttons = []
        if tower.pending_class_choices:
            label_y = self.rect.y + 390
            self._text(screen, "Каждый выбор повышает общий уровень на 1:",
                       (self.rect.x + 18, label_y), self.small, (255, 220, 120))
            cols = 3
            gap = 7
            left = self.rect.x + 18
            top = label_y + 25
            button_w = (self.rect.width - 36 - gap * (cols - 1)) // cols
            button_h = 30
            for i, class_id in enumerate(CLASS_ORDER):
                row, col = divmod(i, cols)
                rect = pygame.Rect(left + col * (button_w + gap), top + row * (button_h + 6), button_w, button_h)
                self.class_buttons.append((rect, class_id))
                pygame.draw.rect(screen, (62, 79, 103), rect, border_radius=4)
                pygame.draw.rect(screen, (145, 160, 180), rect, 1, border_radius=4)
                level = tower.class_levels.get(class_id, 0)
                name = CLASSES[class_id]["name"]
                text = self.small.render(f"{name} {level}→{level + 1}", True, (255, 255, 255))
                screen.blit(text, text.get_rect(center=rect.center))
        else:
            self._text(screen, "Нажмите на другую башню, чтобы открыть её карточку.",
                       (self.rect.x + 18, self.rect.bottom - 34), self.small, (185, 185, 195))

    def handle_click(self, pos, tower):
        """Returns class_id when selected; 'close' when closed; otherwise None."""
        for rect, class_id in self.class_buttons:
            if rect.collidepoint(pos) and tower.pending_class_choices:
                return class_id
        if not tower.pending_class_choices and self.close_rect.collidepoint(pos):
            return "close"
        if not self.rect.collidepoint(pos) and not tower.pending_class_choices:
            return "close"
        return None
