# -*- coding: utf-8 -*-
import pygame
import os
from typing import Tuple
from config import SCREEN_W, SCREEN_H, TILE, COL_BG, COL_WALL, COL_FLOOR, TREASURE_TYPES, COL_GOLD, draw_round_rect
from mapgen import in_bounds
from map_io import ensure_maps_dir, save_map, load_map, apply_map_to_game


BRUSH_WALL = 1
BRUSH_BREAKABLE_WALL = 6  # Новый тип для ломаемых стен
BRUSH_FLOOR = 0
BRUSH_TREASURE = 2
BRUSH_ENEMY = 3
BRUSH_EXIT = 4
BRUSH_SPAWN = 5


def run_map_editor(g_factory) -> None:
    pygame.init()
    # гарантируем явное создание окна нужного размера
    # Увеличенное окно редактора
    editor_w, editor_h = max(1280, SCREEN_W), max(768, SCREEN_H)
    screen = pygame.display.set_mode((editor_w, editor_h))
    pygame.display.set_caption("DunSell — Редактор карт")
    
    # Устанавливаем иконку окна редактора
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
    font = pygame.font.SysFont("consolas", 18)

    # Получаем заготовленный игровой объект для хранения карты
    g = g_factory()
    # Стартуем с полностью пустой карты: без стен и объектов
    g.tiles = [[0 for _ in range(g.MAP_W)] for __ in range(g.MAP_H)]
    g.treasures = []
    g.enemies = []
    g.exit_rect = None

    brush = BRUSH_FLOOR
    treasure_type = 0
    running = True
    painting = False
    paint_button = 1  # 1 - ЛКМ, 3 - ПКМ
    move_mode = False
    selected = {"kind": None, "index": -1}
    # Камера и зум редактора
    cam = pygame.Vector2(0.0, 0.0)
    zoom = 1.0  # 0.25 .. 3.0
    is_panning = False
    pan_start = pygame.Vector2(0.0, 0.0)
    cam_start = pygame.Vector2(0.0, 0.0)
    # Скролл панели инструментов
    toolbar_scroll = 0
    # Имя файла и флаг изменения
    current_map_name = ""
    dirty = False

    def update_title():
        name = f" — {current_map_name}" if current_map_name else ""
        star = " *" if dirty else ""
        pygame.display.set_caption(f"DunSell — Редактор карт{name}{star}")

    # Кнопки панели инструментов
    def compute_toolbar():
        # Скроллируемая панель инструментов
        rects = {"_items": [
            ("brush", BRUSH_WALL, "Стены"),
            ("brush", BRUSH_BREAKABLE_WALL, "Ломаемые"),
            ("brush", BRUSH_FLOOR, "Пол"),
            ("brush", BRUSH_TREASURE, "Сокровище"),
            ("brush", BRUSH_ENEMY, "Враг"),
            ("brush", BRUSH_EXIT, "Выход"),
            ("brush", BRUSH_SPAWN, "Спавн"),
            ("move", 0, "Перемещение"),
            ("open", 0, "Открыть"),
            ("new", 0, "Новая"),
            ("save", 0, "Сохранить"),
        ], "_btn_w": 140, "_btn_h": 34, "_gap": 10, "_x0": 16}
        return rects

    toolbar_rects = compute_toolbar()

    def draw_toolbar():
        panel_h = 110
        panel = pygame.Surface((screen.get_width(), panel_h), pygame.SRCALPHA)
        draw_round_rect(panel, pygame.Rect(8, 4, panel.get_width() - 16, panel_h - 8), (0, 0, 0, 140), radius=12)

        # Прокручиваемая полоса кнопок
        viewport = pygame.Rect(16, 10, panel.get_width() - 32, 40)
        content = pygame.Surface((3000, viewport.h), pygame.SRCALPHA)
        items = toolbar_rects["_items"]
        x = toolbar_rects["_x0"]
        btn_w = toolbar_rects["_btn_w"]; btn_h = toolbar_rects["_btn_h"]; gap = toolbar_rects["_gap"]
        toolbar_rects["_click_map"] = {}
        for kind, bid, label in items:
            r = pygame.Rect(x, 0, btn_w, btn_h)
            selected_btn = (kind == "brush" and brush == bid) or (kind == "move" and move_mode)
            base = (40, 70, 100) if selected_btn else (40, 40, 50)
            border = (120, 180, 255) if selected_btn else (90, 140, 200)
            draw_round_rect(content, r, base, radius=8, border=2, border_color=border)
            txt = font.render(label, True, (230, 235, 240))
            content.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            # Кликом по экрану — учёт скролла и вьюпорта
            vis_r = pygame.Rect(r.x - toolbar_scroll + viewport.x, r.y + viewport.y, r.w, r.h)
            toolbar_rects["_click_map"][(kind, bid)] = vis_r
            x += btn_w + gap
        panel.blit(content, viewport.topleft, area=pygame.Rect(toolbar_scroll, 0, viewport.w, viewport.h))

        # переключатель сокровищ
        t_y = 60
        r_prev = pygame.Rect(16, t_y, 36, 30)
        r_next = pygame.Rect(16 + 36 + 8, t_y, 36, 30)
        r_show = pygame.Rect(16 + 36 + 8 + 36 + 8, t_y, 260, 30)
        draw_round_rect(panel, r_prev, (50, 50, 60), radius=6, border=2, border_color=(90, 140, 200))
        draw_round_rect(panel, r_next, (50, 50, 60), radius=6, border=2, border_color=(90, 140, 200))
        panel.blit(font.render("<", True, (230, 235, 240)), (r_prev.centerx - 5, r_prev.centery - 9))
        panel.blit(font.render(">", True, (230, 235, 240)), (r_next.centerx - 5, r_next.centery - 9))
        draw_round_rect(panel, r_show, (20, 20, 30), radius=6, border=2, border_color=(90, 140, 200))
        t = TREASURE_TYPES[treasure_type]
        panel.blit(font.render(f"Тип: {t['name']}", True, (230, 235, 240)), (r_show.x + 10, r_show.y + 5))
        pygame.draw.circle(panel, t["color"], (r_show.right - 16, r_show.centery), 8)

        screen.blit(panel, (0, 0))

    def is_over_toolbar(mx, my) -> bool:
        return my < 110

    def handle_toolbar_click(mx, my):
        nonlocal brush, treasure_type, move_mode, toolbar_scroll, current_map_name, dirty
        for (kind, bid), r in toolbar_rects.get("_click_map", {}).items():
            if r.collidepoint(mx, my):
                if kind == "brush":
                    brush = bid; move_mode = False
                elif kind == "move":
                    move_mode = not move_mode
                elif kind == "open":
                    name = open_map_dialog()
                    if name:
                        path = os.path.join(ensure_maps_dir(), name)
                        try:
                            data = load_map(path)
                            apply_map_to_game(g, data)
                            current_map_name = name
                            dirty = False
                            update_title()
                        except Exception as ex:
                            print("Open failed:", ex)
                elif kind == "new":
                    g.tiles = [[0 for _ in range(g.MAP_W)] for __ in range(g.MAP_H)]
                    g.treasures.clear(); g.enemies.clear(); g.exit_rect = None
                    current_map_name = ""; dirty = True; update_title()
                elif kind == "save":
                    perform_save(save_as=False)
                elif kind == "saveas":
                    perform_save(save_as=True)
                return True
        # сокровища +/-
        t_y = 60
        r_prev = pygame.Rect(16, t_y, 36, 30)
        r_next = pygame.Rect(16 + 36 + 8, t_y, 36, 30)
        if r_prev.collidepoint(mx, my):
            treasure_type = (treasure_type - 1) % len(TREASURE_TYPES); return True
        if r_next.collidepoint(mx, my):
            treasure_type = (treasure_type + 1) % len(TREASURE_TYPES); return True
        return False

    def open_map_dialog() -> str:
        # Простой диалог выбора файла из maps/
        maps_dir = ensure_maps_dir()
        files = [f for f in os.listdir(maps_dir) if f.lower().endswith('.json')]
        if not files:
            return ""
        idx = 0
        panel_w, panel_h = 640, 420
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return ""
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: return ""
                    if e.key == pygame.K_UP: idx = (idx - 1) % len(files)
                    if e.key == pygame.K_DOWN: idx = (idx + 1) % len(files)
                    if e.key == pygame.K_RETURN: return files[idx]
            overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0,0,0,160)); screen.blit(overlay, (0,0))
            panel.fill((0,0,0,0))
            draw_round_rect(panel, panel.get_rect(), (0,0,0,220), radius=12, border=2, border_color=(90,140,200))
            title = font.render("Выберите карту из maps/", True, (230,240,255))
            panel.blit(title, (20, 20))
            base_y = 64
            for i, name in enumerate(files):
                sel = (i == idx)
                img = font.render(name, True, (230,235,240) if sel else (150,155,165))
                x = 22; y = base_y + i * 26
                if sel:
                    pygame.draw.rect(panel, (40,70,100), pygame.Rect(x-8, y-4, img.get_width()+16, img.get_height()+8), border_radius=8)
                panel.blit(img, (x, y))
            screen.blit(panel, (screen.get_width()//2 - panel_w//2, screen.get_height()//2 - panel_h//2))
            pygame.display.flip(); pygame.time.delay(16)

    # Перемещение объектов
    dragging = {
        "kind": None,   # 'treasure'|'enemy'|'exit'|'spawn'|'shop'
        "index": -1,
        "offset": pygame.Vector2(0,0),
    }

    def pick_object_at(tx: int, ty: int):
        # проверяем выход
        if g.exit_rect and g.exit_rect.collidepoint(tx*TILE + TILE//2, ty*TILE + TILE//2):
            dragging["kind"] = "exit"; dragging["index"] = 0; dragging["offset"] = pygame.Vector2(0,0); selected["kind"] = "exit"; selected["index"] = 0; return True
        # магазин
        if g.shop_rect and g.shop_rect.collidepoint(tx*TILE + TILE//2, ty*TILE + TILE//2):
            dragging["kind"] = "shop"; dragging["index"] = 0; dragging["offset"] = pygame.Vector2(0,0); selected["kind"] = "shop"; selected["index"] = 0; return True
        # проверяем спавн
        if (g.spawn_tx, g.spawn_ty) == (tx, ty):
            dragging["kind"] = "spawn"; dragging["index"] = 0; dragging["offset"] = pygame.Vector2(0,0); selected["kind"] = "spawn"; selected["index"] = 0; return True
        # проверяем сокровища
        for i, it in enumerate(g.treasures):
            if int(it["pos"].x // TILE) == tx and int(it["pos"].y // TILE) == ty:
                dragging["kind"] = "treasure"; dragging["index"] = i; dragging["offset"] = pygame.Vector2(0,0); selected["kind"] = "treasure"; selected["index"] = i; return True
        # проверяем врагов
        for i, en in enumerate(g.enemies):
            if int(en["pos"].x // TILE) == tx and int(en["pos"].y // TILE) == ty:
                dragging["kind"] = "enemy"; dragging["index"] = i; dragging["offset"] = pygame.Vector2(0,0); selected["kind"] = "enemy"; selected["index"] = i; return True
        return False

    def drag_move_to(tx: int, ty: int):
        nonlocal dirty
        if dragging["kind"] == "exit":
            g.exit_rect.x = tx*TILE; g.exit_rect.y = ty*TILE
        elif dragging["kind"] == "shop":
            g.shop_rect.x = tx*TILE; g.shop_rect.y = ty*TILE
        elif dragging["kind"] == "spawn":
            g.spawn_tx, g.spawn_ty = tx, ty
        elif dragging["kind"] == "treasure" and 0 <= dragging["index"] < len(g.treasures):
            g.treasures[dragging["index"]]["pos"] = pygame.Vector2(tx*TILE + TILE/2, ty*TILE + TILE/2)
        elif dragging["kind"] == "enemy" and 0 <= dragging["index"] < len(g.enemies):
            g.enemies[dragging["index"]]["pos"] = pygame.Vector2(tx*TILE + TILE/2, ty*TILE + TILE/2)
        else:
            return
        dirty = True; update_title()

    def clear_drag():
        dragging["kind"] = None; dragging["index"] = -1

    def paint_at(tx: int, ty: int, button: int):
        nonlocal dirty
        if not in_bounds(g, tx, ty):
            return
        if button == 1:
            if brush == BRUSH_WALL:
                if g.tiles[ty][tx] != WALL_NORMAL:
                    g.tiles[ty][tx] = WALL_NORMAL; dirty = True
            elif brush == BRUSH_BREAKABLE_WALL:
                if g.tiles[ty][tx] != WALL_BREAKABLE:
                    g.tiles[ty][tx] = WALL_BREAKABLE; dirty = True
            elif brush == BRUSH_FLOOR:
                if g.tiles[ty][tx] != 0:
                    g.tiles[ty][tx] = 0; dirty = True
            elif brush == BRUSH_TREASURE:
                # не дублировать при удержании — проверим есть ли уже в этой клетке
                if not any(int(it["pos"].x // TILE) == tx and int(it["pos"].y // TILE) == ty for it in g.treasures):
                    g.treasures.append({"pos": pygame.Vector2(tx*TILE + TILE/2, ty*TILE + TILE/2), "type": treasure_type}); dirty = True
            elif brush == BRUSH_ENEMY:
                if not any(int(en["pos"].x // TILE) == tx and int(en["pos"].y // TILE) == ty for en in g.enemies):
                    g.enemies.append({"pos": pygame.Vector2(tx*TILE + TILE/2, ty*TILE + TILE/2), "hp": 3, "t": 0.0, "kind": "chaser", "state": "wander", "atk_cd": 0.0}); dirty = True
            elif brush == BRUSH_EXIT:
                g.exit_rect = pygame.Rect(tx*TILE, ty*TILE, 2*TILE, 2*TILE); dirty = True
            elif brush == BRUSH_SPAWN:
                g.spawn_tx, g.spawn_ty = int(tx), int(ty); dirty = True
        elif button == 3:
            if brush == BRUSH_WALL or brush == BRUSH_BREAKABLE_WALL:
                if g.tiles[ty][tx] != 0:
                    g.tiles[ty][tx] = 0; dirty = True
            elif brush == BRUSH_FLOOR:
                if g.tiles[ty][tx] != WALL_NORMAL:
                    g.tiles[ty][tx] = WALL_NORMAL; dirty = True
            elif brush == BRUSH_TREASURE:
                before = len(g.treasures)
                g.treasures = [it for it in g.treasures if not (int(it["pos"].x // TILE) == tx and int(it["pos"].y // TILE) == ty)]
                if len(g.treasures) != before: dirty = True
            elif brush == BRUSH_ENEMY:
                before = len(g.enemies)
                g.enemies = [en for en in g.enemies if not (int(en["pos"].x // TILE) == tx and int(en["pos"].y // TILE) == ty)]
                if len(g.enemies) != before: dirty = True
            elif brush == BRUSH_EXIT:
                if g.exit_rect is not None:
                    g.exit_rect = None; dirty = True
            # спавн правой кнопкой не удаляем
        if dirty:
            update_title()

    def draw_ui():
        screen.fill(COL_BG)
        # Сетка и тайлы (с учётом камеры и зума)
        for ty in range(g.MAP_H):
            for tx in range(g.MAP_W):
                r = pygame.Rect(int((tx*TILE - cam.x) * zoom), int((ty*TILE - cam.y) * zoom), int(TILE * zoom), int(TILE * zoom))
                if g.tiles[ty][tx] == WALL_NORMAL:
                    col = COL_WALL
                elif g.tiles[ty][tx] == WALL_BREAKABLE:
                    col = COL_BREAKABLE_WALL
                else:
                    col = COL_FLOOR
                pygame.draw.rect(screen, col, r)
                pygame.draw.rect(screen, (30,30,35), r, 1)

        # Сокровища
        for it in g.treasures:
            px = int((it["pos"].x - cam.x) * zoom)
            py = int((it["pos"].y - cam.y) * zoom)
            pygame.draw.circle(screen, TREASURE_TYPES[it["type"]]["color"], (px, py), max(3, int(5 * zoom)))

        # Враги
        for e in g.enemies:
            px = int((e["pos"].x - cam.x) * zoom)
            py = int((e["pos"].y - cam.y) * zoom)
            pygame.draw.circle(screen, (200, 80, 80), (px, py), max(4, int(8 * zoom)), 2)

        # Магазин и выход/спавн
        shop_vis = pygame.Rect(int((g.shop_rect.x - cam.x) * zoom), int((g.shop_rect.y - cam.y) * zoom), int(g.shop_rect.w * zoom), int(g.shop_rect.h * zoom))
        draw_round_rect(screen, shop_vis, (35,55,80), radius=6, border=2, border_color=(90,140,200))
        if g.exit_rect:
            exit_vis = pygame.Rect(int((g.exit_rect.x - cam.x) * zoom), int((g.exit_rect.y - cam.y) * zoom), int(g.exit_rect.w * zoom), int(g.exit_rect.h * zoom))
            draw_round_rect(screen, exit_vis, (120, 255, 160), radius=6, border=2, border_color=(30, 60, 40))
        pygame.draw.circle(screen, (255,255,255), (int(((g.spawn_tx*TILE + TILE//2) - cam.x) * zoom), int(((g.spawn_ty*TILE + TILE//2) - cam.y) * zoom)), max(3, int(6 * zoom)))

        # Панель инструментов (кнопки)
        draw_toolbar()

        # Выделение/стрелки на выбранном объекте
        if selected["kind"] is not None:
            if selected["kind"] == "treasure" and 0 <= selected["index"] < len(g.treasures):
                cx, cy = g.treasures[selected["index"]]["pos"].x, g.treasures[selected["index"]]["pos"].y
            elif selected["kind"] == "enemy" and 0 <= selected["index"] < len(g.enemies):
                cx, cy = g.enemies[selected["index"]]["pos"].x, g.enemies[selected["index"]]["pos"].y
            elif selected["kind"] == "exit" and g.exit_rect:
                cx, cy = g.exit_rect.centerx, g.exit_rect.centery
            elif selected["kind"] == "spawn":
                cx, cy = g.spawn_tx*TILE + TILE/2, g.spawn_ty*TILE + TILE/2
            elif selected["kind"] == "shop" and g.shop_rect:
                cx, cy = g.shop_rect.centerx, g.shop_rect.centery
            else:
                cx = cy = None
            if cx is not None:
                cx = int((cx - cam.x) * zoom); cy = int((cy - cam.y) * zoom)
                col = (255, 230, 120)
                s = max(10, int(16 * zoom))
                pygame.draw.line(screen, col, (cx - s, cy), (cx + s, cy), 2)
                pygame.draw.line(screen, col, (cx, cy - s), (cx, cy + s), 2)
                pygame.draw.polygon(screen, col, [(cx + s, cy), (cx + s - 6, cy - 5), (cx + s - 6, cy + 5)])
                pygame.draw.polygon(screen, col, [(cx - s, cy), (cx - s + 6, cy - 5), (cx - s + 6, cy + 5)])
                pygame.draw.polygon(screen, col, [(cx, cy - s), (cx - 5, cy - s + 6), (cx + 5, cy - s + 6)])
                pygame.draw.polygon(screen, col, [(cx, cy + s), (cx - 5, cy + s - 6), (cx + 5, cy + s - 6)])

        pygame.display.flip()
        # на всякий случай, чтобы окно не скрывалось мгновенно
        pygame.event.pump()

    def prompt_filename() -> str:
        # Модальный ввод имени файла (без .json)
        name = ""
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ")
        panel_w, panel_h = 520, 160
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return ""
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return ""
                    if e.key == pygame.K_RETURN:
                        return name.strip()
                    if e.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        ch = e.unicode
                        if ch and ch in allowed and len(name) < 64:
                            name += ch

            # затемнение
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0,0,0,160))
            screen.blit(overlay, (0,0))

            # панель
            panel.fill((0,0,0,0))
            draw_round_rect(panel, panel.get_rect(), (0,0,0,200), radius=12, border=2, border_color=(90,140,200))
            title = font.render("Введите имя карты (без .json):", True, (230,240,255))
            panel.blit(title, (20, 20))
            box = pygame.Rect(20, 60, panel_w - 40, 36)
            draw_round_rect(panel, box, (20,20,30), radius=8, border=2, border_color=(90,140,200))
            text_img = font.render(name, True, (230,235,240))
            panel.blit(text_img, (box.x + 10, box.y + 8))
            hint = font.render("Enter — сохранить, Esc — отмена", True, (180,185,195))
            panel.blit(hint, (20, 110))

            screen.blit(panel, (SCREEN_W//2 - panel_w//2, SCREEN_H//2 - panel_h//2))
            pygame.display.flip()
            pygame.time.delay(16)

    def prompt_target_gold() -> int:
        # Ввод целевого числа золота (TARGET_GOLD)
        value = str(int(getattr(g, 'TARGET_GOLD', 500)))
        panel_w, panel_h = 420, 180
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return None
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return None
                    if e.key == pygame.K_RETURN:
                        try:
                            return max(0, int(value))
                        except:
                            pass
                    if e.key == pygame.K_BACKSPACE:
                        value = value[:-1]
                    else:
                        ch = e.unicode
                        if ch and ch.isdigit() and len(value) < 9:
                            value += ch
            overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0,0,0,160)); screen.blit(overlay, (0,0))
            panel.fill((0,0,0,0))
            draw_round_rect(panel, panel.get_rect(), (0,0,0,220), radius=12, border=2, border_color=(90,140,200))
            title = font.render("Цель золота для карты:", True, (230,240,255))
            panel.blit(title, (20, 20))
            box = pygame.Rect(20, 60, panel_w - 40, 40)
            draw_round_rect(panel, box, (20,20,30), radius=8, border=2, border_color=(90,140,200))
            txt = font.render(value, True, (230,235,240))
            panel.blit(txt, (box.x + 10, box.y + 10))
            hint = font.render("Enter — подтвердить, Esc — отмена", True, (180,185,195))
            panel.blit(hint, (20, 116))
            screen.blit(panel, (screen.get_width()//2 - panel_w//2, screen.get_height()//2 - panel_h//2))
            pygame.display.flip(); pygame.time.delay(16)

    def perform_save(save_as: bool = False):
        nonlocal current_map_name, dirty
        tgt = prompt_target_gold()
        if tgt is None:
            return
        g.TARGET_GOLD = int(tgt)
        name = current_map_name if (current_map_name and not save_as) else ""
        if not name:
            name = prompt_filename()
            if not name:
                return
            if not name.lower().endswith('.json'):
                name += '.json'
            current_map_name = name
        filepath = os.path.join(ensure_maps_dir(), name)
        from map_io import serialize_game_to_map
        data = serialize_game_to_map(g)
        save_map(filepath, data)
        dirty = False
        update_title()
        print("Saved:", filepath)

    def prompt_save_changes() -> str:
        # Возвращает 'save' | 'discard' | 'cancel'
        panel_w, panel_h = 520, 180
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return 'discard'
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: return 'cancel'
                    if e.key == pygame.K_RETURN: return 'save'
                    if e.key == pygame.K_d: return 'discard'
            overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0,0,0,160)); screen.blit(overlay, (0,0))
            panel.fill((0,0,0,0))
            draw_round_rect(panel, panel.get_rect(), (0,0,0,220), radius=12, border=2, border_color=(90,140,200))
            title = font.render("Сохранить изменения перед выходом?", True, (230,240,255))
            panel.blit(title, (20, 24))
            hint = font.render("Enter — сохранить, D — не сохранять, Esc — отмена", True, (180,185,195))
            panel.blit(hint, (20, 100))
            screen.blit(panel, (screen.get_width()//2 - panel_w//2, screen.get_height()//2 - panel_h//2))
            pygame.display.flip(); pygame.time.delay(16)

    while running:
        dt = clock.tick(60) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if dirty:
                        decision = prompt_save_changes()
                        if decision == 'save':
                            perform_save(save_as=False)
                            running = False
                        elif decision == 'discard':
                            running = False
                        else:
                            pass
                    else:
                        running = False
                # Панорамирование стрелками, PgUp/PgDn — зум
                pan_step = 400 * dt / max(0.25, zoom)
                if e.key == pygame.K_LEFT:
                    cam.x -= pan_step
                elif e.key == pygame.K_RIGHT:
                    cam.x += pan_step
                elif e.key == pygame.K_UP:
                    cam.y -= pan_step
                elif e.key == pygame.K_DOWN:
                    cam.y += pan_step
                elif e.key == pygame.K_PAGEUP:
                    old = zoom
                    zoom = min(3.0, zoom * 1.1)
                    mx, my = pygame.mouse.get_pos()
                    world_before = pygame.Vector2(mx/old + cam.x, my/old + cam.y)
                    world_after = pygame.Vector2(mx/zoom + cam.x, my/zoom + cam.y)
                    cam += world_after - world_before
                elif e.key == pygame.K_PAGEDOWN:
                    old = zoom
                    zoom = max(0.25, zoom / 1.1)
                    mx, my = pygame.mouse.get_pos()
                    world_before = pygame.Vector2(mx/old + cam.x, my/old + cam.y)
                    world_after = pygame.Vector2(mx/zoom + cam.x, my/zoom + cam.y)
                    cam += world_after - world_before
                elif e.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    perform_save(save_as=False)
                elif e.key == pygame.K_F12:
                    perform_save(save_as=True)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
                mx, my = pygame.mouse.get_pos()
                # Клик по панели
                if is_over_toolbar(mx, my) and handle_toolbar_click(mx, my):
                    continue
                if e.button == 2:
                    is_panning = True
                    pan_start.update(mx, my)
                    cam_start.update(cam.x, cam.y)
                    continue
                # Рисование на карте
                tx = int((mx/zoom + cam.x) // TILE)
                ty = int((my/zoom + cam.y) // TILE)
                if move_mode and e.button == 1:
                    # Перемещение объектов только в режиме перемещения
                    if not pick_object_at(tx, ty):
                        selected["kind"] = None; selected["index"] = -1
                else:
                    paint_button = e.button
                    painting = True
                    paint_at(tx, ty, paint_button)
            elif e.type == pygame.MOUSEMOTION and painting:
                mx, my = e.pos
                if is_over_toolbar(mx, my):
                    continue
                tx = int((mx/zoom + cam.x) // TILE)
                ty = int((my/zoom + cam.y) // TILE)
                paint_at(tx, ty, paint_button)
            elif e.type == pygame.MOUSEMOTION and dragging["kind"] is not None:
                mx, my = e.pos
                if is_over_toolbar(mx, my):
                    continue
                tx = int((mx/zoom + cam.x) // TILE)
                ty = int((my/zoom + cam.y) // TILE)
                drag_move_to(tx, ty)
            elif e.type == pygame.MOUSEBUTTONUP and e.button in (1, 2, 3):
                painting = False
                if e.button == 2:
                    is_panning = False
                clear_drag()
            elif e.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                mods = pygame.key.get_mods()
                # Если крутим колесо над панелью (или зажали Shift) — горизонтальный скролл панели
                if is_over_toolbar(mx, my) or (mods & pygame.KMOD_SHIFT):
                    btn_w = toolbar_rects["_btn_w"]; gap = toolbar_rects["_gap"]; x0 = toolbar_rects["_x0"]
                    content_w = x0 + len(toolbar_rects["_items"]) * (btn_w + gap) - gap
                    viewport_w = screen.get_width() - 32
                    max_scroll = max(0, content_w - viewport_w)
                    # e.y > 0 — прокрутка вверх (влево по панели)
                    toolbar_scroll = max(0, min(max_scroll, toolbar_scroll - e.y * 60))
                else:
                    # Зум сцены
                    old_zoom = zoom
                    if e.y > 0:
                        zoom = min(3.0, zoom * 1.1)
                    elif e.y < 0:
                        zoom = max(0.25, zoom / 1.1)
                    # Зум к курсору
                    world_before = pygame.Vector2(mx/old_zoom + cam.x, my/old_zoom + cam.y)
                    world_after = pygame.Vector2(mx/zoom + cam.x, my/zoom + cam.y)
                    cam += world_after - world_before

        # Панорамирование средним кликом
        if is_panning:
            mx, my = pygame.mouse.get_pos()
            delta = pygame.Vector2(mx, my) - pan_start
            cam.x = cam_start.x - delta.x/zoom
            cam.y = cam_start.y - delta.y/zoom

        draw_ui()

    # Возвращаемся в игру без закрытия всего pygame, чтобы не ломать главное окно
    return


