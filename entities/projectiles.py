# entities/projectiles.py
import pygame
import math
from core.assets import get_image
from core.dnd_math import roll_d20
from core.vfx import vfx # <--- ИМПОРТ МЕНЕДЖЕРА ЭФФЕКТОВ

class Bullet:
    def __init__(self, x, y, target, damage, attack_bonus, source_tower):
        self.x = x
        self.y = y
        self.target = target
        self.damage = damage
        self.attack_bonus = attack_bonus
        self.source_tower = source_tower 
        self.speed = 400
        self.alive = True
        
        self.image = get_image("arrow.png", (10, 10), (255, 200, 0), is_circle=True)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def apply_damage(self, enemy):
        # Механика Преимущества и Помехи от высоты
        roll_1 = roll_d20()
        roll_2 = roll_d20()
        
        enemy_col = int(enemy.x // 50)
        enemy_row = int(enemy.y // 50)
        enemy_elev = enemy.level_map.get_elevation(enemy_col, enemy_row)
        tower_elev = self.source_tower.elevation
        
        if tower_elev > enemy_elev:
            final_roll = max(roll_1, roll_2) # Преимущество
        elif tower_elev < enemy_elev:
            final_roll = min(roll_1, roll_2) # Помеха
        else:
            final_roll = roll_1

        damage_dealt = 0
        is_crit = False
        
        if final_roll == 20: 
            damage_dealt = self.damage * 2
            is_crit = True
        elif final_roll == 1: 
            pass
        elif final_roll + self.attack_bonus >= enemy.ac: 
            damage_dealt = self.damage
            
        # Если пробили броню и нанесли урон
        if damage_dealt > 0:
            was_alive = enemy.alive 
            enemy.take_damage(damage_dealt)
            
            # --- ВИЗУАЛЬНЫЕ ЭФФЕКТЫ ---
            vfx.add_hit_effect(enemy.x, enemy.y) # Искры/кровь
            vfx.add_floating_text(enemy.x, enemy.y - 20, damage_dealt, is_crit) # Всплывающий урон
            
            # Выдача опыта за ластхит
            if was_alive and not enemy.alive:
                self.source_tower.gain_xp(enemy.max_hp)

    def update(self, dt, enemies):
        if not self.target.alive:
            self.alive = False
            return

        dx = self.target.rect.centerx - self.x
        dy = self.target.rect.centery - self.y
        dist = math.hypot(dx, dy)

        if dist < 10:
            self.apply_damage(self.target)
            self.alive = False
        else:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
            self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
        # Отрисовка тени
        shadow = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - self.rect.height // 4))


class SplashBullet(Bullet):
    def __init__(self, x, y, target, damage, attack_bonus, splash_radius, source_tower):
        super().__init__(x, y, target, damage, attack_bonus, source_tower)
        self.splash_radius = splash_radius
        self.speed = 250
        
        self.image = get_image("fireball.png", (16, 16), (255, 100, 0), is_circle=True)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self, dt, enemies):
        if not self.target.alive:
            self.alive = False
            return

        dx = self.target.rect.centerx - self.x
        dy = self.target.rect.centery - self.y
        dist = math.hypot(dx, dy)

        if dist < 10:
            for enemy in enemies:
                if not enemy.alive: 
                    continue
                d = math.hypot(enemy.rect.centerx - self.target.rect.centerx, enemy.rect.centery - self.target.rect.centery)
                if d <= self.splash_radius:
                    self.apply_damage(enemy) # Автоматически создаст эффекты для каждого задетого врага!
            self.alive = False
        else:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
            self.rect.center = (int(self.x), int(self.y))