# core/wave_manager.py
import random
from entities.enemies import Goblin, Orc, Troll

class WaveManager:
    def __init__(self, map_path):
        self.map_path = map_path
        self.current_wave = 0 
        self.max_waves = 50
        
        # Вместо одной очереди - список активных независимых очередей (спавнеров)
        self.active_spawners = [] 
        self.spawn_delay = 1.2 
        
        self.game_started = False
        self.waiting_for_next = False
        self.auto_start_timer = 0.0

    def force_next_wave(self):
        """Создает новую волну и запускает её ПАРАЛЛЕЛЬНО с уже идущими"""
        if self.current_wave >= self.max_waves:
            return 0 
            
        self.current_wave += 1
        
        # Математика волн
        total_enemies = 5 + int(self.current_wave * 1.5)
        enemy_level = 1 + (self.current_wave // 4) 
        
        new_enemies = []
        for _ in range(total_enemies):
            if self.current_wave < 5:
                new_enemies.append(Goblin(self.map_path, enemy_level))
            elif self.current_wave < 15:
                cls = Orc if random.random() < 0.3 else Goblin
                new_enemies.append(cls(self.map_path, enemy_level))
            else:
                rand = random.random()
                if rand < 0.15: cls = Troll
                elif rand < 0.45: cls = Orc
                else: cls = Goblin
                new_enemies.append(cls(self.map_path, enemy_level))
                
        # ДОБАВЛЯЕМ НОВУЮ ВОЛНУ В СПИСОК АКТИВНЫХ (Она будет идти независимо от других)
        self.active_spawners.append({
            "enemies": new_enemies,
            "timer": 0.0
        })
        
        # Бонус за досрочный вызов
        bonus_gold = int(self.auto_start_timer) * 2 
        
        # Сбрасываем ожидание, так как волны снова идут
        self.waiting_for_next = False
        self.auto_start_timer = 0.0
        
        return bonus_gold

    def update(self, dt, active_enemies_list):
        if not self.game_started:
            return
            
        # 1. ОБНОВЛЯЕМ ВСЕ АКТИВНЫЕ ВОЛНЫ ОДНОВРЕМЕННО
        for spawner in self.active_spawners:
            spawner["timer"] += dt
            if spawner["timer"] >= self.spawn_delay:
                enemy = spawner["enemies"].pop(0)
                active_enemies_list.append(enemy)
                spawner["timer"] = 0.0 # Сбрасываем таймер только для ЭТОЙ волны
                
        # Очищаем те спавнеры, из которых вышли все мобы
        self.active_spawners = [s for s in self.active_spawners if len(s["enemies"]) > 0]
        
        # 2. ПРОВЕРКА: Если спавнеров больше нет, начинаем отсчет 15 секунд
        if len(self.active_spawners) == 0 and not self.waiting_for_next:
            self.waiting_for_next = True
            self.auto_start_timer = 15.0
                
        # 3. ОТСЧЕТ ДО СЛЕДУЮЩЕЙ ВОЛНЫ
        if self.waiting_for_next:
            self.auto_start_timer -= dt
            if self.auto_start_timer <= 0:
                self.force_next_wave()