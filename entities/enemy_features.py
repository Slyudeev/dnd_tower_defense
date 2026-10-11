# entities/enemy_features.py
import random

class Feature:
    def __init__(self, level=1):
        self.level = level

    def on_spawn(self, enemy):
        pass

    def on_update(self, enemy, dt):
        pass

    def on_take_damage(self, enemy, damage, damage_type):
        return damage


class Regeneration(Feature):
    def on_update(self, enemy, dt):
        if enemy.alive and 0 < enemy.hp < enemy.max_hp:
            enemy.hp += (2.0 * self.level) * dt
            if enemy.hp > enemy.max_hp:
                enemy.hp = enemy.max_hp


class Evasion(Feature):
    def on_take_damage(self, enemy, damage, damage_type):
        # Базовый шанс 10% + 3% за уровень способности
        chance = 10 + self.level * 3
        if random.randint(1, 100) <= chance:
            return 0  # Уклонился
        return damage


class DamageReduction(Feature):
    def on_take_damage(self, enemy, damage, damage_type):
        # Снижает входящий урон на (уровень + 1), но минимум до 1
        reduction = 1 + self.level
        return max(1, damage - reduction) if damage > 0 else 0


class UndeadFortitude(Feature):
    def on_take_damage(self, enemy, damage, damage_type):
        if damage_type == "radiant":
            return damage  # Не работает против radiant (света)

        if enemy.hp - damage <= 0:
            # Шанс выжить с 1 ХП при смертельном ударе
            if random.randint(1, 100) <= 20 + self.level * 10:
                enemy.hp = 1
                return 0  # Урон поглощен
        return damage

class Frenzy(Feature):
    def __init__(self, level=1):
        super().__init__(level)
        self.triggered = False

    def on_update(self, enemy, dt):
        if not self.triggered and enemy.hp < enemy.max_hp / 2:
            enemy.base_speed *= (1.2 + 0.1 * self.level)
            self.triggered = True

class MagicResistance(Feature):
    def on_take_damage(self, enemy, damage, damage_type):
        # Магические типы урона
        if damage_type in ["fire", "cold", "lightning", "radiant", "necrotic", "force", "psychic", "poison"]:
            # Снижает магический урон
            return max(1, int(damage * (1.0 - 0.1 * self.level)))
        return damage
