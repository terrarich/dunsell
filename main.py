# -*- coding: utf-8 -*-
import pygame
import random
from config import SCREEN_W, SCREEN_H, STATE_MENU, STATE_PLAY, STATE_DEAD, STATE_WIN, STATE_MAPS, STATE_EDITOR, STATE_OPTIONS, COL_GOLD
from editor import run_map_editor
from game_state import Game
from systems import (
    clamp_camera, update_particles, update_float_texts,
    handle_input, pick_up_items, enemy_ai_and_collisions,
    update_projectiles, update_visited_by_player, check_exit
)
from render import (
    draw_world, draw_lighting, draw_ui,
    draw_death_or_win_overlay, compute_death_win_button_rects
)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("DunSell")
    
    # Устанавливаем иконку окна
    try:
        icon = pygame.image.load("DS_logo.ico")
        pygame.display.set_icon(icon)
    except:
        # Если не удалось загрузить иконку, создаем простую
        try:
            icon_surface = pygame.Surface((32, 32))
            icon_surface.fill((255, 215, 0))  # Золотой цвет
            pygame.display.set_icon(icon_surface)
        except:
            pass  # Если и это не работает, оставляем без иконки
    
    clock = pygame.time.Clock()

    font_small = pygame.font.SysFont("consolas", 18)
    font_mid = pygame.font.SysFont("consolas", 24, bold=False)
    font_big = pygame.font.SysFont("consolas", 36, bold=True)

    game = Game(screen, clock, font_small, font_mid, font_big)
    # возможность включить пользовательскую карту из меню позже
    # по умолчанию путь maps/custom_map.json

    # Сплэш-надписи в стиле Minecraft
    splash_texts = [
        "Попробуйте Minecraft",
        "Попробуйте Terraria",
        "Создано Terrarich`ем",
        "99% багов бесплатно!",
        "С Сахором",
        "Убей время",
        "Спидран по DunSell",
        "Technoblade never die",
        "Рик роллит!",
    ]
    current_splash = random.choice(splash_texts)
    next_splash_change = pygame.time.get_ticks() + 4000

    running = True
    dt = 0.016

    while running:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()

        # Общие события (выход)
        for e in events:
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        # Состояние: меню
        if game.state == STATE_MENU:
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_UP:
                        game.menu_sel = (game.menu_sel - 1) % len(game.menu_items)
                    elif e.key == pygame.K_DOWN:
                        game.menu_sel = (game.menu_sel + 1) % len(game.menu_items)
                    elif e.key == pygame.K_LEFT:
                        game.menu_items[game.menu_sel]["left"]()
                    elif e.key == pygame.K_RIGHT:
                        game.menu_items[game.menu_sel]["right"]()
                    elif e.key == pygame.K_RETURN:
                        if game.menu_sel == len(game.menu_items) - 1:  # РЕДАКТОР КАРТ
                            # запускаем редактор карт и после выхода возвращаемся в меню
                            def factory():
                                return Game(screen, clock, font_small, font_mid, font_big)
                            # увеличим размер окна редактора отдельно (внутри самого редактора переназначим)
                            run_map_editor(factory)
                            game.state = STATE_MENU
                            continue
                        elif game.menu_sel == len(game.menu_items) - 2:  # МОИ КАРТЫ
                            game._scan_maps()
                            game.state = STATE_MAPS
                        else:  # НАЧАТЬ ИГРУ -> опции
                            game.opt_sel = 0
                            game.state = STATE_OPTIONS

            # Рендер меню
            screen.fill((16, 18, 24))
            title = font_big.render("DunSell", True, (200, 230, 255))
            screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 80))

            desc = font_mid.render("Выбери настройки и нажми Enter, чтобы начать", True, (140, 150, 160))
            screen.blit(desc, (SCREEN_W//2 - desc.get_width()//2, 120))

             # Обновление сплэш-надписи раз в несколько секунд
            now = pygame.time.get_ticks()
            if now >= next_splash_change:
                new_choice = random.choice(splash_texts)
                if new_choice != current_splash:
                    current_splash = new_choice
                next_splash_change = now + 4000

            # Рисуем сплэш-надпись жёлтым и слегка повёрнутой
            splash_img = font_mid.render(current_splash, True, COL_GOLD)
            splash_img = pygame.transform.rotate(splash_img, -12)
            splash_x = SCREEN_W//2 + title.get_width()//2 - splash_img.get_width()//2 + 80
            splash_y = 80 - 16
            screen.blit(splash_img, (splash_x, splash_y))

            base_y = 180
            for i, it in enumerate(game.menu_items):
                is_sel = (i == game.menu_sel)
                name = it["name"]
                val = it["get"]()
                text = f"{name}: {val}" if val != "" else name
                img = font_mid.render(text, True, (230, 235, 240) if is_sel else (140, 150, 160))
                x = SCREEN_W//2 - img.get_width()//2
                y = base_y + i * 40
                if is_sel:
                    pygame.draw.rect(screen, (40, 70, 100), pygame.Rect(x-14, y-4, img.get_width()+28, img.get_height()+8), border_radius=8)
                screen.blit(img, (x, y))

            pygame.display.flip()
            continue

        # Состояние: опции перед стартом
        if game.state == STATE_OPTIONS:
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        game.state = STATE_MENU
                    elif e.key == pygame.K_UP:
                        game.opt_sel = (game.opt_sel - 1) % len(game.opt_items)
                    elif e.key == pygame.K_DOWN:
                        game.opt_sel = (game.opt_sel + 1) % len(game.opt_items)
                    elif e.key == pygame.K_LEFT:
                        game.opt_items[game.opt_sel]["left"]()
                    elif e.key == pygame.K_RIGHT:
                        game.opt_items[game.opt_sel]["right"]()
                    elif e.key == pygame.K_RETURN:
                        if game.opt_sel == len(game.opt_items) - 1:  # СТАРТ
                            game.new_run()
                        
            screen.fill((16, 18, 24))
            title = font_big.render("Параметры перед стартом", True, (200, 230, 255))
            screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 80))

            desc = font_mid.render("Выберите параметры, затем Enter на \"СТАРТ\"", True, (140, 150, 160))
            screen.blit(desc, (SCREEN_W//2 - desc.get_width()//2, 120))

            base_y = 180
            for i, it in enumerate(game.opt_items):
                is_sel = (i == game.opt_sel)
                name = it["name"]
                val = it["get"]()
                text = f"{name}: {val}" if val != "" else name
                img = font_mid.render(text, True, (230, 235, 240) if is_sel else (140, 150, 160))
                x = SCREEN_W//2 - img.get_width()//2
                y = base_y + i * 40
                if is_sel:
                    pygame.draw.rect(screen, (40, 70, 100), pygame.Rect(x-14, y-4, img.get_width()+28, img.get_height()+8), border_radius=8)
                screen.blit(img, (x, y))

            pygame.display.flip()
            continue

        # Состояние: список карт
        if game.state == STATE_MAPS:
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        game.state = STATE_MENU
                    elif e.key == pygame.K_UP:
                        game.selected_map_idx = (game.selected_map_idx - 1) % max(1, len(game.maps_list))
                    elif e.key == pygame.K_DOWN:
                        game.selected_map_idx = (game.selected_map_idx + 1) % max(1, len(game.maps_list))
                    elif e.key == pygame.K_RETURN and len(game.maps_list) > 0:
                        # Выбираем карту
                        import os
                        name = game.maps_list[game.selected_map_idx]
                        game.settings["use_custom_map"] = True
                        game.settings["custom_map_path"] = os.path.join("maps", name)
                        game.new_run()

            screen.fill((16, 18, 24))
            title = font_big.render("Мои карты", True, (200, 230, 255))
            screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 60))
            hint = font_small.render("Esc — назад, Enter — выбрать карту", True, (140, 150, 160))
            screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, 96))

            base_y = 140
            if not game.maps_list:
                empty = font_mid.render("Нет файлов в папке maps", True, (160, 160, 170))
                screen.blit(empty, (SCREEN_W//2 - empty.get_width()//2, base_y))
            else:
                for i, name in enumerate(game.maps_list):
                    is_sel = (i == game.selected_map_idx)
                    label = name[:-5] if name.lower().endswith('.json') else name
                    img = font_mid.render(label, True, (230, 235, 240) if is_sel else (140, 150, 160))
                    x = SCREEN_W//2 - img.get_width()//2
                    y = base_y + i * 34
                    if is_sel:
                        pygame.draw.rect(screen, (40, 70, 100), pygame.Rect(x-14, y-4, img.get_width()+28, img.get_height()+8), border_radius=8)
                    screen.blit(img, (x, y))

            pygame.display.flip()
            continue

        # Состояние: игра
        if game.state == STATE_PLAY:
            handle_input(game, dt, events)
            update_visited_by_player(game)

            clamp_camera(game)
            pick_up_items(game)
            enemy_ai_and_collisions(game, dt)
            update_projectiles(game, dt)
            update_particles(game, dt)
            update_float_texts(game, dt)
            check_exit(game)

            if game.game_over:
                game.state = STATE_DEAD
            elif game.win:
                game.state = STATE_WIN

            draw_world(game)
            draw_lighting(game)
            draw_ui(game)
            pygame.display.flip()
            continue

        # Состояния: смерть / победа
        if game.state in (STATE_DEAD, STATE_WIN):
            buttons = compute_death_win_button_rects(game)
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_r:
                        game.new_run()
                    elif e.key == pygame.K_m:
                        game.state = STATE_MENU
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    if buttons["restart"].collidepoint(mx, my):
                        game.new_run()
                    elif buttons["menu"].collidepoint(mx, my):
                        game.state = STATE_MENU

            draw_world(game)
            draw_lighting(game)
            if game.state == STATE_DEAD:
                draw_death_or_win_overlay(game, "Ты пал…", buttons)
            else:
                draw_death_or_win_overlay(game, "Ты выбрался с сокровищами!", buttons)
            pygame.display.flip()
            continue

    pygame.quit()

if __name__ == "__main__":
    main()