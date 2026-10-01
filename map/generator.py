# map/generator.py
import math
import random
import pygame
from settings import WIDTH, HEIGHT, CELL_SIZE, DARK_BG, LOW_BG, HIGH_BG, ROAD_COLOR, WATER_COLOR, OIL_COLOR, ICE_COLOR
from core.assets import get_image

class MapPath:
    def __init__(self):
        self.cols = WIDTH // CELL_SIZE
        self.rows = HEIGHT // CELL_SIZE
        self.grid_elevation = {} # Высота: 0 (Низина), 1 (Норма), 2 (Возвышенность)
        self.grid_surface = {}   # Поверхность: normal, water, oil, ice
        
        # Загружаем тайлы (Дорога тут больше не нужна, мы рисуем ее линией)
        self.tiles = {
            "normal": get_image("grass.png", (CELL_SIZE, CELL_SIZE), (60, 150, 60)),
            "high": get_image("hill.png", (CELL_SIZE, CELL_SIZE), (120, 120, 120)),
            "low": get_image("dirt.png", (CELL_SIZE, CELL_SIZE), (80, 60, 40))
        }
        
        self.puddles = {
            "water": get_image("water.png", (36, 36), WATER_COLOR, is_circle=True),
            "oil": get_image("oil.png", (36, 36), OIL_COLOR, is_circle=True),
            "ice": get_image("ice.png", (36, 36), ICE_COLOR, is_circle=True)
        }
        
        self._generate_terrain()
        self.waypoints = self._generate_random_path()
        self.road_cells = set()
        self._calculate_road_cells()
        self._sprinkle_surfaces()

    def _generate_terrain(self):
        for c in range(self.cols):
            for r in range(self.rows):
                self.grid_elevation[(c, r)] = 1
                self.grid_surface[(c, r)] = "normal"

        for _ in range(5): 
            cx, cy = random.randint(0, self.cols-1), random.randint(0, self.rows-1)
            for c in range(max(0, cx-2), min(self.cols, cx+3)):
                for r in range(max(0, cy-2), min(self.rows, cy+3)):
                    if random.random() < 0.7: self.grid_elevation[(c, r)] = 2
                    
        for _ in range(4): 
            cx, cy = random.randint(0, self.cols-1), random.randint(0, self.rows-1)
            for c in range(max(0, cx-2), min(self.cols, cx+3)):
                for r in range(max(0, cy-2), min(self.rows, cy+3)):
                    if random.random() < 0.7: self.grid_elevation[(c, r)] = 0

    def _generate_random_path(self):
        waypoints = []
        start_row = random.randint(1, self.rows - 2)
        y_curr = start_row * CELL_SIZE + (CELL_SIZE // 2)
        x_curr = 0
        waypoints.append((x_curr, y_curr))
        
        num_segments = random.randint(3, 5)
        col_steps = sorted(random.sample(range(2, self.cols - 2), num_segments - 1))
        
        for col in col_steps:
            next_x = col * CELL_SIZE + (CELL_SIZE // 2)
            waypoints.append((next_x, y_curr)) 
            valid_rows = [r for r in range(1, self.rows - 1) if abs(r - (y_curr // CELL_SIZE)) >= 2]
            if valid_rows:
                y_curr = random.choice(valid_rows) * CELL_SIZE + (CELL_SIZE // 2)
                waypoints.append((next_x, y_curr)) 
                
        waypoints.append((WIDTH, y_curr))
        return waypoints

    def _calculate_road_cells(self):
        for i in range(len(self.waypoints) - 1):
            x1, y1 = self.waypoints[i]
            x2, y2 = self.waypoints[i+1]
            dist = math.hypot(x2 - x1, y2 - y1)
            if dist == 0: continue
            steps = int(dist)
            for step in range(steps):
                px = x1 + (x2 - x1) * (step / steps)
                py = y1 + (y2 - y1) * (step / steps)
                self.road_cells.add((int(px) // CELL_SIZE, int(py) // CELL_SIZE))

    def _sprinkle_surfaces(self):
        for cell in self.road_cells:
            rand = random.random()
            if rand < 0.10: self.grid_surface[cell] = "water"
            elif rand < 0.18: self.grid_surface[cell] = "oil"
            elif rand < 0.28: self.grid_surface[cell] = "ice"

    def get_elevation(self, col, row):
        return self.grid_elevation.get((col, row), 1)

    def get_surface(self, col, row):
        return self.grid_surface.get((col, row), "normal")

    def draw(self, surface):
        # 1. Рисуем ландшафт
        for c in range(self.cols):
            for r in range(self.rows):
                elev = self.grid_elevation[(c, r)]
                
                # Выбираем картинку
                if elev == 0: tile = self.tiles["low"]
                elif elev == 2: tile = self.tiles["high"]
                else: tile = self.tiles["normal"]
                    
                x, y = c * CELL_SIZE, r * CELL_SIZE
                surface.blit(tile, (x, y))
                
                # === МАГИЯ КОДА ДЛЯ ВЫСОТЫ ===
                if elev == 2:
                    # Делаем скалу светлее (ближе к солнцу)
                    highlight = pygame.Surface((CELL_SIZE, CELL_SIZE))
                    highlight.fill((255, 255, 255))
                    highlight.set_alpha(30)
                    surface.blit(highlight, (x, y))
                    
                    # Рисуем ТЕНЬ (обрыв) снизу, если под скалой обычная земля
                    if self.get_elevation(c, r+1) < 2:
                        shadow = pygame.Surface((CELL_SIZE, 10))
                        shadow.fill((0, 0, 0))
                        shadow.set_alpha(150)
                        surface.blit(shadow, (x, y + CELL_SIZE - 10))
                        
                elif elev == 0:
                    # Делаем низину темнее (в тени)
                    darken = pygame.Surface((CELL_SIZE, CELL_SIZE))
                    darken.fill((0, 0, 0))
                    darken.set_alpha(100) # Сильно затемняем грязь!
                    surface.blit(darken, (x, y))

        # 2. РИСУЕМ ДОРОГУ ПЛАВНОЙ ЛИНИЕЙ ПОВЕРХ ТАЙЛОВ
        # Сначала рисуем толстую черную обводку (чтобы отделить от грязи и скал)
        pygame.draw.lines(surface, (40, 30, 20), False, self.waypoints, 48)
        # Затем рисуем саму дорогу светлым цветом внутри обводки
        pygame.draw.lines(surface, (160, 140, 110), False, self.waypoints, 40)

        # 3. Рисуем лужи
        for cell in self.road_cells:
            surf = self.grid_surface[cell]
            if surf != "normal":
                puddle_img = self.puddles[surf]
                cx = cell[0] * CELL_SIZE + CELL_SIZE // 2
                cy = cell[1] * CELL_SIZE + CELL_SIZE // 2
                rect = puddle_img.get_rect(center=(cx, cy))
                surface.blit(puddle_img, rect)