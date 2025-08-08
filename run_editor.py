# -*- coding: utf-8 -*-
import pygame
from game_state import Game
from editor import run_map_editor


def make_game():
    pygame.init()
    # создаём минимальный контекст для Game без открытия окна здесь
    dummy_screen = pygame.Surface((1, 1))
    clock = pygame.time.Clock()
    font_small = pygame.font.SysFont("consolas", 18)
    font_mid = pygame.font.SysFont("consolas", 24)
    font_big = pygame.font.SysFont("consolas", 36)
    return Game(dummy_screen, clock, font_small, font_mid, font_big)


if __name__ == "__main__":
    run_map_editor(make_game)


