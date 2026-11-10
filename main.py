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
HUD_FONT_SIZE = 32
HUD_MARGIN = 40
HUD_COLOR = (255, 255, 255)
HUD_EMPTY_COLOR = (255, 80, 80)


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


def raycast(start: pygame.Vector2, direction: pygame.Vector2, max_range: float,
            targets: list["GameObject"], ignore: "GameObject | None" = None
            ) -> tuple[pygame.Vector2, "GameObject | None"]:
    """Hitscan: zwraca (punkt trafienia, trafiony obiekt) - najbliższy kolizyjny obiekt na linii.
    Bez trafienia zwraca punkt na końcu zasięgu i None."""
    end = start + direction * max_range
    best_point, best_obj, best_dist = end, None, math.inf
    for obj in targets:
        if obj is ignore or not obj.collidable:
            continue
        clipped = obj.rect.clipline((start.x, start.y), (end.x, end.y))
        if not clipped:
            continue
        point = pygame.Vector2(clipped[0])  # pierwszy punkt = wejście w obiekt (najbliżej strzelca)
        dist = start.distance_squared_to(point)
        if dist < best_dist:
            best_point, best_obj, best_dist = point, obj, dist
    return best_point, best_obj


class Tracer:
    """Chwilowa linia pokazująca tor strzału (efekt prototypowy)."""

    DURATION = 0.08  # sekundy
    COLOR = (255, 230, 80)
    WIDTH = 3

    def __init__(self, start: pygame.Vector2, end: pygame.Vector2):
        self.start = pygame.Vector2(start)
        self.end = pygame.Vector2(end)
        self.age = 0.0

    @property
    def alive(self) -> bool:
        return self.age < self.DURATION

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        pygame.draw.line(surface, self.COLOR, self.start - camera_offset, self.end - camera_offset, self.WIDTH)


class Gun:
    """Prototypowy pistolet (prostokąt) obracany w stronę celu. Strzela hitscanem."""

    LENGTH = 60
    THICKNESS = 16
    HOLD_DISTANCE = 45  # odległość środka pistoletu od środka gracza
    RANGE = 2000  # zasięg hitscanu (px)

    def __init__(self, owner_pos: pygame.Vector2, automatic: bool = True, fire_rate: float = 6.0,
                 magazine_size: int = 12, reload_time: float = 1.5):
        """automatic: True = ogień ciągły po przytrzymaniu LPM, False = jeden strzał na kliknięcie.
        fire_rate: strzały na sekundę. magazine_size: pojemność magazynka. reload_time: sekundy."""
        self.automatic = automatic
        self.fire_rate = fire_rate
        self.magazine_size = magazine_size
        self.reload_time = reload_time
        self.ammo = magazine_size
        self.reload_left = 0.0  # >0 = trwa przeładowanie
        self.pos = pygame.Vector2(owner_pos)
        self.direction = pygame.Vector2(1, 0)
        self.angle = 0.0  # stopnie, 0 = w prawo
        # Placeholder (greybox) - później podmiana na .png (rysowany "w prawo")
        self.base_image = pygame.Surface((self.LENGTH, self.THICKNESS), pygame.SRCALPHA)  # alfa: rogi po obrocie przezroczyste
        self.base_image.fill((200, 200, 200))
        self.image = self.base_image
        self.cooldown = 0.0

    @property
    def reloading(self) -> bool:
        return self.reload_left > 0

    def update(self, dt: float) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.reloading:
            self.reload_left -= dt
            if self.reload_left <= 0:
                self.reload_left = 0.0
                self.ammo = self.magazine_size

    def start_reload(self) -> None:
        if not self.reloading and self.ammo < self.magazine_size:
            self.reload_left = self.reload_time

    def fire(self, owner: "GameObject", targets: list["GameObject"], trigger_held: bool,
             trigger_pressed: bool) -> "tuple[Tracer, GameObject | None] | None":
        """Oddaje strzał, jeśli spust jest wciśnięty (zależnie od trybu), jest amunicja, nie trwa
        przeładowanie i minął cooldown. Zwraca (efekt linii, trafiony obiekt) lub None."""
        wants_fire = trigger_held if self.automatic else trigger_pressed
        if not wants_fire or self.reloading or self.ammo <= 0 or self.cooldown > 0:
            return None
        self.ammo -= 1
        self.cooldown = 1.0 / self.fire_rate
        hit_point, hit_obj = raycast(owner.pos, self.direction, self.RANGE, targets, ignore=owner)
        muzzle = self.pos + self.direction * (self.LENGTH / 2)
        return Tracer(muzzle, hit_point), hit_obj

    def aim_at(self, owner_pos: pygame.Vector2, world_target: pygame.Vector2) -> None:
        to_target = world_target - owner_pos
        if to_target.length_squared() > 0:
            self.direction = to_target.normalize()
            # oś Y ekranu rośnie w dół, stąd minus przy obrocie
            self.angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
        self.pos = owner_pos + self.direction * self.HOLD_DISTANCE
        self.image = pygame.transform.rotate(self.base_image, self.angle)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        center = (round(self.pos.x - camera_offset.x), round(self.pos.y - camera_offset.y))
        surface.blit(self.image, self.image.get_rect(center=center))


