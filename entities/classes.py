# entities/classes.py

def warrior_lvl_up(tower):
    tower.damage += 1
    tower.attack_bonus += 1

def rogue_lvl_up(tower):
    tower.damage += 1
    tower.cooldown_time = max(0.1, tower.cooldown_time - 0.05)

def mage_lvl_up(tower):
    tower.damage += 2
    tower.splash_radius += 5

CLASS_DATA = {
    "Warrior": {
        "name": "Воин",
        "sprite": "warrior.png",
        "color": (50, 100, 200),
        "on_level_up": warrior_lvl_up,
        "choices": {
            3: [
                {"name": "Тяжелый удар", "desc": "+8 Базового Урона", "apply": lambda t: setattr(t, 'damage', t.damage + 8)},
                {"name": "Шквал ударов", "desc": "-30% Перезарядка", "apply": lambda t: setattr(t, 'cooldown_time', t.cooldown_time * 0.7)},
            ],
            5: [
                {"name": "Двойной удар", "desc": "Выпускает 2 снаряда за раз", "apply": lambda t: t.skills.append("double_strike")},
                {"name": "Мастер Оружия", "desc": "+5 Меткость (Игнор брони)", "apply": lambda t: setattr(t, 'attack_bonus', t.attack_bonus + 5)},
            ]
        }
    },
    "Rogue": {
        "name": "Плут",
        "sprite": "rogue.png",
        "color": (200, 200, 50),
        "on_level_up": rogue_lvl_up,
        "choices": {
            3: [
                {"name": "Любимец фортуны", "desc": "+20% Шанс крита", "apply": lambda t: setattr(t, 'crit_chance', t.crit_chance + 20)},
                {"name": "Орлиный глаз", "desc": "+50 Радиус атаки", "apply": lambda t: setattr(t, 'base_range', t.base_range + 50)},
            ],
            5: [
                {"name": "Ассасин", "desc": "Крит наносит x5 урона", "apply": lambda t: setattr(t, 'crit_multiplier', 5)},
                {"name": "Град стрел", "desc": "Выпускает 3 стрелы веером", "apply": lambda t: t.skills.append("arrow_rain")},
            ]
        }
    },
    "Mage": {
        "name": "Маг",
        "sprite": "mage.png",
        "color": (150, 50, 200),
        "on_level_up": mage_lvl_up,
        "choices": {
            3: [
                {"name": "Широкое заклинание", "desc": "+50 Радиус взрыва", "apply": lambda t: setattr(t, 'splash_radius', t.splash_radius + 50)},
                {"name": "Архимаг", "desc": "+15 Урона", "apply": lambda t: setattr(t, 'damage', t.damage + 15)},
            ],
            5: [
                {"name": "Ускорение", "desc": "Перезарядка x2 быстрее", "apply": lambda t: setattr(t, 'cooldown_time', t.cooldown_time * 0.5)},
                {"name": "Контрзаклинание", "desc": "Игнорирует броню", "apply": lambda t: t.skills.append("ignore_ac")},
            ]
        }
    }
}
