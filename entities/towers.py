# entities/towers.py
"""Multiclass character towers. One tower is one character, not one class."""
import math
import random
import pygame

from core.dnd_math import roll_4d6_drop_lowest, get_modifier
from core.assets import get_image
from entities.projectiles import Bullet, SplashBullet
from settings import CELL_SIZE
from entities.class_progression import CLASSES, MAX_CHARACTER_LEVEL

try:
    from meta.profile import profile
except Exception:
    profile = None

pygame.font.init()
LVL_FONT = pygame.font.SysFont(None, 20)
PLUS_FONT = pygame.font.SysFont(None, 36)


class Tower:
    name = "Персонаж"
    base_range = 110
    sprite_name = "warrior.png"
    fallback_color = (70, 110, 200)

    def __init__(self, x, y, level_map, initial_class=None):
        self.x, self.y = float(x), float(y)
        self.level_map = level_map
        col, row = int(self.x // CELL_SIZE), int(self.y // CELL_SIZE)
        self.elevation = level_map.get_elevation(col, row)
        self.image = get_image(self.sprite_name, (40, 40), self.fallback_color)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        stat_bonus = 0
        if profile is not None:
            try:
                stat_bonus = profile.get_stat_bonus()
            except Exception:
                pass
        self.stats = {
            key: roll_4d6_drop_lowest(stat_bonus)
            for key in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
        }
        self.mods = {key: get_modifier(value) for key, value in self.stats.items()}

        # Уровни всех классов. Сумма всегда равна уровню персонажа.
        self.class_levels = {initial_class: 1} if initial_class else {}
        self.level = 1
        self.xp = 0
        self.xp_to_next = 50
        # A newly built character must assign its first level to a class.
        self.pending_class_choices = 0 if initial_class else 1
        self.skills = []
        self.current_cooldown = 0.0
        self._recalculate_combat_stats()

    @property
    def pending_upgrades(self):
        """Compatibility with the old UI; pending entries now mean class choices."""
        return [self.level] * self.pending_class_choices

    @property
    def skill_tree(self):
        return {}

    def gain_xp(self, amount):
        if self.level >= MAX_CHARACTER_LEVEL:
            return
        self.xp += max(0, amount)
        while self.xp >= self.xp_to_next and self.level < MAX_CHARACTER_LEVEL:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.45)
            self.pending_class_choices += 1
            self._recalculate_combat_stats()
        if self.level >= MAX_CHARACTER_LEVEL:
            self.xp = 0

    def choose_class_level(self, class_id):
        """Spend one earned character level on a class (new or already known)."""
        if self.pending_class_choices <= 0 or class_id not in CLASSES:
            return False
        self.class_levels[class_id] = self.class_levels.get(class_id, 0) + 1
        self.pending_class_choices -= 1
        self._recalculate_combat_stats()
        return True

    def apply_skill(self, level, skill_name):
        """Compatibility hook retained for older callers."""
        if skill_name not in self.skills:
            self.skills.append(skill_name)

    def _recalculate_combat_stats(self):
        # Общие параметры персонажа складываются из уровней классов.
        total_class_levels = sum(self.class_levels.values())
        self.damage = 1.0
        self.range = self.base_range
        self.cooldown_time = 1.0
        best_attack_bonus = 2
        self.splash_radius = 0
        self.crit_chance = 5
        self.crit_multiplier = 2
        self.multi_shot = 1
        self.ignore_ac = False
        self.damage_multiplier = 1.0
        self.attack_bonus = 2 + max(self.mods.values()) + (total_class_levels - 1) // 4

        for class_id, class_level in self.class_levels.items():
            data = CLASSES[class_id]
            stat_mod = self.mods[data["stat"]]
            self.damage += class_level * max(0.45, data["damage"] + stat_mod * 0.22)
            self.range = max(self.range, self.base_range + data["range"] + max(0, class_level - 1) * 2)
            self.cooldown_time += class_level * data["cooldown"]
            best_attack_bonus = max(best_attack_bonus, 2 + stat_mod)

            if class_id == "fighter":
                if class_level >= 2:
                    self.damage_multiplier *= 1.10
                if class_level >= 5:
                    self.multi_shot = max(self.multi_shot, 2)
            if class_id == "rogue":
                self.crit_chance += 4 + max(0, stat_mod)
                if class_level >= 2:
                    self.crit_multiplier = max(self.crit_multiplier, 3)
                if class_level >= 5:
                    self.crit_multiplier = max(self.crit_multiplier, 5)
            if class_id in ("wizard", "cleric", "druid", "bard", "sorcerer", "warlock") and class_level >= 2:
                self.splash_radius = max(self.splash_radius, 42 + max(0, self.mods["WIS"]) * 4)
            if class_id in ("wizard", "cleric", "druid", "sorcerer") and class_level >= 5:
                self.splash_radius += 25
            if class_id == "ranger":
                if class_level >= 2:
                    self.multi_shot = max(self.multi_shot, 2)
                if class_level >= 5:
                    self.multi_shot = max(self.multi_shot, 3)
            if class_id == "monk":
                if class_level >= 2:
                    self.multi_shot = max(self.multi_shot, 2)
                if class_level >= 5:
                    self.multi_shot = max(self.multi_shot, 3)
            if class_id == "paladin":
                if class_level >= 2:
                    self.damage_multiplier *= 1.1
                if class_level >= 5:
                    self.splash_radius = max(self.splash_radius, 35)
            if class_id == "barbarian":
                if class_level >= 2:
                    self.damage_multiplier *= 1.2
                if class_level >= 5:
                    self.damage_multiplier *= 1.15
            if class_id == "bard" and class_level >= 5:
                self.damage_multiplier *= 1.15
            if class_id == "sorcerer" and class_level >= 2:
                self.damage_multiplier *= 1.15
            if class_id == "warlock":
                if class_level >= 2:
                    self.ignore_ac = True
                if class_level >= 5:
                    self.damage_multiplier *= 1.25

        self.attack_bonus = max(best_attack_bonus, self.attack_bonus)
        if self.elevation == 2:
            self.range = int(self.range * 1.25)
        elif self.elevation == 0:
            self.range = int(self.range * 0.8)
        self.damage = max(1, int(round(self.damage * self.damage_multiplier)))
        self.cooldown_time = max(0.18, min(2.0, self.cooldown_time))
        self.crit_chance = min(75, max(0, self.crit_chance))
        self.splash_radius = max(0, int(self.splash_radius))

        self.class_summary = " / ".join(
            f"{CLASSES[cid]['name']} {lvl}" for cid, lvl in self.class_levels.items()
        )
        self.skills = []
        for cid, lvl in self.class_levels.items():
            for feature_level, text in CLASSES[cid]["features"].items():
                if lvl >= feature_level:
                    self.skills.append(text)

    def update(self, dt, enemies, bullets_list):
        if self.current_cooldown > 0:
            self.current_cooldown -= dt
        if self.current_cooldown > 0:
            return

        target = None
        closest_progress = -1
        for enemy in enemies:
            if not enemy.alive:
                continue
            distance = math.hypot(enemy.rect.centerx - self.x, enemy.rect.centery - self.y)
            if distance <= self.range:
                progress = enemy.current_wp_index
                if progress > closest_progress:
                    closest_progress = progress
                    target = enemy
        if target is not None:
            self.shoot(target, bullets_list)
            self.current_cooldown = self.cooldown_time

    def shoot(self, enemy, bullets_list):
        damage = self.damage
        if self.crit_chance and random.randint(1, 100) <= self.crit_chance:
            damage *= self.crit_multiplier

        for i in range(self.multi_shot):
            offset = (i - (self.multi_shot - 1) / 2) * 8
            if self.splash_radius > 0:
                bullets_list.append(SplashBullet(
                    self.x + offset, self.y, enemy, damage, self.attack_bonus,
                    self.splash_radius, self,
                ))
            else:
                bullets_list.append(Bullet(
                    self.x + offset, self.y, enemy, damage, self.attack_bonus, self,
                ))

    def draw(self, surface):
        shadow = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - self.rect.height // 4))
        surface.blit(self.image, self.rect)
        level_label = LVL_FONT.render(f"Lv.{self.level}", True, (255, 255, 255))
        surface.blit(level_label, (self.rect.left, self.rect.bottom))
        if self.pending_class_choices:
            plus = PLUS_FONT.render("+", True, (50, 255, 50))
            offset = math.sin(pygame.time.get_ticks() / 200.0) * 3
            surface.blit(plus, (self.rect.centerx - 8, self.rect.top - 25 + offset))


# Старые имена оставлены для совместимости. Все три создают персонажа,
# отличающегося только стартовым классом.
class WarriorTower(Tower):
    name = "Воин"
    sprite_name = "warrior.png"
    fallback_color = (50, 100, 200)
    def __init__(self, x, y, level_map):
        super().__init__(x, y, level_map, "fighter")

class RogueTower(Tower):
    name = "Плут"
    sprite_name = "rogue.png"
    fallback_color = (200, 200, 50)
    def __init__(self, x, y, level_map):
        self.sprite_name = "rogue.png"
        self.fallback_color = (200, 200, 50)
        super().__init__(x, y, level_map, "rogue")

class MageTower(Tower):
    name = "Волшебник"
    sprite_name = "mage.png"
    fallback_color = (150, 50, 200)
    def __init__(self, x, y, level_map):
        self.sprite_name = "mage.png"
        self.fallback_color = (150, 50, 200)
        super().__init__(x, y, level_map, "wizard")