class NameTag:
    """Napis nad postacią - wielokrotnego użytku (gracz, boty, później inni gracze)."""

    FONT_SIZE = 32
    COLOR = (255, 255, 255)
    GAP = 8  # odstęp od górnej krawędzi postaci

    _font: pygame.font.Font | None = None

    def __init__(self, text: str):
        if NameTag._font is None:
            NameTag._font = pygame.font.Font(None, self.FONT_SIZE)
        self.image = NameTag._font.render(text, True, self.COLOR)

    def draw(self, surface: pygame.Surface, target_rect: pygame.Rect, camera_offset: pygame.Vector2) -> None:
        rect = self.image.get_rect(
            midbottom=(target_rect.centerx - round(camera_offset.x), target_rect.top - self.GAP - round(camera_offset.y))
        )
        surface.blit(self.image, rect)


class GameObject:
    """Bazowy obiekt świata (greybox). Kolizje włącza się flagą `collidable` w konstruktorze."""

    MAX_STEP = 8  # maks. przesunięcie (px) w jednym kroku kolizji

    def __init__(self, x: float, y: float, width: int, height: int, color: tuple[int, int, int],
                 collidable: bool = True):
        self.pos = pygame.Vector2(x, y)  # środek obiektu
        self.collidable = collidable
        # Placeholder (greybox) - później podmiana na .png
        self.image = pygame.Surface((width, height))
        self.image.fill(color)

    @property
    def rect(self) -> pygame.Rect:
        return self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def move_and_collide(self, delta: pygame.Vector2, solids: list["GameObject"]) -> None:
        """Przesuwa obiekt osobno w osi X i Y i cofa go przy zderzeniu z kolizyjnymi obiektami
        (dzięki temu obiekt ślizga się wzdłuż ścian). Ta sama metoda posłuży pociskom.
        Ruch jest dzielony na małe kroki, żeby szybki obiekt nie przeskoczył przez cienką ścianę."""
        steps = max(1, math.ceil(max(abs(delta.x), abs(delta.y)) / self.MAX_STEP))
        step = delta / steps
        for _ in range(steps):
            self._step_and_collide(step, solids)

    def _step_and_collide(self, delta: pygame.Vector2, solids: list["GameObject"]) -> None:
        for axis in (0, 1):
            self.pos[axis] += delta[axis]
            if not self.collidable:
                continue
            for other in solids:
                if other is self or not other.collidable:
                    continue
                mine, theirs = self.rect, other.rect
                if not mine.colliderect(theirs):
                    continue
                half = (mine.width if axis == 0 else mine.height) / 2
                if axis == 0:
                    self.pos.x = theirs.left - half if delta.x > 0 else theirs.right + half
                else:
                    self.pos.y = theirs.top - half if delta.y > 0 else theirs.bottom + half

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        surface.blit(self.image, self.rect.move(-round(camera_offset.x), -round(camera_offset.y)))


class Obstacle(GameObject):
    """Przeszkoda statyczna: ściana, skała itp. (domyślnie z kolizją)."""

    def __init__(self, x: float, y: float, width: int, height: int,
                 color: tuple[int, int, int] = (110, 110, 120), collidable: bool = True):
        super().__init__(x, y, width, height, color, collidable)


class Bot(GameObject):
    """Nieruchomy bot testowy do strzelania (zielony kwadrat)."""

    SIZE = 50

    def __init__(self, name: str, x: float, y: float):
        super().__init__(x, y, self.SIZE, self.SIZE, (50, 200, 70))
        self.name_tag = NameTag(name)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        super().draw(surface, camera_offset)
        self.name_tag.draw(surface, self.rect, camera_offset)


