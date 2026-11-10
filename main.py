import math
import os

os.environ["SDL_RENDER_DRIVER"] = "direct3d"  # musi być przed inicjalizacją Pygame

import pygame

TITLE = "Christmas Royale"
VIRTUAL_W, VIRTUAL_H = 1920, 1080  # rozdzielczość projektowa (16:9)
WINDOWED_SIZE = (1280, 720)
FPS = 144
GRID_STEP = 100
GRID_COLOR = (45, 52, 68)


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


class Player:
    SIZE = 50
    SPEED = 400  # piksele na sekundę

    def __init__(self, x: float, y: float):
        self.pos = pygame.Vector2(x, y)
        # Placeholder (greybox) - później podmiana na wczytany .png
        self.image = pygame.Surface((self.SIZE, self.SIZE))
        self.image.fill((40, 90, 255))

    @property
    def rect(self) -> pygame.Rect:
        return self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self, dt: float, keys) -> None:
        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        if direction.length_squared() > 0:
            direction.normalize_ip()  # brak szybszego ruchu po skosie
        self.pos += direction * self.SPEED * dt

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        surface.blit(self.image, self.rect.move(-round(camera_offset.x), -round(camera_offset.y)))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.fullscreen = False
        self.window = self._create_window()
        # Wirtualny ekran 1920x1080 - cała gra rysuje tutaj, potem skalujemy z letterboxingiem
        self.canvas = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        self.clock = pygame.time.Clock()
        self.running = True
        self.player = Player(0, 0)
        self.camera = Camera(self.player.pos)

    def _create_window(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.window = self._create_window()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()

    def update(self, dt: float) -> None:
        self.player.update(dt, pygame.key.get_pressed())
        self.camera.update(dt, self.player.pos)

    def _draw_grid(self, offset: pygame.Vector2) -> None:
        """Tymczasowa siatka (greybox), żeby było widać ruch kamery po nieograniczonym świecie."""
        ox, oy = round(offset.x), round(offset.y)
        for x in range(-(ox % GRID_STEP), VIRTUAL_W, GRID_STEP):
            pygame.draw.line(self.canvas, GRID_COLOR, (x, 0), (x, VIRTUAL_H))
        for y in range(-(oy % GRID_STEP), VIRTUAL_H, GRID_STEP):
            pygame.draw.line(self.canvas, GRID_COLOR, (0, y), (VIRTUAL_W, y))

    def draw(self) -> None:
        self.canvas.fill((25, 30, 40))
        offset = self.camera.offset
        self._draw_grid(offset)
        self.player.draw(self.canvas, offset)
        self._present()

    def _present(self) -> None:
        """Skaluje canvas 16:9 do okna z zachowaniem proporcji (czarne pasy na 16:10)."""
        win_w, win_h = self.window.get_size()
        scale = min(win_w / VIRTUAL_W, win_h / VIRTUAL_H)
        size = (round(VIRTUAL_W * scale), round(VIRTUAL_H * scale))
        scaled = pygame.transform.smoothscale(self.canvas, size)
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, ((win_w - size[0]) // 2, (win_h - size[1]) // 2))
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
