# entities/projectiles.py
import pygame
import math
from core.assets import get_image
from core.dnd_math import roll_d20
from core.vfx import vfx
from settings import CELL_SIZE


class Bullet:
    def __init__(self, x, y, target, damage, attack_bonus, source_tower, damage_type="piercing"):
        self.x, self.y = float(x), float(y)
        self.target = target
        self.damage = damage
        self.attack_bonus = attack_bonus
        self.source_tower = source_tower
        self.damage_type = damage_type
        self.speed = 400
        self.alive = True
        self.image = get_image("arrow.png", (10, 10), (255, 200, 0), is_circle=True)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def apply_damage(self, enemy):
        # Высота даёт преимущество/помеху на бросок атаки.
        roll_1, roll_2 = roll_d20(), roll_d20()
        enemy_col = int(enemy.x // CELL_SIZE)
        enemy_row = int(enemy.y // CELL_SIZE)
        
        # Безопасная проверка выхода за пределы карты
        if 0 <= enemy_col < enemy.level_map.cols and 0 <= enemy_row < enemy.level_map.rows:
            enemy_elev = enemy.level_map.get_elevation(enemy_col, enemy_row)
        else:
            enemy_elev = 1
            
        tower_elev = self.source_tower.elevation
        
        if tower_elev > enemy_elev:
            attack_roll = max(roll_1, roll_2)
        elif tower_elev < enemy_elev:
            attack_roll = min(roll_1, roll_2)
        else:
            attack_roll = roll_1

        if attack_roll == 1:
            vfx.add_floating_text(enemy.x, enemy.y - 20, "Промах", False)
            return
            
        if attack_roll != 20 and not getattr(self.source_tower, "ignore_ac", False):
            if attack_roll + self.attack_bonus < enemy.ac:
                vfx.add_floating_text(enemy.x, enemy.y - 20, "Броня", False)
                return

        damage = int(self.damage * (2 if attack_roll == 20 else 1))
        was_alive = enemy.alive
        
        # Монстр обрабатывает урон своими способностями и статами
        actual_damage = enemy.take_damage(damage, self.damage_type)
        
        vfx.add_hit_effect(enemy.x, enemy.y)
        if actual_damage <= 0:
            vfx.add_floating_text(enemy.x, enemy.y - 20, "Блок/Уворот", False)
        else:
            vfx.add_floating_text(enemy.x, enemy.y - 20, actual_damage, attack_roll == 20)
            
        if was_alive and not enemy.alive:
            self.source_tower.gain_xp(enemy.max_hp)

    def update(self, dt, enemies):
        if not self.target.alive:
            self.alive = False
            return
        dx = self.target.rect.centerx - self.x
        dy = self.target.rect.centery - self.y
        distance = math.hypot(dx, dy)
        if distance < 10:
            self.apply_damage(self.target)
            self.alive = False
            return
        step = min(self.speed * dt, distance)
        self.x += (dx / distance) * step
        self.y += (dy / distance) * step
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
        shadow = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - self.rect.height // 4))
        surface.blit(self.image, self.rect)


class SplashBullet(Bullet):
    def __init__(self, x, y, target, damage, attack_bonus, splash_radius, source_tower, damage_type="fire"):
        # Магические взрывы по умолчанию наносят урон огнем
        super().__init__(x, y, target, damage, attack_bonus, source_tower, damage_type)
        self.splash_radius = splash_radius
        self.speed = 250
        self.image = get_image("fireball.png", (16, 16), (255, 100, 0), is_circle=True)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self, dt, enemies):
        if not self.target.alive:
            self.alive = False
            return
        dx = self.target.rect.centerx - self.x
        dy = self.target.rect.centery - self.y
        distance = math.hypot(dx, dy)
        if distance < 10:
            for enemy in enemies:
                if not enemy.alive:
                    continue
                gap = math.hypot(enemy.rect.centerx - self.target.rect.centerx,
                                enemy.rect.centery - self.target.rect.centery)
                if gap <= self.splash_radius:
                    self.apply_damage(enemy)
            self.alive = False
            return
        step = min(self.speed * dt, distance)
        self.x += (dx / distance) * step
        self.y += (dy / distance) * step
        self.rect.center = (int(self.x), int(self.y))
