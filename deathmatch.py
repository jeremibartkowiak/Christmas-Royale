from __future__ import annotations

import math
import random

import pygame

from account import MATCH_REWARD_TOKENS
from arena import ArenaScene
from bot_ai import AIBot
from camera import Camera
from entities import Player
from maps import ArenaMap, make_dm_arena
from objects import GameObject, SpawnProtection
from results import ResultsScene
from scoring import Participant
from settings import (VIRTUAL_W, VIRTUAL_H, PLAYER_NAME, PLAYER_COLOR, BOT_COLOR)
from ui import MatchHud
from weapons import Gun


class DeathmatchScene(ArenaScene):
    """Deathmatch (singleplayer): gracz + boty do 16 osób na zamkniętej arenie.
    Punkty za zabójstwo zależą od broni (`Gun.points`). Po upływie czasu pokazuje podium Top 3."""

    MATCH_TIME = 600.0  # s (10 minut)
    PLAYER_COUNT = 16  # gracz + boty
    RESPAWN_TIME = 2.5  # s do odrodzenia po śmierci
    FLOOR_COLOR = (34, 40, 56)

    def __init__(self, app, options: dict[str, float] | None = None):
        super().__init__(app)
        opts = options or {}
        self.bot_difficulty = int(opts.get("difficulty", 3))
        self.arena: ArenaMap = make_dm_arena()
        self.objects = self.arena.build_obstacles()
        self.obstacles: list[GameObject] = list(self.objects)  # same przeszkody (linia widzenia botów)
        acc = self.app.account
        pfp = acc.load_pfp_surface((54, 54))
        self.participants = [Participant(acc.name, acc.player_color(), is_player=True, pfp_surface=pfp)]
        self.participants += [Participant(f"Bot{i}", BOT_COLOR) for i in range(1, self.PLAYER_COUNT)]
        self.by_name = {p.name: p for p in self.participants}
        self.time_left = float(opts.get("minutes", self.MATCH_TIME / 60.0)) * 60.0
        self.match_hud = MatchHud()
        self.respawn_font = pygame.font.Font(None, 64)
        self.player_respawn_left = 0.0
        self.bot_respawns: list[list] = []  # [pozostały czas, nazwa bota]
        self.player = self._make_player(0, 0)
        self._spawn_player()
        self.camera = Camera(self.player.pos)
        for p in self.participants:
            if not p.is_player:
                self._spawn_bot(p.name)

    # --- spawn ---
    def _alive_positions(self) -> list[pygame.Vector2]:
        positions = [o.pos for o in self.objects if isinstance(o, AIBot)]
        if self.player_alive:
            positions.append(self.player.pos)
        return positions

    def _pick_spawn(self) -> tuple[int, int]:
        """Losuje jeden z 3 punktów spawnu najdalszych od żywych graczy (żeby nie odradzać się pod nogami)."""
        others = self._alive_positions()

        def clearance(point: tuple[int, int]) -> float:
            return min((pygame.Vector2(point).distance_to(p) for p in others), default=math.inf)

        best = sorted(self.arena.spawn_points, key=clearance, reverse=True)[:3]
        return random.choice(best)

    def _spawn_player(self) -> None:
        self.player = self._make_player(*self._pick_spawn())
        self.player.protection = SpawnProtection()
        self.player_alive = True
        if hasattr(self, "camera"):
            self.camera.pos = pygame.Vector2(self.player.pos)

    def _spawn_bot(self, name: str) -> None:
        self.objects.append(AIBot(name, *self._pick_spawn(),
                                  bounds=self.arena.bounds.inflate(-200, -200),
                                  difficulty=self.bot_difficulty))

    # --- śmierć i punkty ---
    def _on_death(self, obj: GameObject, gun: Gun, killer: GameObject) -> None:
        self.kill_feed.add(killer.name, gun.name, obj.name)
        killer_data = self.by_name.get(killer.name)
        if killer_data is not None and killer is not obj:
            killer_data.points += gun.points
        if obj is self.player:
            self.player_alive = False
            self.player_respawn_left = self.RESPAWN_TIME
        elif obj in self.objects:
            self.objects.remove(obj)
            self.bot_respawns.append([self.RESPAWN_TIME, obj.name])

    # --- aktualizacja ---
    def update_world(self, dt: float) -> None:
        self.time_left -= dt
        if self.time_left <= 0:
            self._finish()
            return
        if self.player_alive:
            self._update_player(dt)
        else:
            self.player_respawn_left -= dt
            if self.player_respawn_left <= 0:
                self._spawn_player()
        for entry in self.bot_respawns:
            entry[0] -= dt
        for _, name in [e for e in self.bot_respawns if e[0] <= 0]:
            self._spawn_bot(name)
        self.bot_respawns = [e for e in self.bot_respawns if e[0] > 0]
        self._update_bots(dt)

    def _update_bots(self, dt: float) -> None:
        bots = [o for o in self.objects if isinstance(o, AIBot)]
        for bot in bots:
            if bot not in self.objects:
                continue  # zginął w tej klatce
            enemies = [b for b in bots if b is not bot and b in self.objects and not self._is_protected(b)]
            if self.player_alive and not self._is_protected(self.player):
                enemies.append(self.player)
            result = bot.act(dt, enemies, self.obstacles, self._targets())
            if result:
                self._handle_shot(result, bot.gun, bot)

    @staticmethod
    def _is_protected(obj: GameObject) -> bool:
        return obj.protection is not None and obj.protection.active

    def _finish(self) -> None:
        self.app.account.add_tokens(MATCH_REWARD_TOKENS)
        self.app.change_scene(ResultsScene(self.app, self.participants, reward_tokens=MATCH_REWARD_TOKENS))

    # --- rysowanie ---
    def draw_floor(self, surface: pygame.Surface, offset: pygame.Vector2) -> None:
        floor = self.arena.bounds.move(-round(offset.x), -round(offset.y))
        pygame.draw.rect(surface, self.FLOOR_COLOR, floor)

    def draw_overlay(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        self.match_hud.draw(surface, self.time_left, self.participants)
        if not self.player_alive:
            shade = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 90))
            surface.blit(shade, (0, 0))
            text = self.respawn_font.render(f"Respawning in {max(0.0, self.player_respawn_left):.1f}",
                                            True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2)))
