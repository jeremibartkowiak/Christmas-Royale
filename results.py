from __future__ import annotations

import math

import pygame

from scene import Scene
from scoring import Participant, ranking
from settings import VIRTUAL_W, VIRTUAL_H, GRID_STEP, GRID_COLOR
from widgets import Button


class ResultsScene(Scene):
    """Podium po meczu: Top 3 na tle - #2 po lewej, #1 pośrodku (najwyższy), #3 po prawej."""

    BG_COLOR = (22, 28, 44)
    BASE_Y = 800  # dolna krawędź podestów
    PEDESTAL_W = 300
    SPACING = 340
    # miejsce -> (wysokość podestu, kolor podestu, rozmiar placeholdera postaci)
    PLACES = {
        1: (380, (255, 200, 60), 130),
        2: (290, (190, 195, 205), 100),
        3: (220, (190, 125, 70), 100),
    }
    PLACE_OFFSETS = {2: -1, 1: 0, 3: 1}

    def __init__(self, app, participants: list[Participant]):
        super().__init__(app)
        self.ranked = ranking(participants)
        self.time = 0.0
        self.title_font = pygame.font.Font(None, 96)
        self.title_font.set_bold(True)
        self.rank_font = pygame.font.Font(None, 110)
        self.rank_font.set_bold(True)
        self.points_font = pygame.font.Font(None, 48)
        self.name_font = pygame.font.Font(None, 56)
        self.you_font = pygame.font.Font(None, 48)
        button_font = pygame.font.Font(None, 50)
        self.back_button = Button(pygame.Rect(0, 0, 380, 80), "Back to menu", button_font)
        self.back_button.rect.center = (VIRTUAL_W // 2, VIRTUAL_H - 75)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button.hit(self.app.mouse_virtual_pos()):
                self.app.go_to_menu()

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(self.BG_COLOR)
        for x in range(0, VIRTUAL_W, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, VIRTUAL_H))
        for y in range(0, VIRTUAL_H, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (0, y), (VIRTUAL_W, y))
        title = self.title_font.render("FINAL RESULTS", True, (255, 255, 255))
        surface.blit(title, title.get_rect(midtop=(VIRTUAL_W // 2, 40)))
        for place, participant in enumerate(self.ranked[:3], start=1):
            self._draw_place(surface, place, participant)
        self._draw_player_place(surface)
        self.back_button.draw(surface, self.app.mouse_virtual_pos())

    def _draw_place(self, surface: pygame.Surface, place: int, participant: Participant) -> None:
        height, color, size = self.PLACES[place]
        cx = VIRTUAL_W // 2 + self.PLACE_OFFSETS[place] * self.SPACING
        pedestal = pygame.Rect(0, 0, self.PEDESTAL_W, height)
        pedestal.midbottom = (cx, self.BASE_Y)
        pygame.draw.rect(surface, color, pedestal, border_radius=8)
        dark = (30, 30, 38)
        rank = self.rank_font.render(f"#{place}", True, dark)
        surface.blit(rank, rank.get_rect(midtop=(cx, pedestal.top + 24)))
        points = self.points_font.render(f"{participant.points} pts", True, dark)
        surface.blit(points, points.get_rect(midtop=(cx, pedestal.top + 120)))
        bob = math.sin(self.time * 2.5) * 8 if place == 1 else 0  # zwycięzca lekko się unosi
        body = pygame.Rect(0, 0, size, size)
        body.midbottom = (cx, pedestal.top - 20 + bob)
        pygame.draw.rect(surface, participant.color, body)
        name = self.name_font.render(participant.name, True, (255, 255, 255))
        surface.blit(name, name.get_rect(midbottom=(cx, body.top - 12)))

    def _draw_player_place(self, surface: pygame.Surface) -> None:
        """Gdy gracz nie jest w Top 3, pokazuje jego miejsce pod podium."""
        for index, p in enumerate(self.ranked):
            if p.is_player and index >= 3:
                text = self.you_font.render(f"Your place: #{index + 1}   {p.points} pts", True, (255, 210, 80))
                surface.blit(text, text.get_rect(midtop=(VIRTUAL_W // 2, self.BASE_Y + 30)))
