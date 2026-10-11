# main.py
import pygame

from settings import WIDTH, HEIGHT, FPS, CELL_SIZE, GRID_COLOR
from map.generator import MapPath
from entities.towers import Tower
from entities.class_progression import CLASSES
from core.wave_manager import WaveManager
from core.vfx import vfx
from ui.tower_panel import TowerPanel

pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("D&D Tower Defense — Multiclass")
clock = pygame.time.Clock()
ui_font = pygame.font.SysFont(None, 32)
small_font = pygame.font.SysFont(None, 22)
large_font = pygame.font.SysFont(None, 92)

def draw_grid(surface):
    grid = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    color = (*GRID_COLOR[:3], 35)
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(grid, color, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(grid, color, (0, y), (WIDTH, y))
    surface.blit(grid, (0, 0))


def main():
    level_map = MapPath()
    wave_manager = WaveManager(level_map)
    enemies, towers, bullets = [], [], []
    occupied_cells = set()
    tower_panel = TowerPanel((WIDTH, HEIGHT))

    gold, lives = 150, 20
    max_towers = 8
    selected_tower_class = Tower
    selected_tower = None
    game_speed, paused, auto_wave = 1, False, False
    game_over = victory = False
    running = True

    speeds = (1, 2, 3, 4)
    speed_buttons = {
        speed: pygame.Rect(WIDTH - 250 + i * 55, 70, 50, 34)
        for i, speed in enumerate(speeds)
    }
    pause_button = pygame.Rect(WIDTH - 250, 112, 90, 34)
    auto_button = pygame.Rect(WIDTH - 150, 112, 150, 34)

    while running:
        real_dt = min(clock.tick(FPS) / 1000.0, 0.05)
        pending_tower = next((t for t in towers if t.pending_class_choices), None)
        if pending_tower is not None and not (selected_tower and selected_tower.pending_class_choices):
            selected_tower = pending_tower
        has_mandatory_choice = bool(selected_tower and selected_tower.pending_class_choices)
        sim_paused = paused or has_mandatory_choice or game_over or victory
        dt = 0.0 if sim_paused else real_dt * game_speed
        build_cost = 50 + len(towers) * 50

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4):
                    game_speed = {pygame.K_F1: 1, pygame.K_F2: 2,
                                  pygame.K_F3: 3, pygame.K_F4: 4}[event.key]
                elif event.key == pygame.K_p:
                    paused = not paused
                elif (game_over or victory) and event.key == pygame.K_r:
                    running = False
                    main()
                    return
                elif not sim_paused:
                    if event.key == pygame.K_SPACE and not game_over and not victory:
                        if not wave_manager.game_started:
                            wave_manager.game_started = True
                            wave_manager.force_next_wave()
                        elif (wave_manager.waiting_for_next and not enemies
                              and not wave_manager.active_spawners
                              and wave_manager.current_wave < wave_manager.max_waves):
                            gold += wave_manager.force_next_wave()

            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue
            pos = event.pos
            mx, my = pos

            hit_speed = False
            for speed, rect in speed_buttons.items():
                if rect.collidepoint(pos):
                    game_speed = speed
                    hit_speed = True
                    break
            if hit_speed:
                continue
            if pause_button.collidepoint(pos):
                paused = not paused
                continue
            if auto_button.collidepoint(pos):
                auto_wave = not auto_wave
                continue

            # Class choice is a mandatory modal; it pauses the simulation.
            if selected_tower and selected_tower.pending_class_choices:
                chosen = tower_panel.handle_click(pos, selected_tower)
                if chosen in CLASSES:
                    selected_tower.choose_class_level(chosen)
                    if selected_tower.pending_class_choices == 0:
                        # Keep the character sheet open after making a choice.
                        pass
                continue

            # Normal tower sheet can be closed or another tower can be selected.
            if selected_tower is not None:
                result = tower_panel.handle_click(pos, selected_tower)
                if result == "close":
                    selected_tower = None
                    continue
                if tower_panel.rect.collidepoint(pos):
                    continue

            if game_over or victory:
                continue

            clicked = next((tower for tower in towers if tower.rect.collidepoint(pos)), None)
            if clicked is not None:
                selected_tower = clicked
                continue

            col, row = mx // CELL_SIZE, my // CELL_SIZE
            cell = (col, row)
            if not (0 <= col < level_map.cols and 0 <= row < level_map.rows):
                continue
            if (len(towers) >= max_towers or cell in occupied_cells
                    or cell in level_map.road_cells or gold < build_cost):
                continue

            center = (col * CELL_SIZE + CELL_SIZE // 2,
                      row * CELL_SIZE + CELL_SIZE // 2)
            tower = Tower(*center, level_map)
            towers.append(tower)
            occupied_cells.add(cell)
            gold -= build_cost
            selected_tower = tower  # открываем карточку для выбора первого класса

        if not running:
            break

        # Simulate only when not paused and no required level-up choice is pending.
        has_mandatory_choice = bool(selected_tower and selected_tower.pending_class_choices)
        if not paused and not has_mandatory_choice and not game_over and not victory:
            wave_manager.update(dt, enemies)
            for tower in towers:
                tower.update(dt, enemies, bullets)
            for bullet in bullets:
                bullet.update(dt, enemies)
            for enemy in enemies:
                enemy.update(dt)

            for enemy in enemies:
                if not enemy.alive:
                    if enemy.hp <= 0:
                        gold += enemy.reward
                    elif enemy.reached_end:
                        lives -= 1
                        if lives <= 0:
                            game_over = True
            bullets = [bullet for bullet in bullets if bullet.alive]
            enemies = [enemy for enemy in enemies if enemy.alive]

            # A level-up is announced and automatically opens that character sheet.
            if selected_tower is None:
                selected_tower = next((t for t in towers if t.pending_class_choices), None)

            if (auto_wave and wave_manager.waiting_for_next and not enemies
                    and not wave_manager.active_spawners
                    and wave_manager.current_wave < wave_manager.max_waves):
                gold += wave_manager.force_next_wave()

            if (wave_manager.current_wave >= wave_manager.max_waves
                    and not wave_manager.active_spawners and not enemies):
                victory = True
            vfx.update(dt)

        # World rendering
        level_map.draw(screen)
        draw_grid(screen)
        for tower in towers:
            tower.draw(screen)
        if selected_tower is not None:
            pygame.draw.circle(screen, (255, 230, 80), selected_tower.rect.center, 25, 2)
        for enemy in enemies:
            enemy.draw(screen)
        for bullet in bullets:
            bullet.draw(screen)
        vfx.draw(screen)

        # Build preview and currently selected starting class.
        if not game_over and not victory and selected_tower is None and not paused:
            mx, my = pygame.mouse.get_pos()
            col, row = mx // CELL_SIZE, my // CELL_SIZE
            if 0 <= col < level_map.cols and 0 <= row < level_map.rows:
                elev = level_map.get_elevation(col, row)
                radius = selected_tower_class.base_range
                if elev == 2:
                    radius = int(radius * 1.25)
                elif elev == 0:
                    radius = int(radius * 0.8)
                color = (220, 220, 220) if (col, row) not in level_map.road_cells else (255, 70, 70)
                pygame.draw.circle(screen, color,
                                   (col * CELL_SIZE + CELL_SIZE // 2,
                                    row * CELL_SIZE + CELL_SIZE // 2), radius, 1)

        # HUD
        screen.blit(ui_font.render(f"Золото: {gold}", True, (255, 215, 0)), (16, 14))
        screen.blit(ui_font.render(f"Жизни: {lives}", True, (255, 110, 110)), (16, 48))
        screen.blit(small_font.render(f"Башни: {len(towers)}/{max_towers}", True, (240, 240, 240)), (16, 84))
        screen.blit(ui_font.render(f"Волна: {wave_manager.current_wave}/{wave_manager.max_waves}",
                                   True, (160, 205, 255)), (WIDTH - 250, 16))
        screen.blit(small_font.render("Класс башни выбирается в карточке персонажа",
                                      True, (240, 240, 220)), (16, HEIGHT - 28))
        if not wave_manager.game_started and not game_over and not victory:
            text = ui_font.render("ПРОБЕЛ — начать волну", True, (90, 255, 110))
            screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        elif wave_manager.waiting_for_next and not wave_manager.active_spawners:
            text = small_font.render(f"Следующая волна через {max(0, wave_manager.auto_start_timer):.1f}с",
                                     True, (255, 255, 255))
            screen.blit(text, (WIDTH - 280, 49))

        # Speed controls
        for speed, rect in speed_buttons.items():
            pygame.draw.rect(screen, (65, 130, 85) if game_speed == speed else (55, 60, 75),
                             rect, border_radius=5)
            pygame.draw.rect(screen, (210, 210, 210), rect, 1, border_radius=5)
            label = small_font.render(f"x{speed}", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=rect.center))
        pygame.draw.rect(screen, (150, 75, 65) if paused else (55, 60, 75), pause_button, border_radius=5)
        screen.blit(small_font.render("Продолжить" if paused else "Пауза", True, (255,255,255)),
                    (pause_button.x + 12, pause_button.y + 9))
        pygame.draw.rect(screen, (65, 130, 85) if auto_wave else (55, 60, 75), auto_button, border_radius=5)
        auto_text = small_font.render(f"Автоволна: {'ВКЛ' if auto_wave else 'ВЫКЛ'}", True, (255,255,255))
        screen.blit(auto_text, auto_text.get_rect(center=auto_button.center))

        if paused or has_mandatory_choice:
            label = ui_font.render("ПАУЗА" if paused else "ВЫБЕРИТЕ КЛАСС", True, (255, 220, 100))
            screen.blit(label, label.get_rect(center=(WIDTH // 2, 24)))

        if selected_tower is not None:
            tower_panel.draw(screen, selected_tower)

        if game_over or victory:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 210))
            screen.blit(shade, (0, 0))
            message = "ПОБЕДА!" if victory else "ИГРА ОКОНЧЕНА"
            color = (255, 215, 0) if victory else (255, 70, 70)
            title = large_font.render(message, True, color)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 25)))
            hint = ui_font.render("R — начать заново", True, (255, 255, 255))
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
