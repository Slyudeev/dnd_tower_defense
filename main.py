# main.py
import pygame

from settings import WIDTH, HEIGHT, FPS, CELL_SIZE, GRID_COLOR
from map.generator import MapPath
from entities.towers import WarriorTower, RogueTower, MageTower
from core.wave_manager import WaveManager
from core.vfx import vfx


pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("D&D Tower Defense")
clock = pygame.time.Clock()

ui_font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 100)


def draw_grid(surface):
    """Рисует ненавязчивую полупрозрачную сетку."""
    grid_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    grid_color = (*GRID_COLOR[:3], 35)

    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(grid_surface, grid_color, (x, 0), (x, HEIGHT))

    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(grid_surface, grid_color, (0, y), (WIDTH, y))

    surface.blit(grid_surface, (0, 0))


def get_skill_choice_rects(number_of_choices):
    """Возвращает прямоугольники кнопок выбора навыка."""
    button_width = min(440, WIDTH - 40)
    button_height = 70
    gap = 16
    total_height = number_of_choices * button_height + max(0, number_of_choices - 1) * gap
    start_y = (HEIGHT - total_height) // 2

    rects = []
    for i in range(number_of_choices):
        rects.append(
            pygame.Rect(
                (WIDTH - button_width) // 2,
                start_y + i * (button_height + gap),
                button_width,
                button_height,
            )
        )

    return rects


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
    max_towers = 8
    upgrading_tower = None

    # Настройки скорости и автовызова волн
    game_speed = 1
    paused = False
    auto_wave = False

    # Кнопки интерфейса
    speed_values = (1, 2, 3, 4)
    speed_buttons = {
        speed: pygame.Rect(WIDTH - 250 + i * 55, 70, 50, 35)
        for i, speed in enumerate(speed_values)
    }
    pause_button = pygame.Rect(WIDTH - 250, 115, 90, 35)
    auto_wave_button = pygame.Rect(WIDTH - 150, 115, 150, 35)

    while running:
        # Ограничиваем большой скачок времени, затем применяем игровую скорость.
        real_dt = min(clock.tick(FPS) / 1000.0, 0.05)
        dt = 0.0 if paused else real_dt * game_speed

        current_cost = 50 + len(towers) * 50

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type == pygame.KEYDOWN:
                # Скорость можно менять с клавиатуры: F1–F4.
                if event.key == pygame.K_F1:
                    game_speed = 1
                elif event.key == pygame.K_F2:
                    game_speed = 2
                elif event.key == pygame.K_F3:
                    game_speed = 3
                elif event.key == pygame.K_F4:
                    game_speed = 4
                elif event.key == pygame.K_p:
                    paused = not paused

                # Перезапуск после завершения игры.
                if (game_over or victory) and event.key == pygame.K_r:
                    main()
                    return

                # Остальные игровые клавиши блокируются во время паузы
                # и при открытом меню навыков.
                if not paused and upgrading_tower is None:
                    if event.key == pygame.K_SPACE and not game_over and not victory:
                        if not wave_manager.game_started:
                            wave_manager.game_started = True
                            wave_manager.force_next_wave()
                        elif wave_manager.current_wave < wave_manager.max_waves:
                            bonus = wave_manager.force_next_wave()
                            if bonus:
                                match_gold += bonus

                    if event.key == pygame.K_1:
                        selected_tower_class = WarriorTower
                    elif event.key == pygame.K_2:
                        selected_tower_class = RogueTower
                    elif event.key == pygame.K_3:
                        selected_tower_class = MageTower

            if event.type != pygame.MOUSEBUTTONDOWN:
                continue

            mx, my = event.pos

            # Кнопки интерфейса обрабатываются раньше клика по карте.
            speed_button_clicked = False
            for speed, rect in speed_buttons.items():
                if rect.collidepoint(mx, my):
                    game_speed = speed
                    speed_button_clicked = True
                    break

            if speed_button_clicked:
                continue

            if pause_button.collidepoint(mx, my):
                paused = not paused
                continue

            if auto_wave_button.collidepoint(mx, my):
                auto_wave = not auto_wave
                continue

            if game_over or victory:
                continue

            # Если открыто меню навыка — обрабатываем только выбор навыка.
            if upgrading_tower is not None:
                if not upgrading_tower.pending_upgrades:
                    upgrading_tower = None
                    continue

                level = upgrading_tower.pending_upgrades[0]
                choices = upgrading_tower.skill_tree.get(level, [])
                choice_rects = get_skill_choice_rects(len(choices))

                for i, choice in enumerate(choices):
                    if choice_rects[i].collidepoint(mx, my):
                        upgrading_tower.apply_skill(level, choice["name"])
                        upgrading_tower.pending_upgrades.pop(0)

                        if not upgrading_tower.pending_upgrades:
                            upgrading_tower = None
                        break

                continue

            # Клик по существующей башне открывает выбор навыка, если он доступен.
            clicked_tower = None
            for tower in towers:
                if tower.rect.collidepoint(mx, my):
                    clicked_tower = tower
                    break

            if clicked_tower is not None:
                if clicked_tower.pending_upgrades:
                    upgrading_tower = clicked_tower
                continue

            # Иначе пробуем построить башню.
            col = mx // CELL_SIZE
            row = my // CELL_SIZE
            cell = (col, row)

            in_map = (
                0 <= col < level_map.cols
                and 0 <= row < level_map.rows
            )

            if not in_map:
                continue

            can_build = (
                len(towers) < max_towers
                and cell not in occupied_cells
                and cell not in level_map.road_cells
                and match_gold >= current_cost
            )

            if can_build:
                center_x = col * CELL_SIZE + CELL_SIZE // 2
                center_y = row * CELL_SIZE + CELL_SIZE // 2

                tower = selected_tower_class(center_x, center_y, level_map)
                towers.append(tower)
                occupied_cells.add(cell)
                match_gold -= current_cost

        # Игровая симуляция остановлена на паузе и во время выбора навыка.
        if not paused and upgrading_tower is None and not game_over and not victory:
            wave_manager.update(dt, enemies)

            for tower in towers:
                tower.update(dt, enemies, bullets)

            for bullet in bullets:
                bullet.update(dt, enemies)

            for enemy in enemies:
                enemy.update(dt)

            # Награды и потеря жизней за уже завершивших движение врагов.
            for enemy in enemies:
                if not enemy.alive:
                    if enemy.hp <= 0:
                        match_gold += enemy.reward
                    elif enemy.reached_end:
                        lives -= 1
                        if lives <= 0:
                            game_over = True

            bullets = [bullet for bullet in bullets if bullet.alive]
            enemies = [enemy for enemy in enemies if enemy.alive]

            # Автоматически начинаем следующую волну,
            # когда все враги текущей волны побеждены.
            if (
                auto_wave
                and wave_manager.game_started
                and wave_manager.waiting_for_next
                and not enemies
                and not wave_manager.active_spawners
                and wave_manager.current_wave < wave_manager.max_waves
            ):
                wave_manager.force_next_wave()

            # Победа после завершения последней волны.
            if (
                wave_manager.current_wave >= wave_manager.max_waves
                and not wave_manager.active_spawners
                and not enemies
            ):
                victory = True

            vfx.update(dt)

        # Отрисовка игрового мира.
        level_map.draw(screen)
        draw_grid(screen)

        for tower in towers:
            tower.draw(screen)

        for enemy in enemies:
            enemy.draw(screen)

        for bullet in bullets:
            bullet.draw(screen)

        # Эффекты рисуются поверх игрового мира, но под интерфейсом.
        vfx.draw(screen)

        # Предпросмотр радиуса башни под курсором.
        if not game_over and not victory and upgrading_tower is None:
            mx, my = pygame.mouse.get_pos()
            col = mx // CELL_SIZE
            row = my // CELL_SIZE

            if 0 <= col < level_map.cols and 0 <= row < level_map.rows:
                preview_x = col * CELL_SIZE + CELL_SIZE // 2
                preview_y = row * CELL_SIZE + CELL_SIZE // 2

                elevation = level_map.get_elevation(col, row)
                preview_range = selected_tower_class.base_range

                if elevation == 2:
                    preview_range = int(preview_range * 1.25)
                elif elevation == 0:
                    preview_range = int(preview_range * 0.8)

                valid_cell = (
                    (col, row) not in occupied_cells
                    and (col, row) not in level_map.road_cells
                    and len(towers) < max_towers
                )

                preview_color = (200, 200, 200) if valid_cell else (255, 50, 50)
                pygame.draw.circle(
                    screen,
                    preview_color,
                    (preview_x, preview_y),
                    preview_range,
                    1,
                )

        # Основной интерфейс.
        screen.blit(
            ui_font.render(f"Золото: {match_gold}", True, (255, 215, 0)),
            (20, 20),
        )
        screen.blit(
            ui_font.render(f"Жизни: {lives}", True, (255, 100, 100)),
            (20, 60),
        )

        tower_limit_color = (
            (50, 255, 50) if len(towers) < max_towers else (255, 50, 50)
        )
        screen.blit(
            ui_font.render(
                f"Башни: {len(towers)}/{max_towers}",
                True,
                tower_limit_color,
            ),
            (20, 100),
        )

        wave_text = (
            f"Волна: {wave_manager.current_wave} / {wave_manager.max_waves}"
        )
        screen.blit(
            ui_font.render(wave_text, True, (150, 200, 255)),
            (WIDTH - 250, 20),
        )

        if (
            not wave_manager.game_started
            and not game_over
            and not victory
            and upgrading_tower is None
        ):
            start_text = ui_font.render(
                "Нажмите ПРОБЕЛ, чтобы начать",
                True,
                (50, 255, 50),
            )
            screen.blit(
                start_text,
                start_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)),
            )

        elif (
            wave_manager.waiting_for_next
            and not game_over
            and not victory
            and upgrading_tower is None
        ):
            timer_text = small_font.render(
                f"Следующая волна через: "
                f"{wave_manager.auto_start_timer:.1f}с",
                True,
                (255, 255, 255),
            )
            screen.blit(timer_text, (WIDTH - 280, 55))

        screen.blit(
            small_font.render(
                "[1] Воин  |  [2] Плут  |  [3] Маг",
                True,
                (200, 200, 200),
            ),
            (20, HEIGHT - 55),
        )

        if len(towers) < max_towers:
            build_text = (
                f"Стройка: {selected_tower_class.name} "
                f"(Цена: {current_cost} G)"
            )
            build_color = (255, 255, 50)
        else:
            build_text = "ЛИМИТ БАШЕН ДОСТИГНУТ!"
            build_color = (255, 50, 50)

        screen.blit(
            small_font.render(build_text, True, build_color),
            (20, HEIGHT - 30),
        )

        # Кнопки скорости.
        for speed, rect in speed_buttons.items():
            selected = game_speed == speed
            button_color = (65, 130, 85) if selected else (55, 60, 75)

            pygame.draw.rect(screen, button_color, rect, border_radius=6)
            pygame.draw.rect(
                screen,
                (210, 210, 210),
                rect,
                width=2,
                border_radius=6,
            )

            label = small_font.render(f"x{speed}", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=rect.center))

        # Кнопка паузы.
        pause_color = (150, 75, 65) if paused else (55, 60, 75)
        pygame.draw.rect(
            screen,
            pause_color,
            pause_button,
            border_radius=6,
        )
        pygame.draw.rect(
            screen,
            (210, 210, 210),
            pause_button,
            width=2,
            border_radius=6,
        )

        pause_label = small_font.render(
            "Продолжить" if paused else "Пауза",
            True,
            (255, 255, 255),
        )
        screen.blit(
            pause_label,
            pause_label.get_rect(center=pause_button.center),
        )

        # Кнопка автовызова волн.
        auto_color = (65, 130, 85) if auto_wave else (55, 60, 75)
        pygame.draw.rect(
            screen,
            auto_color,
            auto_wave_button,
            border_radius=6,
        )
        pygame.draw.rect(
            screen,
            (210, 210, 210),
            auto_wave_button,
            width=2,
            border_radius=6,
        )

        auto_label = small_font.render(
            f"Автоволна: {'ВКЛ' if auto_wave else 'ВЫКЛ'}",
            True,
            (255, 255, 255),
        )
        screen.blit(
            auto_label,
            auto_label.get_rect(center=auto_wave_button.center),
        )

        if paused:
            paused_label = ui_font.render(
                "ПАУЗА",
                True,
                (255, 220, 100),
            )
            screen.blit(
                paused_label,
                paused_label.get_rect(center=(WIDTH // 2, 35)),
            )

        # Меню выбора навыка.
        if upgrading_tower is not None and upgrading_tower.pending_upgrades:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            screen.blit(overlay, (0, 0))

            level = upgrading_tower.pending_upgrades[0]
            choices = upgrading_tower.skill_tree.get(level, [])

            title = ui_font.render(
                f"Выберите навык: {upgrading_tower.name}, уровень {level}",
                True,
                (255, 255, 255),
            )
            screen.blit(
                title,
                title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 110)),
            )

            mouse_pos = pygame.mouse.get_pos()
            choice_rects = get_skill_choice_rects(len(choices))

            for i, choice in enumerate(choices):
                rect = choice_rects[i]
                hovered = rect.collidepoint(mouse_pos)
                color = (75, 75, 115) if hovered else (50, 50, 80)

                pygame.draw.rect(screen, color, rect, border_radius=10)
                pygame.draw.rect(
                    screen,
                    (210, 210, 210),
                    rect,
                    width=2,
                    border_radius=10,
                )

                name_text = ui_font.render(
                    choice["name"],
                    True,
                    (255, 215, 0),
                )
                desc_text = small_font.render(
                    choice.get("desc", ""),
                    True,
                    (220, 220, 220),
                )

                screen.blit(name_text, (rect.x + 15, rect.y + 8))
                screen.blit(desc_text, (rect.x + 15, rect.y + 42))

        # Экран поражения.
        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))

            game_over_text = large_font.render(
                "GAME OVER",
                True,
                (255, 50, 50),
            )
            screen.blit(
                game_over_text,
                game_over_text.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 - 30)
                ),
            )

            restart_text = ui_font.render(
                "Нажмите R для перезапуска",
                True,
                (255, 255, 255),
            )
            screen.blit(
                restart_text,
                restart_text.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 + 50)
                ),
            )

        # Экран победы.
        if victory:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))

            victory_text = large_font.render(
                "VICTORY!",
                True,
                (255, 215, 0),
            )
            screen.blit(
                victory_text,
                victory_text.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 - 30)
                ),
            )

            restart_text = ui_font.render(
                "Нажмите R для новой игры",
                True,
                (255, 255, 255),
            )
            screen.blit(
                restart_text,
                restart_text.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 + 50)
                ),
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
