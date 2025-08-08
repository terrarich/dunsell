# -*- coding: utf-8 -*-
import json
import os
import pygame
from typing import Dict, Any
from config import TILE


def ensure_maps_dir() -> str:
    maps_dir = os.path.join(os.getcwd(), "maps")
    os.makedirs(maps_dir, exist_ok=True)
    return maps_dir


def save_map(filepath: str, data: Dict[str, Any]) -> None:
    ensure_maps_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_map(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def serialize_game_to_map(g) -> Dict[str, Any]:
    tiles = g.tiles
    treasures = []
    for it in g.treasures:
        tx = int(it["pos"].x // TILE)
        ty = int(it["pos"].y // TILE)
        treasures.append({"tx": tx, "ty": ty, "type": it["type"]})

    enemies = []
    for e in g.enemies:
        tx = int(e["pos"].x // TILE)
        ty = int(e["pos"].y // TILE)
        enemies.append({"tx": tx, "ty": ty, "kind": e["kind"], "hp": e.get("hp", 3)})

    exit_obj = None
    if g.exit_rect is not None:
        exit_obj = {"tx": int(g.exit_rect.x // TILE), "ty": int(g.exit_rect.y // TILE), "w": int(g.exit_rect.w // TILE), "h": int(g.exit_rect.h // TILE)}

    shop = {
        "tx": int(g.shop_rect.x // TILE),
        "ty": int(g.shop_rect.y // TILE),
        "w": int(g.shop_rect.w // TILE),
        "h": int(g.shop_rect.h // TILE),
    }

    spawn = {"tx": int(g.spawn_tx), "ty": int(g.spawn_ty)}

    return {
        "map_w": g.MAP_W,
        "map_h": g.MAP_H,
        "tiles": tiles,
        "treasures": treasures,
        "enemies": enemies,
        "exit": exit_obj,
        "shop": shop,
        "spawn": spawn,
        "target_gold": g.TARGET_GOLD,
        "breakable_walls": g.breakable_walls,
    }


def apply_map_to_game(g, data: Dict[str, Any]) -> None:
    from mapgen import world_to_tile
    g.MAP_W = int(data.get("map_w", g.MAP_W))
    g.MAP_H = int(data.get("map_h", g.MAP_H))
    g.tiles = data["tiles"]

    g.treasures.clear()
    for it in data.get("treasures", []):
        g.treasures.append({
            "pos": pygame.Vector2(it["tx"] * TILE + TILE/2, it["ty"] * TILE + TILE/2),
            "type": int(it.get("type", 0))
        })

    g.enemies.clear()
    for e in data.get("enemies", []):
        g.enemies.append({
            "pos": pygame.Vector2(e["tx"] * TILE + TILE/2, e["ty"] * TILE + TILE/2),
            "hp": int(e.get("hp", 3)),
            "t": 0.0,
            "kind": e.get("kind", "chaser"),
            "state": "wander",
            "atk_cd": 0.0,
        })

    shop = data.get("shop")
    if shop:
        g.shop_rect.x = int(shop["tx"]) * TILE
        g.shop_rect.y = int(shop["ty"]) * TILE
        g.shop_rect.w = int(shop.get("w", 6)) * TILE
        g.shop_rect.h = int(shop.get("h", 4)) * TILE

    ex = data.get("exit")
    g.exit_rect = None
    if ex:
        g.exit_rect = pygame.Rect(int(ex["tx"]) * TILE, int(ex["ty"]) * TILE, int(ex.get("w", 2)) * TILE, int(ex.get("h", 2)) * TILE)

    spawn = data.get("spawn")
    if spawn:
        g.spawn_tx = int(spawn["tx"]) ; g.spawn_ty = int(spawn["ty"])
    g.player["pos"] = pygame.Vector2(g.spawn_tx * TILE + TILE/2, g.spawn_ty * TILE + TILE/2)

    g.TARGET_GOLD = int(data.get("target_gold", g.TARGET_GOLD))
    g.exit_open = False
    
    # Загружаем ломаемые стены
    g.breakable_walls = data.get("breakable_walls", {})
    # Конвертируем ключи из строк в кортежи
    if g.breakable_walls:
        converted_walls = {}
        for key_str, hp in g.breakable_walls.items():
            if isinstance(key_str, str):
                # Парсим строку "(x, y)" в кортеж
                key_str = key_str.strip("()")
                x, y = map(int, key_str.split(","))
                converted_walls[(x, y)] = hp
            else:
                converted_walls[key_str] = hp
        g.breakable_walls = converted_walls

