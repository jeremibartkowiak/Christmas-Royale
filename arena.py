from __future__ import annotations

import pygame

from camera import Camera
from entities import Player
from objects import GameObject
from scene import Scene
from settings import VIRTUAL_W, VIRTUAL_H, GRID_STEP, GRID_COLOR, BACKGROUND_COLOR
from ui import EscMenu, Hud, KillFeed
from weapons import Gun, Tracer


class ArenaScene(Scene):
    """Wspólna baza scen z walką (Debug, Deathmatch...): gracz, strzelanie, kamera, HUD, kill feed
    i menu ESC (wstrzymuje grę). Podklasa musi w `__init__` ustawić `self.player`, `self.camera`
    i `self.objects`, a także zaimplementować `update_world`."""

    def __init__(self, app):
        super().__init__(app)
        self.player: Player
        self.camera: Camera
        self.player_alive = True
        self.objects: list[GameObject] = []
        self.tracers: list[Tracer] = []
        self.kill_feed = KillFeed()
        self.hud = Hud()
        self.esc_menu = EscMenu()
        self.esc_menu_open = False
        self.fire_pressed = False

    # --- zdarzenia ---
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.esc_menu_open = not self.esc_menu_open
            self.fire_pressed = False
            return
        if self.esc_menu_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.esc_menu.button_at(self.app.mouse_virtual_pos()) == "leave":
                    self.app.go_to_menu()
            return
        if not self.player_alive:
            self.handle_dead_event(event)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.player.gun.start_reload()
        elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
            self.player.inventory.select(event.key - pygame.K_1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.fire_pressed = True  # kliknięcie w tej klatce (dla broni półautomatycznych)

    def handle_dead_event(self, event: pygame.event.Event) -> None:
        """Zdarzenia, gdy gracz nie żyje (np. przyciski ekranu eliminacji)."""

    def mouse_world_pos(self) -> pygame.Vector2:
        """Pozycja kursora w świecie: okno -> wirtualny ekran 1920x1080 -> świat (z kamerą)."""
        return self.app.mouse_virtual_pos() + self.camera.offset

    # --- walka ---
    def _targets(self) -> list[GameObject]:
        """Obiekty, które mogą zostać trafione (świat + żywy gracz)."""
        return self.objects + [self.player] if self.player_alive else list(self.objects)

    def _handle_shot(self, result, gun: Gun, shooter: GameObject) -> None:
        tracer, hit = result
        self.tracers.append(tracer)
        if hit is None or hit.health is None or hit.health.is_dead:
            return
        if hit.protection is not None and hit.protection.active:
            return  # ochrona po spawnie pochłania strzał
        hit.health.take_damage(gun.damage)
        if hit.health.is_dead:
            self._on_death(hit, gun, shooter)

    def _on_death(self, obj: GameObject, gun: Gun, killer: GameObject) -> None:
        if obj.name:
            self.kill_feed.add(killer.name, gun.name, obj.name)
        if obj is self.player:
            self.player_alive = False
        elif obj in self.objects:
            self.objects.remove(obj)  # bot / niszczalny obiekt znika

    def _update_player(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        firing = pygame.mouse.get_pressed()[0]
        moving = bool(keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d])
        self.player.update(dt, keys, self.objects)
        self.player.aim_at(self.mouse_world_pos())
        self.player.gun.update(dt)
        result = self.player.shoot(self._targets(), firing, self.fire_pressed)
        if result:
            self._handle_shot(result, self.player.gun, self.player)
        if self.player.protection is not None:
            self.player.protection.update(dt, moving or firing or self.fire_pressed)

    # --- aktualizacja ---
    def update_world(self, dt: float) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        if self.esc_menu_open:
            return  # menu ESC wstrzymuje grę
        self.update_world(dt)
        self.fire_pressed = False
        for tracer in self.tracers:
            tracer.update(dt)
        self.tracers = [t for t in self.tracers if t.alive]
        self.kill_feed.update(dt)
        self.camera.update(dt, self.player.pos)

    # --- rysowanie ---
    def _draw_grid(self, surface: pygame.Surface, offset: pygame.Vector2) -> None:
        """Tymczasowa siatka (greybox), żeby było widać ruch kamery po nieograniczonym świecie."""
        ox, oy = round(offset.x), round(offset.y)
        for x in range(-(ox % GRID_STEP), VIRTUAL_W, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, VIRTUAL_H))
        for y in range(-(oy % GRID_STEP), VIRTUAL_H, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (0, y), (VIRTUAL_W, y))

    def draw_floor(self, surface: pygame.Surface, offset: pygame.Vector2) -> None:
        """Hak dla podklas: rysowanie podłoża pod siatką."""

    def draw_overlay(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        """Hak dla podklas: elementy UI rysowane na wierzchu HUD-u (np. ekran eliminacji, czas meczu)."""

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND_COLOR)
        offset = self.camera.offset
        self.draw_floor(surface, offset)
        self._draw_grid(surface, offset)
        for obj in self.objects:
            obj.draw(surface, offset)
        if self.player_alive:
            self.player.draw(surface, offset)
        for tracer in self.tracers:
            tracer.draw(surface, offset)
        self.hud.draw(surface, self.player)
        self.kill_feed.draw(surface)
        mouse = self.app.mouse_virtual_pos()
        self.draw_overlay(surface, mouse)
        if self.esc_menu_open:
            self.esc_menu.draw(surface, mouse)
