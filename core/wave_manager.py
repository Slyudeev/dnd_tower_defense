# core/wave_manager.py
import random
from entities.enemies import Goblin, Orc, Troll, Skeleton, Golem


class WaveManager:
    def __init__(self, map_path):
        self.map_path = map_path
        self.current_wave = 0
        self.max_waves = 50
        self.active_spawners = []
        self.spawn_delay = 1.2
        self.game_started = False
        self.waiting_for_next = False
        self.auto_start_timer = 0.0

    def force_next_wave(self):
        """Start the next wave. Returns any early-call gold bonus."""
        if self.current_wave >= self.max_waves:
            return 0
        self.current_wave += 1
        total_enemies = 5 + int(self.current_wave * 1.5)
        enemy_level = 1 + self.current_wave // 4
        wave_enemies = []
        for _ in range(total_enemies):
            if self.current_wave < 4:
                kind = Goblin
            elif self.current_wave < 8:
                kind = Skeleton if random.random() < 0.4 else Goblin
            elif self.current_wave < 15:
                roll = random.random()
                kind = Orc if roll < 0.4 else Skeleton if roll < 0.7 else Goblin
            else:
                roll = random.random()
                kind = Golem if roll < 0.1 else Troll if roll < 0.25 else Orc if roll < 0.6 else Skeleton
            wave_enemies.append(kind(self.map_path, enemy_level))

        self.active_spawners.append({"enemies": wave_enemies, "timer": 0.0})
        bonus_gold = int(self.auto_start_timer) * 2 if self.waiting_for_next else 0
        self.waiting_for_next = False
        self.auto_start_timer = 0.0
        self.game_started = True
        return bonus_gold

    def update(self, dt, active_enemies_list):
        if not self.game_started:
            return

        # Spawn each wave queue independently; a large dt can spawn multiple mobs
        # without losing the elapsed time.
        for spawner in self.active_spawners:
            spawner["timer"] += dt
            while spawner["timer"] >= self.spawn_delay and spawner["enemies"]:
                active_enemies_list.append(spawner["enemies"].pop(0))
                spawner["timer"] -= self.spawn_delay

        self.active_spawners = [s for s in self.active_spawners if s["enemies"]]
        living_enemies = any(enemy.alive for enemy in active_enemies_list)

        # The inter-wave countdown begins only after every queued and living
        # enemy is gone. Actual launch is controlled by the auto-wave toggle in
        # main.py or by the player's manual Space input.
        if not self.active_spawners and not living_enemies:
            if not self.waiting_for_next and self.current_wave < self.max_waves:
                self.waiting_for_next = True
                self.auto_start_timer = 15.0
            elif self.waiting_for_next:
                self.auto_start_timer = max(0.0, self.auto_start_timer - dt)
        else:
            self.waiting_for_next = False
            self.auto_start_timer = 0.0
