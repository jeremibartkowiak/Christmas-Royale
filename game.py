from __future__ import annotations

import pygame

from arena import ArenaScene
from camera import Camera
from entities import Bot, Player
from objects import Obstacle
from ui import EliminatedScreen
from weapons import Gun


class GameScene(ArenaScene):
    """Tryb testowy (debug): arena z nieruchomymi botami i ekranem eliminacji (Respawn / Quit)."""

    RESPAWN_POS = (0, 0)

    def __init__(self, app):
        super().__init__(app)
        self.player = Player(*self.RESPAWN_POS)
        self.eliminated_screen = EliminatedScreen()
        # Obiekty świata (poza graczem). Kolizje: flaga `collidable` w konstruktorze obiektu.
        self.objects = [
            Bot("Bot1", 400, -250), Bot("Bot2", -500, 200), Bot("Bot3", 300, 450),
            Bot("Bot4", -700, -150, gun=Gun(pygame.Vector2(-700, -150), name="Pistol", fire_rate=1.0,
                                           magazine_size=9999, damage=10)),
            Obstacle(-300, -300, 400, 40),
            Obstacle(250, 100, 40, 300),
            Obstacle(-150, 350, 100, 100, color=(120, 90, 60)),
        ]
        self.camera = Camera(self.player.pos)

    def respawn(self) -> None:
        self.player = Player(*self.RESPAWN_POS)
        self.player_alive = True
        self.camera.pos = pygame.Vector2(self.player.pos)

    def handle_dead_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            button = self.eliminated_screen.button_at(self.app.mouse_virtual_pos())
            if button == "respawn":
                self.respawn()
            elif button == "quit":
                self.app.quit()

    def update_world(self, dt: float) -> None:
        if self.player_alive:
            self._update_player(dt)
        for bot in [o for o in self.objects if isinstance(o, Bot)]:
            result = bot.update(dt, self._targets())
            if result:
                self._handle_shot(result, bot.gun, bot)

    def draw_overlay(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        if not self.player_alive:
            self.eliminated_screen.draw(surface, mouse)
