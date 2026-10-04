# main.py
import pygame
from settings import WIDTH, HEIGHT, FPS, CELL_SIZE, GRID_COLOR
from map.generator import MapPath
from entities.towers import HeroTower
from entities.classes import CLASS_DATA
from core.wave_manager import WaveManager
from core.vfx import vfx

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("D&D Tower Defense: Multiclassing")
clock = pygame.time.Clock()

ui_font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 100)

def draw_grid(surface):
    grid_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    grid_color = (*GRID_COLOR[:3], 35)
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(grid_surface, grid_color, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(grid_surface, grid_color, (0, y), (WIDTH, y))
    surface.blit(grid_surface, (0, 0))

def main():
    running = True
    level_map = MapPath()
    wave_manager = WaveManager(level_map)

    enemies, towers, bullets = [], [], []
    occupied_cells = set()

    match_gold = 150
    lives = 20
    game_over = victory = False

    selected_starting_class = "Warrior"
    max_towers = 8
    
    selected_tower = None # Выбранная башня для просмотра статов/прокачки

    game_speed = 1
    paused = False
    auto_wave = False

    speed_values = (1, 2, 3, 4)
    speed_buttons = {s: pygame.Rect(WIDTH - 250 + i * 55, 70, 50, 35) for i, s in enumerate(speed_values)}
    pause_button = pygame.Rect(WIDTH - 250, 115, 90, 35)
    auto_wave_button = pygame.Rect(WIDTH - 150, 115, 150, 35)

    while running:
        # ПАУЗА: Ручная ИЛИ если у выделенной башни есть нераспределенный уровень/навык
        needs_choice = selected_tower and (selected_tower.unspent_levels > 0 or len(selected_tower.pending_choices) > 0)
        real_paused = paused or needs_choice

        real_dt = min(clock.tick(FPS) / 1000.0, 0.05)
        dt = 0.0 if real_paused else real_dt * game_speed

        current_cost = 50 + len(towers) * 50

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1: game_speed = 1
                elif event.key == pygame.K_F2: game_speed = 2
                elif event.key == pygame.K_F3: game_speed = 3
                elif event.key == pygame.K_F4: game_speed = 4
                elif event.key == pygame.K_p: paused = not paused

                if (game_over or victory) and event.key == pygame.K_r:
                    main()
                    return

                if not real_paused:
                    if event.key == pygame.K_SPACE and not game_over and not victory:
                        if not wave_manager.game_started:
                            wave_manager.game_started = True
                            wave_manager.force_next_wave()
                        elif wave_manager.current_wave < wave_manager.max_waves:
                            bonus = wave_manager.force_next_wave()
                            if bonus: match_gold += bonus

                    if event.key == pygame.K_1: selected_starting_class = "Warrior"
                    elif event.key == pygame.K_2: selected_starting_class = "Rogue"
                    elif event.key == pygame.K_3: selected_starting_class = "Mage"

            if event.type != pygame.MOUSEBUTTONDOWN:
                continue

            mx, my = event.pos

            # Проверка кликов по интерфейсу башни (Меню Мультикласса)
            if selected_tower:
                panel_rect = pygame.Rect(10, 10, 280, HEIGHT - 20)
                if panel_rect.collidepoint(mx, my):
                    # Если есть нераспределенные уровни - обрабатываем кнопки классов
                    if selected_tower.unspent_levels > 0:
                        y_offset = 350
                        for c_name in CLASS_DATA.keys():
                            btn = pygame.Rect(20, y_offset, 260, 35)
                            if btn.collidepoint(mx, my):
                                selected_tower.level_up_class(c_name)
                            y_offset += 45
                    # Если нужно выбрать навык
                    elif len(selected_tower.pending_choices) > 0:
                        choice_data = selected_tower.pending_choices[0]
                        y_offset = 350
                        for i, opt in enumerate(choice_data["options"]):
                            btn = pygame.Rect(20, y_offset, 260, 60)
                            if btn.collidepoint(mx, my):
                                selected_tower.apply_skill(choice_data, i)
                            y_offset += 70

                    # Кнопка закрытия интерфейса
                    close_btn = pygame.Rect(260, 25, 20, 20)
                    if close_btn.collidepoint(mx, my) and not needs_choice:
                        selected_tower = None
                    continue
                else:
                    # Клик вне панели. Если выбор обязателен - игнорируем клик
                    if needs_choice: continue
                    # Иначе - снимаем выделение и продолжаем проверку карты
                    selected_tower = None

            # Кнопки скорости
            speed_button_clicked = False
            for speed, rect in speed_buttons.items():
                if rect.collidepoint(mx, my):
                    game_speed = speed
                    speed_button_clicked = True
                    break
            if speed_button_clicked: continue

            if pause_button.collidepoint(mx, my):
                paused = not paused
                continue

            if auto_wave_button.collidepoint(mx, my):
                auto_wave = not auto_wave
                continue

            if game_over or victory: continue

            # Выбор существующей башни
            clicked_tower = None
            for tower in towers:
                if tower.rect.collidepoint(mx, my):
                    clicked_tower = tower
                    break

            if clicked_tower is not None:
                selected_tower = clicked_tower
                continue

            # Постройка новой башни
            col, row = mx // CELL_SIZE, my // CELL_SIZE
            cell = (col, row)

            in_map = (0 <= col < level_map.cols and 0 <= row < level_map.rows)
            if not in_map: continue

            can_build = (
                len(towers) < max_towers
                and cell not in occupied_cells
                and cell not in level_map.road_cells
                and match_gold >= current_cost
            )

            if can_build:
                center_x = col * CELL_SIZE + CELL_SIZE // 2
                center_y = row * CELL_SIZE + CELL_SIZE // 2
                tower = HeroTower(center_x, center_y, level_map, selected_starting_class)
                towers.append(tower)
                occupied_cells.add(cell)
                match_gold -= current_cost

        # Игровая симуляция
        if not real_paused and not game_over and not victory:
            wave_manager.update(dt, enemies)
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

            if (auto_wave and wave_manager.game_started and wave_manager.waiting_for_next
                and not enemies and not wave_manager.active_spawners 
                and wave_manager.current_wave < wave_manager.max_waves):
                wave_manager.force_next_wave()

            if (wave_manager.current_wave >= wave_manager.max_waves
                and not wave_manager.active_spawners and not enemies):
                victory = True

            vfx.update(dt)

        # Отрисовка
        level_map.draw(screen)
        draw_grid(screen)

        # Радиус выбранной башни или превью
        if selected_tower:
            pygame.draw.circle(screen, (200, 200, 200), (selected_tower.x, selected_tower.y), selected_tower.range, 1)
        elif not game_over and not victory:
            mx, my = pygame.mouse.get_pos()
            col, row = mx // CELL_SIZE, my // CELL_SIZE
            if 0 <= col < level_map.cols and 0 <= row < level_map.rows:
                preview_x = col * CELL_SIZE + CELL_SIZE // 2
                preview_y = row * CELL_SIZE + CELL_SIZE // 2
                valid_cell = (col, row) not in occupied_cells and (col, row) not in level_map.road_cells and len(towers) < max_towers
                preview_color = (200, 200, 200) if valid_cell else (255, 50, 50)
                pygame.draw.circle(screen, preview_color, (preview_x, preview_y), 130, 1) # Базовый радиус превью

        for tower in towers: tower.draw(screen)
        for enemy in enemies: enemy.draw(screen)
        for bullet in bullets: bullet.draw(screen)
        vfx.draw(screen)

        # UI Статистика
        screen.blit(ui_font.render(f"Золото: {match_gold}", True, (255, 215, 0)), (20, 20))
        screen.blit(ui_font.render(f"Жизни: {lives}", True, (255, 100, 100)), (20, 60))
        tower_limit_color = (50, 255, 50) if len(towers) < max_towers else (255, 50, 50)
        screen.blit(ui_font.render(f"Герои: {len(towers)}/{max_towers}", True, tower_limit_color), (20, 100))

        wave_text = f"Волна: {wave_manager.current_wave} / {wave_manager.max_waves}"
        screen.blit(ui_font.render(wave_text, True, (150, 200, 255)), (WIDTH - 250, 20))

        if not wave_manager.game_started and not game_over and not victory and not needs_choice:
            start_text = ui_font.render("Нажмите ПРОБЕЛ, чтобы начать", True, (50, 255, 50))
            screen.blit(start_text, start_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        screen.blit(small_font.render("[1] Воин  |  [2] Плут  |  [3] Маг", True, (200, 200, 200)), (20, HEIGHT - 55))
        if len(towers) < max_towers:
            cls_color = CLASS_DATA[selected_starting_class]["color"]
            build_text = f"Стройка: {CLASS_DATA[selected_starting_class]['name']} (Цена: {current_cost} G)"
            screen.blit(small_font.render(build_text, True, cls_color), (20, HEIGHT - 30))

        # Отрисовка кнопок
        for speed, rect in speed_buttons.items():
            btn_col = (65, 130, 85) if game_speed == speed else (55, 60, 75)
            pygame.draw.rect(screen, btn_col, rect, border_radius=6)
            pygame.draw.rect(screen, (210, 210, 210), rect, width=2, border_radius=6)
            label = small_font.render(f"x{speed}", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=rect.center))

        pause_col = (150, 75, 65) if paused else (55, 60, 75)
        pygame.draw.rect(screen, pause_col, pause_button, border_radius=6)
        pygame.draw.rect(screen, (210, 210, 210), pause_button, width=2, border_radius=6)
        p_label = small_font.render("Продолжить" if paused else "Пауза", True, (255, 255, 255))
        screen.blit(p_label, p_label.get_rect(center=pause_button.center))

        auto_col = (65, 130, 85) if auto_wave else (55, 60, 75)
        pygame.draw.rect(screen, auto_col, auto_wave_button, border_radius=6)
        pygame.draw.rect(screen, (210, 210, 210), auto_wave_button, width=2, border_radius=6)
        a_label = small_font.render(f"Автоволна: {'ВКЛ' if auto_wave else 'ВЫКЛ'}", True, (255, 255, 255))
        screen.blit(a_label, a_label.get_rect(center=auto_wave_button.center))

        if paused and not needs_choice:
            paused_label = ui_font.render("ПАУЗА", True, (255, 220, 100))
            screen.blit(paused_label, paused_label.get_rect(center=(WIDTH // 2, 35)))

        # === ПАНЕЛЬ МУЛЬТИКЛАССА И ХАРАКТЕРИСТИК (ПО КЛИКУ) ===
        if selected_tower:
            panel = pygame.Rect(10, 10, 280, HEIGHT - 20)
            overlay = pygame.Surface((280, HEIGHT - 20), pygame.SRCALPHA)
            overlay.fill((30, 30, 45, 240))
            screen.blit(overlay, (10, 10))
            pygame.draw.rect(screen, (100, 100, 120), panel, 2, border_radius=8)
            
            # Кнопка X
            pygame.draw.rect(screen, (200, 50, 50), (260, 25, 20, 20), border_radius=4)
            
            title = ui_font.render(f"Герой (Ур. {selected_tower.global_level})", True, (255, 215, 0))
            screen.blit(title, (20, 25))
            
            # Характеристики
            y = 65
            s = selected_tower.stats
            screen.blit(small_font.render(f"STR:{s['STR']} DEX:{s['DEX']} CON:{s['CON']}", True, (200, 200, 200)), (20, y))
            screen.blit(small_font.render(f"INT:{s['INT']} WIS:{s['WIS']} CHA:{s['CHA']}", True, (200, 200, 200)), (20, y+20))
            
            # Боевые статы
            y += 50
            screen.blit(small_font.render(f"Урон: {selected_tower.damage}", True, (255, 100, 100)), (20, y))
            screen.blit(small_font.render(f"Меткость: +{selected_tower.attack_bonus}", True, (100, 255, 100)), (20, y+25))
            screen.blit(small_font.render(f"Скорость: {selected_tower.cooldown_time:.2f}с", True, (100, 200, 255)), (20, y+50))
            screen.blit(small_font.render(f"Крит: {selected_tower.crit_chance}% (x{selected_tower.crit_multiplier})", True, (255, 150, 50)), (20, y+75))
            
            # Уровни классов
            y += 110
            screen.blit(ui_font.render("Классы:", True, (200, 200, 255)), (20, y))
            y += 30
            for c_name, c_lvl in selected_tower.classes.items():
                c_col = CLASS_DATA[c_name]["color"]
                screen.blit(small_font.render(f"{CLASS_DATA[c_name]['name']}: {c_lvl}", True, c_col), (20, y))
                y += 25
                
            # Изученные Навыки
            y += 10
            if selected_tower.learned_skill_names:
                screen.blit(ui_font.render("Навыки:", True, (200, 200, 255)), (20, y))
                y += 30
                for sk in selected_tower.learned_skill_names:
                    screen.blit(small_font.render(f"- {sk}", True, (220, 220, 220)), (20, y))
                    y += 20
                    
            # === КНОПКИ ВЫБОРА ===
            if selected_tower.unspent_levels > 0:
                y = 350
                screen.blit(ui_font.render("НОВЫЙ УРОВЕНЬ!", True, (50, 255, 50)), (20, y-35))
                for c_name in CLASS_DATA.keys():
                    btn = pygame.Rect(20, y, 260, 35)
                    pygame.draw.rect(screen, CLASS_DATA[c_name]["color"], btn, border_radius=5)
                    pygame.draw.rect(screen, (255, 255, 255), btn, 1, border_radius=5)
                    screen.blit(ui_font.render(f"+1 {CLASS_DATA[c_name]['name']}", True, (255, 255, 255)), (btn.x + 10, btn.y + 5))
                    y += 45
            elif len(selected_tower.pending_choices) > 0:
                choice_data = selected_tower.pending_choices[0]
                y = 350
                c_label = CLASS_DATA[choice_data['class_name']]['name']
                screen.blit(ui_font.render(f"Навык ({c_label} {choice_data['level']})", True, (255, 215, 0)), (20, y-35))
                for opt in choice_data["options"]:
                    btn = pygame.Rect(20, y, 260, 60)
                    pygame.draw.rect(screen, (60, 60, 80), btn, border_radius=5)
                    pygame.draw.rect(screen, (200, 200, 200), btn, 1, border_radius=5)
                    screen.blit(ui_font.render(opt["name"], True, (255, 255, 255)), (btn.x + 10, btn.y + 5))
                    screen.blit(small_font.render(opt["desc"], True, (180, 180, 180)), (btn.x + 10, btn.y + 35))
                    y += 70

        if game_over or victory:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))
            text = "GAME OVER" if game_over else "VICTORY!"
            col = (255, 50, 50) if game_over else (255, 215, 0)
            txt_ren = large_font.render(text, True, col)
            screen.blit(txt_ren, txt_ren.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))
            rest = ui_font.render("Нажмите R для рестарта", True, (255, 255, 255))
            screen.blit(rest, rest.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)))

        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()
