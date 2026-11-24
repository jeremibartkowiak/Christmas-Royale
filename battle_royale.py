from __future__ import annotations

import random

import pygame

from arena import ArenaScene
from bot_ai import AIBot
from camera import Camera
from entities import Player
from loot import Chest, Pickup
from maps import ArenaMap, make_br_arena
from objects import GameObject, Obstacle
from settings import VIRTUAL_W, VIRTUAL_H
from ui import BattleRoyaleEndScreen, BattleRoyaleHud
from weapons import Gun, roll_weapon
from zone import StormZone


class BattleRoyaleScene(ArenaScene):
    """Battle Royale (singleplayer): 1 gracz + 99 botów na wielkiej mapie, start bez broni,
    losowy loot ze skrzyń (`Weapons Pool`), fioletowy storm i 1 życie."""

    PLAYER_COUNT = 100
    FLOOR_COLOR = (34, 42, 58)
    CELL_SIZE = 320  # rozmiar komórki siatki przestrzennej do kolizji (3x3 = ~960x960 px)
    SIGHT_CELL = 1150  # większa siatka do wykrywania wrogów i przeszkód wzrokiem

    def __init__(self, app, options: dict[str, float] | None = None):
        super().__init__(app)
        self.options = options or {}
        self.bot_difficulty = int(self.options.get("difficulty", 3))
        self.arena: ArenaMap
        self.arena, chest_spots = make_br_arena(chest_count=90)

        obstacles = self.arena.build_obstacles()
        self.obstacles: list[GameObject] = list(obstacles)
        self.chests: list[Chest[Gun]] = [
            Chest(x, y, roll_weapon(pygame.Vector2(x, y))) for x, y in chest_spots
        ]
        self.objects = list(obstacles) + list(self.chests)

        # Statyczne przeszkody i skrzynie (poza 4 ścianami granicznymi) w indeksie przestrzennym
        self.static_grid: dict[tuple[int, int], list[GameObject]] = {}
        self.sight_grid: dict[tuple[int, int], list[GameObject]] = {}
        for obs in obstacles[4:]:
            self._grid_add(self.static_grid, obs, self.CELL_SIZE)
            self._grid_add(self.sight_grid, obs, self.SIGHT_CELL)
        for chest in self.chests:
            self._grid_add(self.static_grid, chest, self.CELL_SIZE)
        self.border_walls: list[GameObject] = list(obstacles[:4])

        # Losowe pozycje startowe dla 100 uczestników
        spawns = list(self.arena.spawn_points)
        random.shuffle(spawns)
        px, py = spawns[0]
        self.player = Player(px, py, guns=[])  # start bez broni!
        self.camera = Camera(self.player.pos)

        bounds = self.arena.bounds.inflate(-200, -200)
        self.bots: list[AIBot] = []
        for i in range(1, self.PLAYER_COUNT):
            bx, by = spawns[i % len(spawns)]
            bot = AIBot(f"Bot{i}", bx, by, bounds=bounds, difficulty=self.bot_difficulty, start_empty=True)
            self.bots.append(bot)
            self.objects.append(bot)

        self.zone = StormZone(self.arena.bounds)
        self.br_hud = BattleRoyaleHud(self.arena.bounds, obstacles[4:])
        self.end_screen = BattleRoyaleEndScreen()
        self.eliminations = 0
        self.match_over = False
        self.victory = False
        self.player_place = self.PLAYER_COUNT

    # --- indeks przestrzenny (optymalizacja dla 100 graczy) ---
    @staticmethod
    def _cell(pos: pygame.Vector2, size: int) -> tuple[int, int]:
        return (int(pos.x // size), int(pos.y // size))

    def _grid_add(self, grid: dict[tuple[int, int], list], obj: GameObject, size: int) -> None:
        r = obj.rect
        c0 = (int(r.left // size), int(r.top // size))
        c1 = (int(r.right // size), int(r.bottom // size))
        for cx in range(c0[0], c1[0] + 1):
            for cy in range(c0[1], c1[1] + 1):
                grid.setdefault((cx, cy), []).append(obj)

    def _nearby(self, grid: dict[tuple[int, int], list], pos: pygame.Vector2, size: int,
                extra: list | None = None) -> list:
        cx, cy = self._cell(pos, size)
        out = list(extra) if extra else []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.extend(grid.get((cx + dx, cy + dy), ()))
        return out

    # --- logika meczu ---
    @property
    def alive_count(self) -> int:
        return len(self.bots) + (1 if self.player_alive else 0)

    def _shows_crosshair(self) -> bool:
        return super()._shows_crosshair() and not self.match_over

    def handle_dead_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_end_click(self.app.mouse_virtual_pos())

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.match_over and not self.esc_menu_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.esc_menu_open = True
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_end_click(self.app.mouse_virtual_pos())
            return
        super().handle_event(event)

    def _handle_end_click(self, pos: pygame.Vector2) -> None:
        btn = self.end_screen.button_at(pos)
        if btn == "again":
            self.app.change_scene(BattleRoyaleScene(self.app, self.options))
        elif btn == "menu":
            self.app.go_to_menu()

    def _on_death(self, obj: GameObject, gun: Gun, killer: GameObject) -> None:
        self.kill_feed.add(killer.name, gun.name, obj.name)
        if killer is self.player and obj is not self.player:
            self.eliminations += 1
        self._remove_participant(obj)

    def _remove_participant(self, obj: GameObject) -> None:
        if obj is self.player:
            if self.player_alive:
                self.player_place = self.alive_count
                self.player_alive = False
                self.match_over = True
        else:
            if obj in self.bots:
                self.bots.remove(obj)
            if obj in self.objects:
                self.objects.remove(obj)
            if self.player_alive and not self.bots:
                self.player_place = 1
                self.victory = True
                self.match_over = True

    def update_world(self, dt: float) -> None:
        if self.match_over:
            return
        self.zone.update(dt)

        # Siatki przestrzenne na bieżącą klatkę (boty + skrzynie + pickupy)
        bot_grid: dict[tuple[int, int], list[AIBot]] = {}
        bot_sight_grid: dict[tuple[int, int], list[AIBot]] = {}
        for bot in self.bots:
            bot_grid.setdefault(self._cell(bot.pos, self.CELL_SIZE), []).append(bot)
            bot_sight_grid.setdefault(self._cell(bot.pos, self.SIGHT_CELL), []).append(bot)
        chest_grid: dict[tuple[int, int], list[Chest]] = {}
        for chest in self.chests:
            if not chest.opened:
                chest_grid.setdefault(self._cell(chest.pos, self.CELL_SIZE), []).append(chest)
        pickup_grid: dict[tuple[int, int], list[Pickup]] = {}
        for pickup in self.pickups:
            pickup_grid.setdefault(self._cell(pickup.pos, self.CELL_SIZE), []).append(pickup)

        if self.player_alive:
            local_solids = self._nearby(self.static_grid, self.player.pos, self.CELL_SIZE, self.border_walls)
            local_solids.extend(self._nearby(bot_grid, self.player.pos, self.CELL_SIZE))
            self._update_player_local(dt, local_solids)

        self._update_bots(dt, bot_grid, bot_sight_grid, chest_grid, pickup_grid)
        self._apply_storm_damage(dt)

    def _update_player_local(self, dt: float, local_solids: list[GameObject]) -> None:
        keys = pygame.key.get_pressed()
        firing = pygame.mouse.get_pressed()[0]
        self.player.update(dt, keys, local_solids)
        self.player.aim_at(self.mouse_world_pos())
        if self.player.gun is not None:
            self.player.gun.update(dt)
            shoot_targets = self._nearby(self.sight_grid, self.player.pos, self.SIGHT_CELL, self.border_walls)
            shoot_targets.extend(b for b in self.bots if b.pos.distance_squared_to(self.player.pos) < 2200 ** 2)
            result = self.player.shoot(shoot_targets, firing, self.fire_pressed)
            if result:
                self._handle_shot(result, self.player.gun, self.player)

    def _update_bots(self, dt: float, bot_grid, bot_sight_grid, chest_grid, pickup_grid) -> None:
        for bot in list(self.bots):
            if bot not in self.bots:
                continue
            local_obs = self._nearby(self.static_grid, bot.pos, self.CELL_SIZE, self.border_walls)
            local_bots = [b for b in self._nearby(bot_grid, bot.pos, self.CELL_SIZE) if b is not bot and b in self.bots]
            world = local_obs + local_bots
            if self.player_alive and bot.pos.distance_squared_to(self.player.pos) < self.CELL_SIZE ** 2:
                world.append(self.player)

            # Wzrok i cele sprawdzane tylko wtedy, gdy bot szuka celu lub ma aktywny cel
            enemies: list[GameObject] = []
            sight_obs = local_obs
            if bot.gun is not None and (bot.think_left - dt <= 0 or bot.target is not None):
                sight_obs = self._nearby(self.sight_grid, bot.pos, self.SIGHT_CELL, self.border_walls)
                enemies = [b for b in self._nearby(bot_sight_grid, bot.pos, self.SIGHT_CELL)
                           if b is not bot and b in self.bots]
                if self.player_alive and bot.pos.distance_squared_to(self.player.pos) < self.SIGHT_CELL ** 2:
                    enemies.append(self.player)

            loot_target = None
            if bot.gun is None:
                local_pickups = [p for p in self._nearby(pickup_grid, bot.pos, self.CELL_SIZE) if p.can_pickup]
                if local_pickups:
                    nearest_p = min(local_pickups, key=lambda p: p.pos.distance_squared_to(bot.pos))
                    loot_target = nearest_p.pos
                else:
                    local_chests = self._nearby(chest_grid, bot.pos, self.CELL_SIZE)
                    if local_chests:
                        nearest_c = min(local_chests, key=lambda c: c.pos.distance_squared_to(bot.pos))
                        loot_target = nearest_c.pos
                        if bot.pos.distance_to(nearest_c.pos) <= nearest_c.interact_range:
                            loot = nearest_c.update_interaction(dt, bot.pos, True)
                            if loot is not None:
                                bot.inventory.add(loot)

            # Podnoszenie pickupów przez bota, jeśli nie ma broni
            if bot.gun is None:
                for p in list(self._nearby(pickup_grid, bot.pos, self.CELL_SIZE)):
                    if p in self.pickups and p.can_pickup and bot.rect.colliderect(p.rect):
                        if isinstance(p.item, Gun):
                            bot.inventory.add(p.item)
                        self.pickups.remove(p)
                        break

            result = bot.act(dt, enemies, sight_obs, world,
                             safe_center=self.zone.center, safe_radius=self.zone.radius,
                             loot_target=loot_target)
            if result:
                self._handle_shot(result, bot.gun, bot)

    def _apply_storm_damage(self, dt: float) -> None:
        dps = self.zone.dps
        if dps <= 0:
            return
        dmg = dps * dt
        if self.player_alive and not self.zone.is_inside(self.player.pos):
            self.player.health.take_damage(dmg)
            if self.player.health.is_dead:
                self.kill_feed.add("Storm", "Zone", self.player.name)
                self._remove_participant(self.player)
        for bot in list(self.bots):
            if not self.zone.is_inside(bot.pos):
                bot.health.take_damage(dmg)
                if bot.health.is_dead:
                    self.kill_feed.add("Storm", "Zone", bot.name)
                    self._remove_participant(bot)

    # --- rysowanie (z przycinaniem do widoku kamery dla wydajności) ---
    def draw_floor(self, surface: pygame.Surface, offset: pygame.Vector2) -> None:
        floor = self.arena.bounds.move(-round(offset.x), -round(offset.y))
        pygame.draw.rect(surface, self.FLOOR_COLOR, floor)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((25, 30, 40))
        offset = self.camera.offset
        self.draw_floor(surface, offset)
        self._draw_grid(surface, offset)

        view = pygame.Rect(offset.x - 150, offset.y - 150, VIRTUAL_W + 300, VIRTUAL_H + 300)
        for pickup in self.pickups:
            if view.colliderect(pickup.rect):
                pickup.draw(surface, offset)
        for obj in self.objects:
            if view.colliderect(obj.rect):
                obj.draw(surface, offset)
        if self.player_alive:
            self.player.draw(surface, offset)
            for chest in self.chests:
                if not chest.opened and view.colliderect(chest.rect):
                    chest.draw_prompt(surface, offset, self.player.pos)
        for tracer in self.tracers:
            tracer.draw(surface, offset)

        # Fioletowy Storm nad światem gry, pod HUD-em
        self.zone.draw(surface, offset)
        self.hud.draw(surface, self.player)
        self.br_hud.draw(surface, self.player.pos, self.zone, self.alive_count, self.eliminations)
        self.kill_feed.draw(surface)

        mouse = self.app.mouse_virtual_pos()
        if self.match_over:
            self.end_screen.draw(surface, mouse, self.victory, self.player_place,
                                 self.PLAYER_COUNT, self.eliminations)
        if self._shows_crosshair():
            self.crosshair.draw(surface, mouse)
        if self.esc_menu_open:
            self.esc_menu.draw(surface, mouse)
