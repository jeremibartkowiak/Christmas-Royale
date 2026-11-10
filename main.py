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
HP_BAR_SIZE = (380, 34)
HP_BAR_SLANT = 14  # pochylenie paska (px)
HP_FONT_SIZE = 30
HP_BAR_COLOR = (76, 175, 60)  # zawsze zielony, niezależnie od ilości HP
HP_BAR_BACK_COLOR = (20, 45, 22)


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

    THICKNESS = 16
    HOLD_DISTANCE = 45  # odległość środka pistoletu od środka gracza
    RANGE = 2000  # zasięg hitscanu (px)

    def __init__(self, owner_pos: pygame.Vector2, name: str = "Pistol", automatic: bool = True,
                 fire_rate: float = 6.0, magazine_size: int = 12, reload_time: float = 1.5,
                 damage: float = 20, length: int = 60, color: tuple[int, int, int] = (200, 200, 200)):
        """name: nazwa pokazywana w kill feedzie.
        automatic: True = ogień ciągły po przytrzymaniu LPM, False = jeden strzał na kliknięcie.
        fire_rate: strzały na sekundę. magazine_size: pojemność magazynka. reload_time: sekundy.
        damage: obrażenia zadawane jednym strzałem. length/color: wygląd placeholdera."""
        self.name = name
        self.length = length
        self.damage = damage
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
        self.base_image = pygame.Surface((self.length, self.THICKNESS), pygame.SRCALPHA)  # alfa: rogi po obrocie przezroczyste
        self.base_image.fill(color)
        self.image = self.base_image
        self.cooldown = 0.0

    @property
    def reloading(self) -> bool:
        return self.reload_left > 0

    def cancel_reload(self) -> None:
        self.reload_left = 0.0

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
        muzzle = self.pos + self.direction * (self.length / 2)
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


def make_pistol(owner_pos: pygame.Vector2) -> Gun:
    return Gun(owner_pos, name="Pistol", automatic=True, fire_rate=6.0, magazine_size=12,
               reload_time=1.5, damage=20)


def make_sniper(owner_pos: pygame.Vector2) -> Gun:
    return Gun(owner_pos, name="Sniper", automatic=False, fire_rate=1.0, magazine_size=1,
               reload_time=3.0, damage=100, length=100, color=(120, 140, 120))


class Inventory:
    """Plecak gracza: lista broni i jedna aktywna. Każda broń trzyma własny stan (amunicję itd.)."""

    def __init__(self, guns: list[Gun]):
        self.guns = guns
        self.index = 0

    @property
    def active(self) -> Gun:
        return self.guns[self.index]

    def select(self, index: int) -> None:
        if 0 <= index < len(self.guns) and index != self.index:
            self.active.cancel_reload()  # zmiana broni przerywa przeładowanie
            self.index = index


class KillFeed:
    """Log eliminacji w stylu CS:GO (prawy górny róg): zabójca, nazwa broni i wyeliminowany."""

    DURATION = 5.0  # sekundy widoczności wpisu
    MAX_ENTRIES = 5
    FONT_SIZE = 28
    MARGIN = 30
    PADDING = (14, 6)
    TEXT_COLOR = (255, 255, 255)
    WEAPON_COLOR = (255, 210, 80)
    BACK_COLOR = (0, 0, 0, 150)
    ROW_GAP = 6

    def __init__(self):
        self.font = pygame.font.Font(None, self.FONT_SIZE)
        self.entries: list[list] = []  # [broń, ofiara, wiek]

    def add(self, killer_name: str, weapon_name: str, victim_name: str) -> None:
        self.entries.append([killer_name, weapon_name, victim_name, 0.0])
        self.entries = self.entries[-self.MAX_ENTRIES:]

    def update(self, dt: float) -> None:
        for entry in self.entries:
            entry[3] += dt
        self.entries = [e for e in self.entries if e[3] < self.DURATION]

    def draw(self, surface: pygame.Surface) -> None:
        y = self.MARGIN
        for killer, weapon, victim, _ in self.entries:
            parts = [self.font.render(killer, True, self.TEXT_COLOR),
                     self.font.render(weapon, True, self.WEAPON_COLOR),
                     self.font.render(victim, True, self.TEXT_COLOR)]
            gap = 16
            w = sum(p.get_width() for p in parts) + gap * (len(parts) - 1) + self.PADDING[0] * 2
            h = max(p.get_height() for p in parts) + self.PADDING[1] * 2
            box = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(box, self.BACK_COLOR, box.get_rect(), border_radius=6)
            x = self.PADDING[0]
            for part in parts:
                box.blit(part, (x, self.PADDING[1]))
                x += part.get_width() + gap
            surface.blit(box, (VIRTUAL_W - self.MARGIN - w, y))
            y += h + self.ROW_GAP


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


class Health:
    """Komponent punktów życia - wielokrotnego użytku (gracz, boty, niszczalne obiekty na mapie)."""

    def __init__(self, max_hp: float):
        self.max_hp = max_hp
        self.hp = max_hp

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def fraction(self) -> float:
        return self.hp / self.max_hp

    def take_damage(self, amount: float) -> None:
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: float) -> None:
        self.hp = min(self.max_hp, self.hp + amount)


