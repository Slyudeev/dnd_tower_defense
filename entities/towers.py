# entities/towers.py
import pygame
import math
from core.dnd_math import roll_4d6_drop_lowest, get_modifier
from meta.profile import profile
from entities.projectiles import Bullet, SplashBullet
from core.assets import get_image
from settings import CELL_SIZE
from entities.classes import CLASS_DATA

pygame.font.init()
LVL_FONT = pygame.font.SysFont(None, 20)
PLUS_FONT = pygame.font.SysFont(None, 36)

class HeroTower:
    def __init__(self, x, y, level_map, first_class):
        self.x = x
        self.y = y
        self.level_map = level_map
        col, row = int(self.x // CELL_SIZE), int(self.y // CELL_SIZE)
        self.elevation = level_map.get_elevation(col, row)

        # Базовые характеристики (бросаются как в D&D)
        bonus = profile.get_stat_bonus() if hasattr(profile, 'get_stat_bonus') else 0
        self.stats = {
            "STR": roll_4d6_drop_lowest(bonus), "DEX": roll_4d6_drop_lowest(bonus),
            "CON": roll_4d6_drop_lowest(bonus), "INT": roll_4d6_drop_lowest(bonus),
            "WIS": roll_4d6_drop_lowest(bonus), "CHA": roll_4d6_drop_lowest(bonus)
        }
        self.mods = {stat: get_modifier(val) for stat, val in self.stats.items()}

        # Прокачка и классы
        self.classes = {}
        self.global_level = 0
        self.xp = 0
        self.xp_to_next = 50
        self.unspent_levels = 0
        self.pending_choices = []
        
        self.skills = []
        self.learned_skill_names = []

        # Боевые статы (высчитываются от модов)
        self.base_range = 130
        self.damage = max(1, 2 + self.mods["STR"])
        self.attack_bonus = 2 + self.mods["DEX"]
        self.cooldown_time = max(0.4, 1.2 - (self.mods["DEX"] * 0.1))
        self.crit_chance = 5
        self.crit_multiplier = 2
        self.splash_radius = 0
        self.current_cooldown = 0
        
        # Получение первого класса при постройке
        self.primary_class = first_class
        c_data = CLASS_DATA[first_class]
        self.image = get_image(c_data["sprite"], (40, 40), c_data["color"])
        self.rect = self.image.get_rect(center=(self.x, self.y))
        
        self.level_up_class(first_class)

    @property
    def range(self):
        if self.elevation == 2: return int(self.base_range * 1.25)
        elif self.elevation == 0: return int(self.base_range * 0.8)
        return self.base_range

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.unspent_levels += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)

    def level_up_class(self, class_name):
        if self.unspent_levels > 0 and self.global_level > 0:
            self.unspent_levels -= 1
            
        self.global_level += 1
        if class_name not in self.classes:
            self.classes[class_name] = 0
            
        self.classes[class_name] += 1
        lvl = self.classes[class_name]
        
        # Применяем бонусы класса
        CLASS_DATA[class_name]["on_level_up"](self)
        
        # Проверяем, есть ли выбор навыка на этом уровне этого класса
        if lvl in CLASS_DATA[class_name]["choices"]:
            self.pending_choices.append({
                "class_name": class_name,
                "level": lvl,
                "options": CLASS_DATA[class_name]["choices"][lvl]
            })

    def apply_skill(self, choice_data, option_idx):
        opt = choice_data["options"][option_idx]
        opt["apply"](self)
        self.learned_skill_names.append(opt["name"])
        self.pending_choices.remove(choice_data)

    def update(self, dt, enemies, bullets_list):
        if self.current_cooldown > 0:
            self.current_cooldown -= dt
            
        if self.current_cooldown <= 0:
            for enemy in enemies:
                if not enemy.alive: continue
                dist = math.hypot(enemy.rect.centerx - self.x, enemy.rect.centery - self.y)
                if dist <= self.range:
                    self.shoot(enemy, bullets_list)
                    self.current_cooldown = self.cooldown_time
                    break

    def shoot(self, enemy, bullets_list):
        # Башня сама решает, как стрелять в зависимости от навыков!
        if "splash_attack" in self.skills or self.classes.get("Mage", 0) > 0:
            bullets_list.append(SplashBullet(self.x, self.y, enemy, self))
        else:
            bullets_list.append(Bullet(self.x, self.y, enemy, self))
            
        if "double_strike" in self.skills:
            bullets_list.append(Bullet(self.x + 8, self.y + 8, enemy, self))
            
        if "arrow_rain" in self.skills:
            bullets_list.append(Bullet(self.x + 15, self.y, enemy, self))
            bullets_list.append(Bullet(self.x - 15, self.y, enemy, self))

    def draw(self, surface):
        shadow = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - self.rect.height // 4))
        
        surface.blit(self.image, self.rect)
        
        lvl_text = LVL_FONT.render(f"Lv.{self.global_level}", True, (255, 255, 255))
        surface.blit(lvl_text, (self.rect.left, self.rect.bottom))
        
        for i in range(len(self.learned_skill_names)):
            pygame.draw.circle(surface, (255, 215, 0), (self.rect.right - 5, self.rect.bottom - 5 - (i * 8)), 3)

        if self.unspent_levels > 0 or len(self.pending_choices) > 0:
            plus_txt = PLUS_FONT.render("+", True, (50, 255, 50))
            offset = math.sin(pygame.time.get_ticks() / 200.0) * 3
            surface.blit(plus_txt, (self.rect.centerx - 8, self.rect.top - 25 + offset))
