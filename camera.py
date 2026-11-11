import math

import pygame

from settings import VIRTUAL_W, VIRTUAL_H


class Camera:
    """Kamera z płynnym podążaniem (lerp niezależny od FPS). Pozycja = środek widoku w świecie."""

    FOLLOW_SPEED = 6.0  # im wyżej, tym ciaśniej kamera trzyma gracza

    def __init__(self, target_pos: pygame.Vector2):
        self.pos = pygame.Vector2(target_pos)

    @property
    def offset(self) -> pygame.Vector2:
        """Lewy górny róg widoku w współrzędnych świata."""
        return self.pos - pygame.Vector2(VIRTUAL_W / 2, VIRTUAL_H / 2)

    def update(self, dt: float, target_pos: pygame.Vector2) -> None:
        t = 1 - math.exp(-self.FOLLOW_SPEED * dt)
        self.pos += (target_pos - self.pos) * t
