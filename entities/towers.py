# entities/towers.py
import pygame
import math
import random

from core.dnd_math import roll_4d6_drop_lowest, get_modifier
from meta.profile import profile
from entities.projectiles import Bullet, SplashBullet
from core.assets import get_image
from settings import CELL_SIZE

pygame.font.init()
LVL_FONT = pygame.font.SysFont(None, 20)
PLUS_FONT = pygame.font.SysFont(None, 36) # Шрифт для значка "+"

class Tower:
    name = "Base"
    base_range = 100 

    def __init__(self, x, y, level_map, sprite_name, fallback_color):
        self.x = x
        self.y = y
        self.level_map = level_map
        
        col, row = int(self.x // CELL_SIZE), int(self.y // CELL_SIZE)
        self.elevation = level_map.get_elevation(col, row)
        
        # --- БОНУС ВЫСОТЫ ---
        if self.elevation == 2: self.range = int(self.base_range * 1.25)
        elif self.elevation == 0: self.range = int(self.base_range * 0.8)
        else: self.range = self.base_range
            
        self.image = get_image(sprite_name, (40, 40), fallback_color)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        
        self.level = 1
        self.xp = 0
        self.xp_to_next = 50
        
        # --- СИСТЕМА НАВЫКОВ ---
        self.skills = [] 
        self.pending_upgrades = [] # Список уровней, ожидающих выбора навыка
        self.skill_tree = {} # Дерево навыков (задается в наследниках)
        
        bonus = profile.get_stat_bonus()
        self.stats = {
            "STR": roll_4d6_drop_lowest(bonus), "DEX": roll_4d6_drop_lowest(bonus),
            "CON": roll_4d6_drop_lowest(bonus), "INT": roll_4d6_drop_lowest(bonus),
            "WIS": roll_4d6_drop_lowest(bonus), "CHA": roll_4d6_drop_lowest(bonus)
        }
        self.mods = {stat: get_modifier(val) for stat, val in self.stats.items()}
        
        self.cooldown_time = 1.0
        self.current_cooldown = 0
        self.damage = 1
        self.attack_bonus = 0 

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level_up()
            
    def level_up(self):
        self.level += 1
        self.xp_to_next = int(self.xp_to_next * 1.5) 
        
        self.damage += 1
        if self.level % 2 == 0:
            self.attack_bonus += 1
            
        # Если на этом уровне есть выбор навыков - добавляем в ожидание
        if self.level in self.skill_tree:
            self.pending_upgrades.append(self.level)
            
        print(f"[{self.name}] получил Уровень {self.level}!")

    def apply_skill(self, level, skill_name):
        """Метод применения навыка. Реализуется в наследниках."""
        self.skills.append(skill_name)
        print(f"[{self.name}] Изучил: {skill_name}")

    def print_stats(self):
        elevation_name = "Возвышенность" if self.elevation == 2 else ("Низина" if self.elevation == 0 else "Равнина")
        print(f"--- Построен [{self.name}] ({elevation_name}) ---")
        print(f"STR:{self.stats['STR']} DEX:{self.stats['DEX']} INT:{self.stats['INT']} WIS:{self.stats['WIS']} CHA:{self.stats['CHA']}")

    def update(self, dt, enemies, bullets_list):
        if self.current_cooldown > 0: self.current_cooldown -= dt
            
        if self.current_cooldown <= 0:
            for enemy in enemies:
                if not enemy.alive: continue
                dist = math.hypot(enemy.rect.centerx - self.x, enemy.rect.centery - self.y)
                if dist <= self.range:
                    self.shoot(enemy, bullets_list)
                    self.current_cooldown = self.cooldown_time
                    break

    def shoot(self, enemy, bullets_list):
        bullets_list.append(Bullet(self.x, self.y, enemy, self.damage, self.attack_bonus, self))

    def draw(self, surface):
        # 1. Тень
        shadow = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - self.rect.height // 4))
        
        # 2. Сама башня
        surface.blit(self.image, self.rect)
        
        # 3. Текст уровня
        lvl_text = LVL_FONT.render(f"Lv.{self.level}", True, (255, 255, 255))
        surface.blit(lvl_text, (self.rect.left, self.rect.bottom))
        
        # 4. Точки изученных навыков
        for i in range(len(self.skills)):
            pygame.draw.circle(surface, (255, 215, 0), (self.rect.right - 5, self.rect.bottom - 5 - (i * 8)), 3)

        # 5. Зеленый ПЛЮС, если есть доступная прокачка
        if len(self.pending_upgrades) > 0:
            plus_txt = PLUS_FONT.render("+", True, (50, 255, 50))
            # Анимация "прыжка" плюсика
            offset = math.sin(pygame.time.get_ticks() / 200.0) * 3
            surface.blit(plus_txt, (self.rect.centerx - 8, self.rect.top - 25 + offset))


# ==========================================
# ИГРОВЫЕ КЛАССЫ С ДЕРЕВОМ НАВЫКОВ
# ==========================================

class WarriorTower(Tower):
    name = "Warrior"
    base_range = 150

    def __init__(self, x, y, level_map):
        super().__init__(x, y, level_map, "warrior.png", (50, 100, 200))
        self.damage = max(1, 4 + self.mods["STR"])
        self.attack_bonus = 2 + self.mods["STR"]
        self.cooldown_time = max(0.2, 1.2 - (self.mods["DEX"] * 0.1))
        
        self.double_strike = False 

        # ДЕРЕВО НАВЫКОВ ВОИНА
        self.skill_tree = {
            3: [
                {"name": "Тяжелый удар", "desc": "+8 Базового Урона"},
                {"name": "Шквал ударов", "desc": "-40% Время перезарядки"}
            ],
            5: [
                {"name": "Двойной удар", "desc": "Выпускает 2 снаряда за раз"},
                {"name": "Мастер Оружия", "desc": "+5 Меткость (Игнор брони), +2 Урон"}
            ]
        }
        self.print_stats()

    def apply_skill(self, level, skill_name):
        super().apply_skill(level, skill_name)
        if skill_name == "Тяжелый удар": self.damage += 8
        elif skill_name == "Шквал ударов": self.cooldown_time *= 0.6
        elif skill_name == "Двойной удар": self.double_strike = True
        elif skill_name == "Мастер Оружия": 
            self.attack_bonus += 5
            self.damage += 2

    def shoot(self, enemy, bullets_list):
        bullets_list.append(Bullet(self.x, self.y, enemy, self.damage, self.attack_bonus, self))
        if self.double_strike:
            bullets_list.append(Bullet(self.x + 8, self.y + 8, enemy, self.damage, self.attack_bonus, self))


class RogueTower(Tower):
    name = "Rogue"
    base_range = 130

    def __init__(self, x, y, level_map):
        super().__init__(x, y, level_map, "rogue.png", (200, 200, 50))
        self.damage = max(1, 2 + self.mods["DEX"])
        self.attack_bonus = 4 + self.mods["DEX"]
        self.cooldown_time = 0.4 
        
        self.crit_chance = max(0, 5 + (self.mods["CHA"] * 5) + (self.mods["WIS"] * 2))
        self.crit_multiplier = 3 
        self.arrow_rain = False

        # ДЕРЕВО НАВЫКОВ ПЛУТА
        self.skill_tree = {
            3: [
                {"name": "Любимец фортуны", "desc": "+20% Шанс критического удара"},
                {"name": "Орлиный глаз", "desc": "+50 Радиус атаки"}
            ],
            5: [
                {"name": "Ассасин", "desc": "Крит. удар наносит x5 урона"},
                {"name": "Град стрел", "desc": "Выпускает 3 стрелы веером"}
            ]
        }
        self.print_stats()

    def apply_skill(self, level, skill_name):
        super().apply_skill(level, skill_name)
        if skill_name == "Любимец фортуны": self.crit_chance += 20
        elif skill_name == "Орлиный глаз": self.range += 50
        elif skill_name == "Ассасин": self.crit_multiplier = 5
        elif skill_name == "Град стрел": self.arrow_rain = True

    def shoot(self, enemy, bullets_list):
        final_damage = self.damage
        if random.randint(1, 100) <= self.crit_chance:
            final_damage *= self.crit_multiplier 
            
        bullets_list.append(Bullet(self.x, self.y, enemy, final_damage, self.attack_bonus, self))
        
        if self.arrow_rain:
            bullets_list.append(Bullet(self.x + 15, self.y, enemy, final_damage, self.attack_bonus, self))
            bullets_list.append(Bullet(self.x - 15, self.y, enemy, final_damage, self.attack_bonus, self))


class MageTower(Tower):
    name = "Mage"
    base_range = 180

    def __init__(self, x, y, level_map):
        super().__init__(x, y, level_map, "mage.png", (150, 50, 200))
        self.damage = max(1, 8 + self.mods["INT"])
        self.attack_bonus = 3 + self.mods["INT"]
        self.cooldown_time = 2.5 
        self.splash_radius = max(30, 60 + (self.mods["WIS"] * 8))
        self.ignore_ac = False 

        # ДЕРЕВО НАВЫКОВ МАГА
        self.skill_tree = {
            3: [
                {"name": "Широкое заклинание", "desc": "+50 Радиус взрыва фаербола"},
                {"name": "Архимаг", "desc": "+15 Базового Урона"}
            ],
            5: [
                {"name": "Ускорение", "desc": "Перезарядка заклинаний быстрее в 2 раза"},
                {"name": "Контрзаклинание", "desc": "Атаки пробивают любую броню врагов"}
            ]
        }
        self.print_stats()

    def apply_skill(self, level, skill_name):
        super().apply_skill(level, skill_name)
        if skill_name == "Широкое заклинание": self.splash_radius += 50
        elif skill_name == "Архимаг": self.damage += 15
        elif skill_name == "Ускорение": self.cooldown_time *= 0.5
        elif skill_name == "Контрзаклинание": self.ignore_ac = True

    def shoot(self, enemy, bullets_list):
        ab = 999 if self.ignore_ac else self.attack_bonus
        bullets_list.append(SplashBullet(
            self.x, self.y, enemy, self.damage, ab, self.splash_radius, self
        ))