class Player(GameObject):
    SIZE = 50
    SPEED = 400  # piksele na sekundę

    def __init__(self, x: float, y: float, name: str = "Player1"):
        super().__init__(x, y, self.SIZE, self.SIZE, (40, 90, 255))
        self.gun = Gun(self.pos)
        self.name_tag = NameTag(name)

    def update(self, dt: float, keys, solids: list[GameObject]) -> None:
        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        if direction.length_squared() > 0:
            direction.normalize_ip()  # brak szybszego ruchu po skosie
        self.move_and_collide(direction * self.SPEED * dt, solids)

    def aim_at(self, world_target: pygame.Vector2) -> None:
        self.gun.aim_at(self.pos, world_target)

    def shoot(self, targets: list[GameObject], trigger_held: bool, trigger_pressed: bool):
        return self.gun.fire(self, targets, trigger_held, trigger_pressed)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        super().draw(surface, camera_offset)
        self.gun.draw(surface, camera_offset)
        self.name_tag.draw(surface, self.rect, camera_offset)


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
        self.tracers: list[Tracer] = []
        self.fire_pressed = False
        self.hud_font = pygame.font.Font(None, HUD_FONT_SIZE)
        # Obiekty świata (poza graczem). Kolizje: flaga `collidable` w konstruktorze obiektu.
        self.objects: list[GameObject] = [
            Bot("Bot1", 400, -250), Bot("Bot2", -500, 200), Bot("Bot3", 300, 450),
            Obstacle(-300, -300, 400, 40),
            Obstacle(250, 100, 40, 300),
            Obstacle(-150, 350, 100, 100, color=(120, 90, 60)),
        ]
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
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.player.gun.start_reload()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.fire_pressed = True  # kliknięcie w tej klatce (dla broni półautomatycznych)

    def update(self, dt: float) -> None:
        self.player.update(dt, pygame.key.get_pressed(), self.objects)
        self.player.aim_at(self.mouse_world_pos())
        self.player.gun.update(dt)
        result = self.player.shoot(self.objects, pygame.mouse.get_pressed()[0], self.fire_pressed)
        self.fire_pressed = False
        if result:
            tracer, _hit_obj = result  # trafiony obiekt - na razie bez efektu (brak ustalonych zasad obrażeń)
            self.tracers.append(tracer)
        for tracer in self.tracers:
            tracer.update(dt)
        self.tracers = [t for t in self.tracers if t.alive]
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
        for obj in self.objects:
            obj.draw(self.canvas, offset)
        self.player.draw(self.canvas, offset)
        for tracer in self.tracers:
            tracer.draw(self.canvas, offset)
        self._draw_hud()
        self._present()

    def _draw_hud(self) -> None:
        """Proste UI (rysowane po świecie, na stałe w rogu wirtualnego ekranu): amunicja."""
        gun = self.player.gun
        text = f"{gun.ammo} / {gun.magazine_size}"
        color = HUD_COLOR if gun.ammo > 0 else HUD_EMPTY_COLOR
        image = self.hud_font.render(text, True, color)
        self.canvas.blit(image, image.get_rect(bottomright=(VIRTUAL_W - HUD_MARGIN, VIRTUAL_H - HUD_MARGIN)))

    def _viewport(self) -> tuple[float, pygame.Vector2, tuple[int, int]]:
        """Zwraca (skala, lewy górny róg obrazu w oknie, rozmiar obrazu) dla letterboxingu."""
        win_w, win_h = self.window.get_size()
        scale = min(win_w / VIRTUAL_W, win_h / VIRTUAL_H)
        size = (round(VIRTUAL_W * scale), round(VIRTUAL_H * scale))
        origin = pygame.Vector2((win_w - size[0]) // 2, (win_h - size[1]) // 2)
        return scale, origin, size

    def mouse_world_pos(self) -> pygame.Vector2:
        """Pozycja kursora w świecie: okno -> wirtualny ekran 1920x1080 -> świat (z kamerą)."""
        scale, origin, _ = self._viewport()
        virtual = (pygame.Vector2(pygame.mouse.get_pos()) - origin) / scale
        return virtual + self.camera.offset

    def _present(self) -> None:
        """Skaluje canvas 16:9 do okna z zachowaniem proporcji (czarne pasy na 16:10)."""
        _, origin, size = self._viewport()
        scaled = pygame.transform.smoothscale(self.canvas, size)
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, origin)
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
