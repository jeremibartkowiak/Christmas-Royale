from __future__ import annotations

import math

import pygame

from play_menu import PlayCard
from scene import Scene
from settings import VIRTUAL_W, VIRTUAL_H, GRID_STEP, GRID_COLOR, PLAYER_NAME
from widgets import Button


class MenuScene(Scene):
    """Menu główne (lobby): tło z postacią, górny pasek i przycisk Play, który otwiera kartę wyboru trybu."""

    BAR_H = 90
    BG_COLOR = (22, 28, 44)
    BAR_COLOR = (12, 15, 24)
    ACCENT = (255, 210, 80)
    GREEN = (60, 185, 75)
    GREEN_HOVER = (85, 215, 100)
    TITLE_SIZE = 52
    PLAY_SIZE = (440, 110)
    PLAY_FONT_SIZE = 72
    QUIT_SIZE = (150, 56)
    CHAR_SIZE = 170  # placeholder postaci w lobby (niebieski kwadrat)
    CHAR_COLOR = (40, 90, 255)
    CHAR_NAME_SIZE = 60

    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.title_font = pygame.font.Font(None, self.TITLE_SIZE)
        self.title_font.set_bold(True)
        self.name_font = pygame.font.Font(None, self.CHAR_NAME_SIZE)
        small_font = pygame.font.Font(None, 36)
        play_font = pygame.font.Font(None, self.PLAY_FONT_SIZE)
        play_font.set_bold(True)
        self.play_button = Button(pygame.Rect(0, 0, *self.PLAY_SIZE), "PLAY", play_font,
                                  self.GREEN, self.GREEN_HOVER, border_radius=12)
        self.play_button.rect.center = (VIRTUAL_W // 2, VIRTUAL_H - 130)
        self.quit_button = Button(pygame.Rect(0, 0, *self.QUIT_SIZE), "Quit", small_font)
        self.quit_button.rect.midright = (VIRTUAL_W - 30, self.BAR_H // 2)
        self.card = PlayCard(self.app, top=self.BAR_H)
        self.card_open = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.card_open:
            if self.card.handle_event(event) == "close":
                self.card_open = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.mouse_virtual_pos()
            if self.play_button.hit(pos):
                self.card_open = True
            elif self.quit_button.hit(pos):
                self.app.quit()

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self, surface: pygame.Surface) -> None:
        mouse = self.app.mouse_virtual_pos()
        self._draw_background(surface)
        if self.card_open:
            self.card.draw(surface, mouse)
        else:
            self.play_button.draw(surface, mouse)
        self._draw_bar(surface, mouse)

    def _draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(self.BG_COLOR)
        for x in range(0, VIRTUAL_W, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, VIRTUAL_H))
        for y in range(0, VIRTUAL_H, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (0, y), (VIRTUAL_W, y))
        # Postać w lobby (placeholder) lekko "lewituje", pod nią cień
        cx, cy = VIRTUAL_W // 2, VIRTUAL_H // 2 + 20
        bob = math.sin(self.time * 2.0) * 10
        shadow = pygame.Surface((self.CHAR_SIZE, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        surface.blit(shadow, shadow.get_rect(center=(cx, cy + self.CHAR_SIZE // 2 + 50)))
        body = pygame.Rect(0, 0, self.CHAR_SIZE, self.CHAR_SIZE)
        body.center = (cx, cy + bob)
        pygame.draw.rect(surface, self.CHAR_COLOR, body)
        name = self.name_font.render(PLAYER_NAME, True, (255, 255, 255))
        surface.blit(name, name.get_rect(midbottom=(cx, body.top - 24)))

    def _draw_bar(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        pygame.draw.rect(surface, self.BAR_COLOR, (0, 0, VIRTUAL_W, self.BAR_H))
        pygame.draw.line(surface, self.ACCENT, (0, self.BAR_H), (VIRTUAL_W, self.BAR_H), 3)
        title = self.title_font.render("CHRISTMAS ROYALE", True, (255, 255, 255))
        surface.blit(title, title.get_rect(midleft=(40, self.BAR_H // 2)))
        self.quit_button.draw(surface, mouse)
