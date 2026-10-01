# entities/enemies.py
import pygame
import math
from core.assets import get_image
from core.dnd_math import get_modifier
from settings import CELL_SIZE

class Enemy:
    def __init__(self, path_map, level, base_speed, base_hp, reward, sprite_name, size, fallback_color):
        self.level_map = path_map
        self.waypoints = path_map.waypoints
        self.current_wp_index = 0
        self.x, self.y = self.waypoints[0]
        
        self.level = level
        self.alive = True
        self.reached_end = False
        
        self.stats = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
        
        self.max_hp = base_hp + (level * 5)
        self.hp = self.max_hp
        self.base_speed = base_speed # Сохраняем БАЗОВУЮ скорость
        self.reward = reward + (level * 2)
        
        self.ac = 10 
        self.image = get_image(sprite_name, (size, size), fallback_color, is_circle=True)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def calculate_ac(self):
        self.ac = 10 + get_modifier(self.stats["DEX"])

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def update(self, dt):
        if not self.alive: return

        if self.current_wp_index >= len(self.waypoints) - 1:
            self.alive = False
            self.reached_end = True
            return

        col, row = int(self.x // CELL_SIZE), int(self.y // CELL_SIZE)
        current_surface = self.level_map.get_surface(col, row)
        current_elev = self.level_map.get_elevation(col, row)

        # 1. Влияние луж (Вода, Масло, Лед)
        speed_mult = 1.0
        if current_surface == "water": speed_mult = 0.6
        elif current_surface == "oil": speed_mult = 0.3
        elif current_surface == "ice": speed_mult = 1.6

        # 2. Влияние уклона (смотрим на 25 пикселей вперед)
        target_x, target_y = self.waypoints[self.current_wp_index + 1]
        dx, dy = target_x - self.x, target_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 0:
            next_col = int((self.x + (dx/dist) * 25) // CELL_SIZE)
            next_row = int((self.y + (dy/dist) * 25) // CELL_SIZE)
            next_elev = self.level_map.get_elevation(next_col, next_row)
            
            if next_elev > current_elev: speed_mult *= 0.5   # В гору - тяжело
            elif next_elev < current_elev: speed_mult *= 1.5 # С горы - легко

        actual_speed = self.base_speed * speed_mult

        if dist < 5:
            self.current_wp_index += 1
        else:
            self.x += (dx / dist) * actual_speed * dt
            self.y += (dy / dist) * actual_speed * dt
            self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
	
        surface.blit(self.image, self.rect)
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(surface, (50, 50, 50), (self.rect.centerx - 15, self.rect.top - 10, 30, 4))
        pygame.draw.rect(surface, (255, 0, 0), (self.rect.centerx - 15, self.rect.top - 10, max(0, 30 * hp_ratio), 4))

# Классы Goblin, Orc и Troll остаются БЕЗ ИЗМЕНЕНИЙ, кроме вызова super().__init__ 
# (они унаследуют новую логику). Для экономии места прикрепляю только Goblin. 
# Вы можете скопировать Orc и Troll из вашего старого файла.

class Goblin(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=120, base_hp=10, reward=10, sprite_name="goblin.png", size=24, fallback_color=(200, 50, 50))
        self.stats["DEX"] = 16 + (level // 2) 
        self.calculate_ac()
        
class Orc(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=70, base_hp=40, reward=20, sprite_name="orc.png", size=32, fallback_color=(50, 180, 50))
        self.stats["STR"] = 16 + (level // 2)
        self.stats["CON"] = 14 + (level // 2)
        self.ac = 12 + get_modifier(self.stats["DEX"])
        self.enraged = False
    def update(self, dt):
        if self.hp < self.max_hp / 2 and not self.enraged:
            self.base_speed *= 1.5
            self.enraged = True
        super().update(dt)

class Troll(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=45, base_hp=100, reward=45, sprite_name="troll.png", size=44, fallback_color=(80, 100, 150))
        self.stats["CON"] = 18 + (level // 2)
        self.stats["DEX"] = 8
        self.calculate_ac()
    def update(self, dt):
        if self.alive and 0 < self.hp < self.max_hp:
            self.hp += get_modifier(self.stats["CON"]) * 2 * dt
            if self.hp > self.max_hp: self.hp = self.max_hp
        super().update(dt)