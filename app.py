from __future__ import annotations

import pygame

from loading import LoadingScene
from menu import MenuScene
from modes import GameMode
from scene import Scene
from settings import TITLE, VIRTUAL_W, VIRTUAL_H, WINDOWED_SIZE, FPS


class App:
    """Okno, wirtualny ekran 1920x1080 ze skalowaniem (letterbox), pętla główna i aktywna scena."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.fullscreen = False
        self.window = self._create_window()
        # Wirtualny ekran 1920x1080 - cała gra rysuje tutaj, potem skalujemy z letterboxingiem
        self.canvas = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene: Scene = MenuScene(self)

    # --- sceny ---
    def change_scene(self, scene: Scene) -> None:
        self.scene = scene

    def go_to_menu(self) -> None:
        self.change_scene(MenuScene(self))

    def start_game(self, mode: GameMode) -> None:
        """Ekran wczytywania, a po nim scena wybranego trybu."""
        self.change_scene(LoadingScene(self, mode))

    def quit(self) -> None:
        self.running = False

    # --- okno ---
    def _create_window(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.window = self._create_window()

    def _viewport(self) -> tuple[float, pygame.Vector2, tuple[int, int]]:
        """Zwraca (skala, lewy górny róg obrazu w oknie, rozmiar obrazu) dla letterboxingu."""
        win_w, win_h = self.window.get_size()
        scale = min(win_w / VIRTUAL_W, win_h / VIRTUAL_H)
        size = (round(VIRTUAL_W * scale), round(VIRTUAL_H * scale))
        origin = pygame.Vector2((win_w - size[0]) // 2, (win_h - size[1]) // 2)
        return scale, origin, size

    def mouse_virtual_pos(self) -> pygame.Vector2:
        """Pozycja kursora na wirtualnym ekranie 1920x1080 (do UI)."""
        scale, origin, _ = self._viewport()
        return (pygame.Vector2(pygame.mouse.get_pos()) - origin) / scale

    def _present(self) -> None:
        """Skaluje canvas 16:9 do okna z zachowaniem proporcji (czarne pasy na 16:10)."""
        _, origin, size = self._viewport()
        scaled = pygame.transform.smoothscale(self.canvas, size)
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, origin)
        pygame.display.flip()

    # --- pętla ---
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                else:
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.scene.draw(self.canvas)
            self._present()
        pygame.quit()