class GameObject:
    """Bazowy obiekt świata (greybox). Kolizje włącza się flagą `collidable` w konstruktorze,
    a punkty życia podaniem `max_hp` (None = obiekt niezniszczalny)."""

    MAX_STEP = 8  # maks. przesunięcie (px) w jednym kroku kolizji

    def __init__(self, x: float, y: float, width: int, height: int, color: tuple[int, int, int],
                 collidable: bool = True, max_hp: float | None = None):
        self.pos = pygame.Vector2(x, y)  # środek obiektu
        self.collidable = collidable
        self.name = ""  # pusta = obiekt bez nazwy (nie trafia do kill feedu)
        self.health: Health | None = Health(max_hp) if max_hp is not None else None
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
                 color: tuple[int, int, int] = (110, 110, 120), collidable: bool = True,
                 max_hp: float | None = None):
        super().__init__(x, y, width, height, color, collidable, max_hp)


class Bot(GameObject):
    """Bot testowy (zielony kwadrat). Opcjonalnie ma broń i strzela cały czas w jedną stronę."""

    SIZE = 50

    def __init__(self, name: str, x: float, y: float, max_hp: float = 100,
                 gun: Gun | None = None, fire_direction: tuple[float, float] = (1, 0)):
        super().__init__(x, y, self.SIZE, self.SIZE, (50, 200, 70), max_hp=max_hp)
        self.name = name
        self.name_tag = NameTag(name)
        self.gun = gun
        self.fire_direction = pygame.Vector2(fire_direction)

    def update(self, dt: float, targets: list[GameObject]):
        """Zwraca wynik strzału (tracer, trafiony obiekt) albo None."""
        if self.gun is None:
            return None
        self.gun.update(dt)
        self.gun.aim_at(self.pos, self.pos + self.fire_direction)
        return self.gun.fire(self, targets, True, True)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        super().draw(surface, camera_offset)
        if self.gun is not None:
            self.gun.draw(surface, camera_offset)
        self.name_tag.draw(surface, self.rect, camera_offset)


