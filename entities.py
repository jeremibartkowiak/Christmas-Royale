from __future__ import annotations

import pygame

from objects import GameObject
from settings import BOT_COLOR, PLAYER_COLOR, PLAYER_NAME
from ui import NameTag
from weapons import Gun, Inventory, make_pistol, make_sniper


class Bot(GameObject):
    """Bot testowy (zielony kwadrat). Opcjonalnie ma pojedynczą broń lub ekwipunek z broniami."""

    SIZE = 50

    def __init__(self, name: str, x: float, y: float, max_hp: float = 100,
                 gun: Gun | None = None, fire_direction: tuple[float, float] = (1, 0),
                 inventory: Inventory | None = None):
        super().__init__(x, y, self.SIZE, self.SIZE, BOT_COLOR, max_hp=max_hp)
        self.name = name
        self.name_tag = NameTag(name)
        self.inventory = inventory
        self._gun = gun
        self.fire_direction = pygame.Vector2(fire_direction)

    @property
    def gun(self) -> Gun | None:
        return self.inventory.active if self.inventory is not None else self._gun

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

    def __init__(self, x: float, y: float, name: str = PLAYER_NAME, max_hp: float = 100):
        super().__init__(x, y, self.SIZE, self.SIZE, PLAYER_COLOR, max_hp=max_hp)
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
