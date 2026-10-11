# entities/class_progression.py
"""Gameplay definitions for D&D-inspired multiclass tower classes.

This is a lightweight game adaptation, not a rules-complete implementation of D&D.
Class levels unlock their features automatically; every character level is assigned
by the player to exactly one class.
"""

CLASSES = {
    "fighter": {
        "name": "Воин", "stat": "STR", "range": 8, "damage": 2.0,
        "cooldown": -0.035, "attack": 1.0, "style": "martial",
        "features": {2: "Боевой стиль: +10% урона", 5: "Дополнительная атака"},
    },
    "rogue": {
        "name": "Плут", "stat": "DEX", "range": 15, "damage": 1.0,
        "cooldown": -0.07, "attack": 1.0, "style": "precision",
        "features": {2: "Скрытая атака: +25% крит. урона", 5: "Смертельный критический удар"},
    },
    "wizard": {
        "name": "Волшебник", "stat": "INT", "range": 35, "damage": 4.0,
        "cooldown": 0.04, "attack": 1.0, "style": "magic",
        "features": {2: "Магический урон по области", 5: "Большой радиус взрыва"},
    },
    "cleric": {
        "name": "Жрец", "stat": "WIS", "range": 20, "damage": 2.5,
        "cooldown": 0.02, "attack": 1.0, "style": "magic",
        "features": {2: "Священная магия по области", 5: "Усиленное заклинание"},
    },
    "ranger": {
        "name": "Следопыт", "stat": "DEX", "range": 30, "damage": 2.0,
        "cooldown": -0.04, "attack": 1.0, "style": "precision",
        "features": {2: "Меткий выстрел", 5: "Залп по цели"},
    },
    "paladin": {
        "name": "Паладин", "stat": "CHA", "range": 15, "damage": 3.0,
        "cooldown": 0.02, "attack": 1.0, "style": "holy",
        "features": {2: "Божественная кара", 5: "Взрыв священной энергии"},
    },
    "barbarian": {
        "name": "Варвар", "stat": "STR", "range": 0, "damage": 4.0,
        "cooldown": 0.025, "attack": 0.5, "style": "martial",
        "features": {2: "Ярость: +20% урона", 5: "Сокрушительный удар"},
    },
    "bard": {
        "name": "Бард", "stat": "CHA", "range": 25, "damage": 1.5,
        "cooldown": -0.025, "attack": 1.0, "style": "magic",
        "features": {2: "Вдохновляющая магия", 5: "Мощный аккорд"},
    },
    "druid": {
        "name": "Друид", "stat": "WIS", "range": 25, "damage": 3.0,
        "cooldown": 0.025, "attack": 1.0, "style": "magic",
        "features": {2: "Природная магия по области", 5: "Гнев природы"},
    },
    "monk": {
        "name": "Монах", "stat": "DEX", "range": 5, "damage": 1.5,
        "cooldown": -0.09, "attack": 0.5, "style": "martial",
        "features": {2: "Шквал ударов", 5: "Пять шагов ладони"},
    },
    "sorcerer": {
        "name": "Чародей", "stat": "CHA", "range": 35, "damage": 4.0,
        "cooldown": 0.03, "attack": 1.0, "style": "magic",
        "features": {2: "Метамагия: +15% урона", 5: "Усиленное заклинание"},
    },
    "warlock": {
        "name": "Колдун", "stat": "CHA", "range": 30, "damage": 3.5,
        "cooldown": -0.015, "attack": 1.0, "style": "magic",
        "features": {2: "Мистический заряд", 5: "Улучшенный мистический заряд"},
    },
}

CLASS_ORDER = tuple(CLASSES.keys())
MAX_CHARACTER_LEVEL = 20


def get_class_name(class_id):
    return CLASSES[class_id]["name"]


def get_unlocked_features(class_levels):
    """Return (class_id, feature_level, feature_text) tuples."""
    result = []
    for class_id, level in class_levels.items():
        for feature_level, text in CLASSES[class_id]["features"].items():
            if level >= feature_level:
                result.append((class_id, feature_level, text))
    return result
