# entities/enemies.py
import pygame
import math
from core.assets import get_image
from core.dnd_math import get_modifier
from settings import CELL_SIZE
from entities.enemy_features import Regeneration, Evasion, DamageReduction, Frenzy, MagicResistance, UndeadFortitude

class Enemy:
    def __init__(self, path_map, level, base_speed, base_hp, reward, sprite_name, size, fallback_color):
        self.level_map = path_map
        self.waypoints = path_map.waypoints
        self.current_wp_index = 0
        self.x, self.y = self.waypoints[0]

        self.level = level
        self.alive = True
        self.reached_end = False

        # D&D Статы (по умолчанию 10)
        self.stats = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}

        # D&D Тэги (humanoid, undead, construct и т.д.)
        self.tags = set()

        # Сопротивления и уязвимости к типам урона
        # Типы: slashing, piercing, bludgeoning, fire, cold, lightning, poison, radiant, necrotic, force, psychic
        self.resistances = set()
        self.immunities = set()
        self.vulnerabilities = set()

        # Способности (из enemy_features.py)
        self.features = []

        self.max_hp = base_hp + (level * 5)
        self.hp = self.max_hp
        self.base_speed = base_speed
        self.reward = reward + (level * 2)
        self.natural_armor = 0

        self.ac = 10 
        self.image = get_image(sprite_name, (size, size), fallback_color, is_circle=True)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def setup_stats(self):
        """Вызывается в наследниках после настройки статов для перерасчета."""
        # Модификатор телосложения влияет на ХП
        con_mod = get_modifier(self.stats["CON"])
        self.max_hp += con_mod * self.level
        self.hp = self.max_hp
        self.calculate_ac()

        for feat in self.features:
            feat.on_spawn(self)

    def calculate_ac(self):
        self.ac = 10 + get_modifier(self.stats["DEX"]) + self.natural_armor

    def take_damage(self, amount, damage_type="bludgeoning"):
        """Наносит урон с учетом способностей, сопротивлений и тэгов. Возвращает фактический урон."""
        if amount <= 0 or not self.alive:
            return 0

        # 1. Способности (могут дать уворот или снижение урона)
        for feat in self.features:
            amount = feat.on_take_damage(self, amount, damage_type)

        if amount <= 0:
            return 0 # Полностью избежал урона

        # 2. Иммунитеты
        if damage_type in self.immunities:
            return 0

        # 3. Сопротивления (урон делится на 2)
        if damage_type in self.resistances:
            amount = max(1, amount // 2)

        # 4. Уязвимости (урон умножается на 2)
        if damage_type in self.vulnerabilities:
            amount *= 2

        actual_damage = int(amount)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.alive = False

        return actual_damage

    def update(self, dt):
        if not self.alive: return

        for feat in self.features:
            feat.on_update(self, dt)

        if self.current_wp_index >= len(self.waypoints) - 1:
            self.alive = False
            self.reached_end = True
            return

        col, row = int(self.x // CELL_SIZE), int(self.y // CELL_SIZE)
        current_surface = self.level_map.get_surface(col, row)
        current_elev = self.level_map.get_elevation(col, row)

        # 1. Влияние луж
        speed_mult = 1.0
        if current_surface == "water": speed_mult = 0.6
        elif current_surface == "oil": speed_mult = 0.3
        elif current_surface == "ice": speed_mult = 1.6

        # 2. Влияние уклона
        target_x, target_y = self.waypoints[self.current_wp_index + 1]
        dx, dy = target_x - self.x, target_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 0:
            next_col = int((self.x + (dx/dist) * 25) // CELL_SIZE)
            next_row = int((self.y + (dy/dist) * 25) // CELL_SIZE)
            if 0 <= next_col < self.level_map.cols and 0 <= next_row < self.level_map.rows:
                next_elev = self.level_map.get_elevation(next_col, next_row)
                if next_elev > current_elev: speed_mult *= 0.5
                elif next_elev < current_elev: speed_mult *= 1.5

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
        # Цвет полоски ХП зависит от типа монстра (например нежить - фиолетовая, остальные красные)
        bar_color = (150, 0, 255) if "undead" in self.tags else ((0, 200, 255) if "construct" in self.tags else (255, 0, 0))
        pygame.draw.rect(surface, bar_color, (self.rect.centerx - 15, self.rect.top - 10, max(0, 30 * hp_ratio), 4))


# ================= БЕСТИАРИЙ =================

class Goblin(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=120, base_hp=10, reward=10, sprite_name="goblin.png", size=24, fallback_color=(200, 50, 50))
        self.tags = {"humanoid", "goblinoid"}
        self.stats.update({"STR": 8, "DEX": 16 + (level//2), "CON": 10, "INT": 10, "WIS": 8, "CHA": 8})

        # Гоблины ловкие, имеют шанс уворота
        self.features.append(Evasion(level=1 + level//5))
        self.setup_stats()

class Orc(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=70, base_hp=40, reward=20, sprite_name="orc.png", size=32, fallback_color=(50, 180, 50))
        self.tags = {"humanoid", "orc"}
        self.stats.update({"STR": 16 + (level//2), "DEX": 12, "CON": 16 + (level//2), "INT": 8, "WIS": 11, "CHA": 10})
        self.natural_armor = 2

        # Орки впадают в ярость при низком ХП
        self.features.append(Frenzy(level=1 + level//4))
        self.setup_stats()

class Troll(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=45, base_hp=80, reward=45, sprite_name="troll.png", size=44, fallback_color=(80, 100, 150))
        self.tags = {"giant"}
        self.stats.update({"STR": 18 + (level//2), "DEX": 8, "CON": 20 + (level//2), "INT": 7, "WIS": 9, "CHA": 7})
        self.natural_armor = 4

        # Классика D&D: уязвимость к огню, регенерация
        self.vulnerabilities.add("fire")
        self.features.append(Regeneration(level=max(1, level // 2)))
        self.setup_stats()

class Skeleton(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=80, base_hp=15, reward=12, sprite_name="skeleton.png", size=24, fallback_color=(220, 220, 220))
        self.tags = {"undead"}
        self.stats.update({"STR": 10, "DEX": 14 + (level//3), "CON": 15, "INT": 6, "WIS": 8, "CHA": 5})

        # Нежить: иммунитет к яду, уязвимость к дробящему и сияющему урону
        self.immunities.add("poison")
        self.vulnerabilities.update({"bludgeoning", "radiant"})
        self.resistances.add("piercing") # Стрелы плохо работают по костям

        self.features.append(UndeadFortitude(level=level))
        self.setup_stats()

class Golem(Enemy):
    def __init__(self, path_map, level):
        super().__init__(path_map, level, base_speed=40, base_hp=60, reward=30, sprite_name="golem.png", size=40, fallback_color=(150, 100, 50))
        self.tags = {"construct"}
        self.stats.update({"STR": 20 + (level//2), "DEX": 8, "CON": 20, "INT": 3, "WIS": 10, "CHA": 1})
        self.natural_armor = 6 + (level // 3)

        self.immunities.update({"poison", "psychic"})
        self.resistances.update({"slashing", "piercing"}) # Прочный как камень

        self.features.append(DamageReduction(level=level // 2 + 1))
        self.features.append(MagicResistance(level=1 + level//3))
        self.setup_stats()