class Player(GameObject):
    SIZE = 50
    SPEED = 400  # piksele na sekundę

    def __init__(self, x: float, y: float, name: str = "Player1", max_hp: float = 100):
        super().__init__(x, y, self.SIZE, self.SIZE, (40, 90, 255), max_hp=max_hp)
        self.name = name
        self.inventory = Inventory([make_pistol(self.pos), make_sniper(self.pos)])
        self.name_tag = NameTag(name)

    @property
    def gun(self) -> Gun:
        return self.inventory.active

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
    RESPAWN_POS = (0, 0)
    EL_TITLE_SIZE = 72
    EL_BUTTON_SIZE = (320, 70)
    EL_BUTTON_FONT_SIZE = 44
    EL_BUTTON_COLOR = (60, 60, 75)
    EL_BUTTON_HOVER_COLOR = (95, 95, 120)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.fullscreen = False
        self.window = self._create_window()
        # Wirtualny ekran 1920x1080 - cała gra rysuje tutaj, potem skalujemy z letterboxingiem
        self.canvas = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        self.clock = pygame.time.Clock()
        self.running = True
        self.player = Player(*self.RESPAWN_POS)
        self.player_alive = True
        self.tracers: list[Tracer] = []
        self.kill_feed = KillFeed()
        self.fire_pressed = False
        self.hud_font = pygame.font.Font(None, HUD_FONT_SIZE)
        self.hp_font = pygame.font.Font(None, HP_FONT_SIZE)
        self.hp_font.set_bold(True)
        self.el_title_font = pygame.font.Font(None, self.EL_TITLE_SIZE)
        self.el_button_font = pygame.font.Font(None, self.EL_BUTTON_FONT_SIZE)
        center_x = VIRTUAL_W // 2
        self.respawn_button = pygame.Rect(0, 0, *self.EL_BUTTON_SIZE)
        self.respawn_button.center = (center_x, VIRTUAL_H // 2 + 30)
        self.quit_button = pygame.Rect(0, 0, *self.EL_BUTTON_SIZE)
        self.quit_button.center = (center_x, VIRTUAL_H // 2 + 120)
        # Obiekty świata (poza graczem). Kolizje: flaga `collidable` w konstruktorze obiektu.
        self.objects: list[GameObject] = [
            Bot("Bot1", 400, -250), Bot("Bot2", -500, 200), Bot("Bot3", 300, 450),
            Bot("Bot4", -700, -150, gun=Gun(pygame.Vector2(-700, -150), name="Pistol", fire_rate=1.0,
                                           magazine_size=9999, damage=10)),
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

    def respawn(self) -> None:
        self.player = Player(*self.RESPAWN_POS)
        self.player_alive = True
        self.camera.pos = pygame.Vector2(self.player.pos)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif not self.player_alive:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = self.mouse_virtual_pos()
                    if self.respawn_button.collidepoint(pos):
                        self.respawn()
                    elif self.quit_button.collidepoint(pos):
                        self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.player.gun.start_reload()
            elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
                self.player.inventory.select(event.key - pygame.K_1)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.fire_pressed = True  # kliknięcie w tej klatce (dla broni półautomatycznych)

    def _targets(self) -> list[GameObject]:
        """Obiekty, które mogą zostać trafione (świat + żywy gracz)."""
        return self.objects + [self.player] if self.player_alive else list(self.objects)

    def _handle_shot(self, result, gun: Gun, shooter: GameObject) -> None:
        tracer, hit = result
        self.tracers.append(tracer)
        if hit is None or hit.health is None or hit.health.is_dead:
            return
        hit.health.take_damage(gun.damage)
        if hit.health.is_dead:
            self._on_death(hit, gun.name, shooter)

    def _on_death(self, obj: GameObject, weapon_name: str, killer: GameObject) -> None:
        if obj.name:
            self.kill_feed.add(killer.name, weapon_name, obj.name)
        if obj is self.player:
            self.player_alive = False
        elif obj in self.objects:
            self.objects.remove(obj)  # bot / niszczalny obiekt znika

    def update(self, dt: float) -> None:
        if self.player_alive:
            self.player.update(dt, pygame.key.get_pressed(), self.objects)
            self.player.aim_at(self.mouse_world_pos())
            self.player.gun.update(dt)
            result = self.player.shoot(self._targets(), pygame.mouse.get_pressed()[0], self.fire_pressed)
            if result:
                self._handle_shot(result, self.player.gun, self.player)
        self.fire_pressed = False
        for bot in [o for o in self.objects if isinstance(o, Bot)]:
            result = bot.update(dt, self._targets())
            if result:
                self._handle_shot(result, bot.gun, bot)
        for tracer in self.tracers:
            tracer.update(dt)
        self.tracers = [t for t in self.tracers if t.alive]
        self.kill_feed.update(dt)
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
        if self.player_alive:
            self.player.draw(self.canvas, offset)
        for tracer in self.tracers:
            tracer.draw(self.canvas, offset)
        self._draw_hud()
        self.kill_feed.draw(self.canvas)
        if not self.player_alive:
            self._draw_eliminated_screen()
        self._present()

    def _draw_hud(self) -> None:
        """Proste UI (rysowane po świecie, na stałe w rogu wirtualnego ekranu): amunicja i HP."""
        gun = self.player.gun
        text = f"{gun.name}   {gun.ammo} / {gun.magazine_size}"
        color = HUD_COLOR if gun.ammo > 0 else HUD_EMPTY_COLOR
        image = self.hud_font.render(text, True, color)
        self.canvas.blit(image, image.get_rect(bottomright=(VIRTUAL_W - HUD_MARGIN, VIRTUAL_H - HUD_MARGIN)))
        self._draw_hp_bar()

    def _draw_hp_bar(self) -> None:
        """Minimalistyczny pasek HP gracza w stylu Fortnite (lewy dolny róg, zawsze zielony,
        lekko pochylony) z napisem 'hp | max'. Tylko w HUD, bez pasków nad postaciami."""
        health = self.player.health
        w, h = HP_BAR_SIZE
        x, y = HUD_MARGIN, VIRTUAL_H - HUD_MARGIN - h
        slant = HP_BAR_SLANT

        def parallelogram(width: float) -> list[tuple[float, float]]:
            return [(x + slant, y), (x + slant + width, y), (x + width, y + h), (x, y + h)]

        pygame.draw.polygon(self.canvas, HP_BAR_BACK_COLOR, parallelogram(w))
        if health.hp > 0:
            pygame.draw.polygon(self.canvas, HP_BAR_COLOR, parallelogram(w * health.fraction))
        text = self.hp_font.render(f"{math.ceil(health.hp)} | {math.ceil(health.max_hp)}", True, HUD_COLOR)
        self.canvas.blit(text, text.get_rect(midleft=(x + slant + 12, y + h // 2)))

    def _draw_eliminated_screen(self) -> None:
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.canvas.blit(overlay, (0, 0))
        title = self.el_title_font.render("YOU HAVE BEEN ELIMINATED", True, (255, 255, 255))
        self.canvas.blit(title, title.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2 - 80)))
        mouse = self.mouse_virtual_pos()
        for rect, label in ((self.respawn_button, "Respawn"), (self.quit_button, "Quit")):
            color = self.EL_BUTTON_HOVER_COLOR if rect.collidepoint(mouse) else self.EL_BUTTON_COLOR
            pygame.draw.rect(self.canvas, color, rect, border_radius=8)
            text = self.el_button_font.render(label, True, (255, 255, 255))
            self.canvas.blit(text, text.get_rect(center=rect.center))

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

    def mouse_world_pos(self) -> pygame.Vector2:
        """Pozycja kursora w świecie: okno -> wirtualny ekran 1920x1080 -> świat (z kamerą)."""
        return self.mouse_virtual_pos() + self.camera.offset

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
