# entities/projectiles.py
import pygame
import math
import random
from core.assets import get_image
from core.dnd_math import roll_d20
from core.vfx import vfx

class Bullet:
    def __init__(self, x, y, target, source_tower):
        self.x, self.y = x, y
        self.target = target
        self.source_tower = source_tower 
        self.speed = 400
        self.alive = True
        
        # Считываем статы Героя в момент выстрела
        self.damage = source_tower.damage
        self.attack_bonus = 999 if "ignore_ac" in source_tower.skills else source_tower.attack_bonus
        self.crit_chance = source_tower.crit_chance
        self.crit_multiplier = source_tower.crit_multiplier
        
        self.image = get_image("arrow.png", (10, 10), (255, 200, 0), is_circle=True)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def apply_damage(self, enemy):
        roll_1 = roll_d20()
        roll_2 = roll_d20()
        
        enemy_col, enemy_row = int(enemy.x // 50), int(enemy.y // 50)
        enemy_elev = enemy.level_map.get_elevation(enemy_col, enemy_row)
        tower_elev = self.source_tower.elevation
        
        if tower_elev > enemy_elev: final_roll = max(roll_1, roll_2)
        elif tower_elev < enemy_elev: final_roll = min(roll_1, roll_2)
        else: final_roll = roll_1

        damage_dealt = 0
        is_crit = False
        roll_crit = random.randint(1, 100)
        
        # Крит от D20 ИЛИ от шанса крита Плута
        if final_roll == 20 or roll_crit <= self.crit_chance:
            damage_dealt = self.damage * self.crit_multiplier
            is_crit = True
        elif final_roll == 1: 
            pass
        elif final_roll + self.attack_bonus >= enemy.ac: 
            damage_dealt = self.damage
            
        if damage_dealt > 0:
            was_alive = enemy.alive 
            enemy.take_damage(damage_dealt)
            vfx.add_hit_effect(enemy.x, enemy.y)
            vfx.add_floating_text(enemy.x, enemy.y - 20, damage_dealt, is_crit)
            
            if was_alive and not enemy.alive:
                self.source_tower.gain_xp(enemy.max_hp)

    def update(self, dt, enemies):
        if not self.target.alive:
            self.alive = False
            return
        dx, dy = self.target.rect.centerx - self.x, self.target.rect.centery - self.y
        dist = math.hypot(dx, dy)
        if dist < 10:
            self.apply_damage(self.target)
            self.alive = False
        else:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
            self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
        shadow = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - self.rect.height // 4))


class SplashBullet(Bullet):
    def __init__(self, x, y, target, source_tower):
        super().__init__(x, y, target, source_tower)
        self.splash_radius = max(30, source_tower.splash_radius)
        self.speed = 250
        
        self.image = get_image("fireball.png", (16, 16), (255, 100, 0), is_circle=True)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self, dt, enemies):
        if not self.target.alive:
            self.alive = False
            return
        dx, dy = self.target.rect.centerx - self.x, self.target.rect.centery - self.y
        dist = math.hypot(dx, dy)
        if dist < 10:
            for enemy in enemies:
                if not enemy.alive: continue
                d = math.hypot(enemy.rect.centerx - self.target.rect.centerx, enemy.rect.centery - self.target.rect.centery)
                if d <= self.splash_radius:
                    self.apply_damage(enemy)
            self.alive = False
        else:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
            self.rect.center = (int(self.x), int(self.y))
