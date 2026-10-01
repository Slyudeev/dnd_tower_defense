# main.py
import pygame
from settings import WIDTH, HEIGHT, FPS, DARK_BG, ROAD_COLOR, CELL_SIZE, GRID_COLOR
from map.generator import MapPath
from entities.towers import WarriorTower, RogueTower, MageTower
from core.wave_manager import WaveManager 
from core.vfx import vfx # <--- ИМПОРТ МЕНЕДЖЕРА ЭФФЕКТОВ

pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("D&D Tower Defense")
clock = pygame.time.Clock()

ui_font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 100)

def draw_grid(surface):
    # Создаем прозрачную поверхность для сетки
    grid_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    # Цвет сетки: белый, но почти прозрачный (альфа 30 из 255)
    grid_color = (255, 255, 255, 30) 
    
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(grid_surf, grid_color, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(grid_surf, grid_color, (0, y), (WIDTH, y))
        
    surface.blit(grid_surf, (0, 0))

def main():
    running = True
    level_map = MapPath()
    wave_manager = WaveManager(level_map)
    
    enemies = []
    towers = []
    bullets = []
    occupied_cells = set()
    
    match_gold = 150 
    lives = 20
    
    game_over = False
    victory = False 
    
    selected_tower_class = WarriorTower
    MAX_TOWERS = 8
    upgrading_tower = None

    while running:
        dt = clock.tick(FPS) / 1000.0
        current_cost = 50 + (len(towers) * 50)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                if (game_over or victory) and event.key == pygame.K_r:
                    main()
                    return
                if not upgrading_tower:
                    if event.key == pygame.K_SPACE and not game_over and not victory:
                        if not wave_manager.game_started:
                            wave_manager.game_started = True
                            wave_manager.force_next_wave()
                        else:
                            if wave_manager.current_wave < wave_manager.max_waves:
                                match_gold += wave_manager.force_next_wave()
                        
                    if event.key == pygame.K_1: selected_tower_class = WarriorTower
                    if event.key == pygame.K_2: selected_tower_class = RogueTower
                    if event.key == pygame.K_3: selected_tower_class = MageTower

            if event.type == pygame.MOUSEBUTTONDOWN and not game_over and not victory:
                mx, my = pygame.mouse.get_pos()
                
                # МЕНЮ ВЫБОРА НАВЫКОВ
                if upgrading_tower:
                    lvl = upgrading_tower.pending_upgrades[0]
                    choices = upgrading_tower.skill_tree[lvl]
                    
                    panel_y = HEIGHT // 2 - (len(choices) * 40)
                    for i, choice in enumerate(choices):
                        rect = pygame.Rect(WIDTH//2 - 200, panel_y + i * 90, 400, 70)
                        if rect.collidepoint(mx, my):
                            upgrading_tower.apply_skill(lvl, choice["name"])
                            upgrading_tower.pending_upgrades.pop(0)
                            if not upgrading_tower.pending_upgrades:
                                upgrading_tower = None
                            break
                # ОБЫЧНАЯ ИГРА
                else:
                    clicked_on_tower = None
                    for t in towers:
                        if t.rect.collidepoint(mx, my):
                            clicked_on_tower = t
                            break
                            
                    if clicked_on_tower:
                        if len(clicked_on_tower.pending_upgrades) > 0:
                            upgrading_tower = clicked_on_tower
                    else:
                        col, row = mx // CELL_SIZE, my // CELL_SIZE
                        cell = (col, row)
                        if len(towers) < MAX_TOWERS and cell not in occupied_cells and cell not in level_map.road_cells:
                            if match_gold >= current_cost:
                                center_x = col * CELL_SIZE + CELL_SIZE // 2
                                center_y = row * CELL_SIZE + CELL_SIZE // 2
                                towers.append(selected_tower_class(center_x, center_y, level_map))
                                match_gold -= current_cost
                                occupied_cells.add(cell)

        # === ЛОГИКА ИГРЫ (ОБНОВЛЕНИЕ) ===
        if not game_over and not victory and not upgrading_tower:
            wave_manager.update(dt, enemies)
            vfx.update(dt) # <--- ОБНОВЛЯЕМ ЭФФЕКТЫ

            for tower in towers: tower.update(dt, enemies, bullets)
            for bullet in bullets: bullet.update(dt, enemies)
            for enemy in enemies: enemy.update(dt)

            for enemy in enemies:
                if not enemy.alive:
                    if enemy.hp <= 0: match_gold += enemy.reward
                    elif enemy.reached_end:
                        lives -= 1
                        if lives <= 0: game_over = True

            bullets = [b for b in bullets if b.alive]
            enemies = [e for e in enemies if e.alive]

            if wave_manager.current_wave >= wave_manager.max_waves and len(wave_manager.active_spawners) == 0 and len(enemies) == 0:
                victory = True

        # === ОТРИСОВКА ИГРОВОГО МИРА ===
        level_map.draw(screen) 
        draw_grid(screen)

        for tower in towers: tower.draw(screen)
        for enemy in enemies: enemy.draw(screen)
        for bullet in bullets: bullet.draw(screen)
        
        vfx.draw(screen) # <--- РИСУЕМ ЭФФЕКТЫ ПОВЕРХ ВРАГОВ, НО ПОД UI

        # ПРЕДПРОСМОТР РАДИУСА
        if not game_over and not victory and not upgrading_tower:
            mx, my = pygame.mouse.get_pos()
            col, row = mx // CELL_SIZE, my // CELL_SIZE
            preview_x = col * CELL_SIZE + CELL_SIZE // 2
            preview_y = row * CELL_SIZE + CELL_SIZE // 2
            
            preview_elev = level_map.get_elevation(col, row)
            preview_range = selected_tower_class.base_range
            if preview_elev == 2: preview_range = int(preview_range * 1.25)
            elif preview_elev == 0: preview_range = int(preview_range * 0.8)
            
            if (col, row) not in occupied_cells and (col, row) not in level_map.road_cells and len(towers) < MAX_TOWERS:
                pygame.draw.circle(screen, (200, 200, 200), (preview_x, preview_y), preview_range, 1)
            else:
                pygame.draw.circle(screen, (255, 50, 50), (preview_x, preview_y), preview_range, 1)

        # === ИНТЕРФЕЙС ===
        screen.blit(ui_font.render(f"Золото: {match_gold}", True, (255, 215, 0)), (20, 20))
        screen.blit(ui_font.render(f"Жизни: {lives}", True, (255, 100, 100)), (20, 60))
        
        limit_color = (50, 255, 50) if len(towers) < MAX_TOWERS else (255, 50, 50)
        screen.blit(ui_font.render(f"Башни: {len(towers)}/{MAX_TOWERS}", True, limit_color), (20, 100))
        screen.blit(ui_font.render(f"Волна: {wave_manager.current_wave} / {wave_manager.max_waves}", True, (150, 200, 255)), (WIDTH - 250, 20))
        
        if not wave_manager.game_started and not game_over and not victory and not upgrading_tower:
            screen.blit(ui_font.render("Нажмите ПРОБЕЛ, чтобы начать", True, (50, 255, 50)), (WIDTH/2 - 200, HEIGHT/2))
        elif wave_manager.waiting_for_next and not game_over and not victory and not upgrading_tower:
            screen.blit(small_font.render(f"Следующая волна через: {wave_manager.auto_start_timer:.1f}с", True, (255, 255, 255)), (WIDTH - 280, 60))

        screen.blit(small_font.render("[1] Воин  |  [2] Плут  |  [3] Маг", True, (200, 200, 200)), (20, HEIGHT - 55))
        if len(towers) < MAX_TOWERS:
            screen.blit(small_font.render(f"Стройка: {selected_tower_class.name} (Цена: {current_cost} G)", True, (255, 255, 50)), (20, HEIGHT - 30))
        else:
            screen.blit(small_font.render("ЛИМИТ БАШЕН ДОСТИГНУТ!", True, (255, 50, 50)), (20, HEIGHT - 30))

        # --- ОТРИСОВКА МЕНЮ ВЫБОРА НАВЫКОВ ---
        if upgrading_tower:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            
            lvl = upgrading_tower.pending_upgrades[0]
            title_txt = ui_font.render(f"Выберите навык для {upgrading_tower.name} (Уровень {lvl})", True, (255, 255, 255))
            screen.blit(title_txt, title_txt.get_rect(center=(WIDTH/2, HEIGHT/2 - 120)))
            
            choices = upgrading_tower.skill_tree[lvl]
            panel_y = HEIGHT // 2 - (len(choices) * 40)
            
            mx, my = pygame.mouse.get_pos()
            
            for i, choice in enumerate(choices):
                rect = pygame.Rect(WIDTH//2 - 200, panel_y + i * 90, 400, 70)
                bg_color = (70, 70, 100) if rect.collidepoint(mx, my) else (50, 50, 80)
                
                pygame.draw.rect(screen, bg_color, rect, border_radius=10)
                pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=10)
                
                name_txt = ui_font.render(choice["name"], True, (255, 215, 0))
                desc_txt = small_font.render(choice["desc"], True, (200, 200, 200))
                
                screen.blit(name_txt, (rect.x + 15, rect.y + 10))
                screen.blit(desc_txt, (rect.x + 15, rect.y + 40))

        # --- ЭКРАН ПОРАЖЕНИЯ И ПОБЕДЫ ---
        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            go_text = large_font.render("GAME OVER", True, (255, 50, 50))
            screen.blit(go_text, go_text.get_rect(center=(WIDTH/2, HEIGHT/2 - 30)))
            res_text = ui_font.render("Нажмите 'R' для перезапуска", True, (255, 255, 255))
            screen.blit(res_text, res_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 50)))

        if victory:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            vic_text = large_font.render("VICTORY!", True, (255, 215, 0))
            screen.blit(vic_text, vic_text.get_rect(center=(WIDTH/2, HEIGHT/2 - 30)))
            res_text = ui_font.render("Нажмите 'R' для новой игры", True, (255, 255, 255))
            screen.blit(res_text, res_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 50)))

        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()