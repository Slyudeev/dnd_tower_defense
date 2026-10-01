# core/dnd_math.py
import random
import math

def roll_4d6_drop_lowest(bonus=0):
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.remove(min(rolls))
    return sum(rolls) + bonus

def get_modifier(stat):
    return math.floor((stat - 10) / 2)

def roll_d20():
    return random.randint(1, 20)