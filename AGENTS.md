# AGENTS.md — Christmas Royale

Ten plik definiuje zasady współpracy, wymagania techniczne i architekturę projektu **Christmas Royale** dla każdego agenta AI pracującego nad kodem.

---

## 1. Podział ról i Złota Zasada (ŚWIĘTOŚĆ)

- **Użytkownik (Dyrektor Kreatywny i Artysta):** wymyśla wszystkie zasady gry, mechaniki, balans, układ UI oraz tworzy wszystkie grafiki (wycięte tekstury memowe, Sprite Cranberry, mapy). Podejmuje **każdą** decyzję o tym, jak gra wygląda i działa.
- **Agent AI (Główny Programista / Lead Programmer):** jest wyłącznie wykonawcą technicznym. Pisze czysty, zoptymalizowany kod obiektowy (OOP), dba o matematykę, fizykę, kolizje, architekturę i przyszłą sieć.
- **ZŁOTA ZASADA:** **ZABRANIA SIĘ** podejmowania jakichkolwiek decyzji projektowych za Użytkownika. W przypadku najmniejszych wątpliwości (balans, zachowanie mechaniki, wygląd UI, struktura plików) **ZATRZYMAJ SIĘ i zapytaj Użytkownika o zdanie**. Nie zgaduj i nie narzucaj domyślnych rozwiązań projektowych bez zgody. Jeśli w prototypie musisz wstawić tymczasowe liczby (np. prędkość, rozmiar, kolor), wyraźnie wskaż je w odpowiedzi jako tymczasowe do decyzji Użytkownika.

---

## 2. Wymagania techniczne i konwencje

- **Środowisko:** Python + `pygame-ce` w lokalnym środowisku wirtualnym `.venv`.
  - Uruchamianie i testy zawsze przez `.venv\Scripts\python.exe`.
- **DirectX (obowiązkowo):** w `main.py` na samej górze pliku, **przed** jakimkolwiek importem `pygame` (i modułów importujących `pygame`), musi znajdować się:
  ```python
  os.environ["SDL_RENDER_DRIVER"] = "direct3d"
  ```
- **Rozdzielczość i skalowanie (16:9 vs 16:10):**
  - Gra rysuje **wyłącznie** na wirtualnym płótnie `VIRTUAL_W x VIRTUAL_H` (`1920x1080`, 16:9) w `App.canvas`.
  - Na końcu klatki `App._present()` skaluje `canvas` z zachowaniem proporcji (`smoothscale` + czarne pasy / letterboxing na ekranach 1920x1200 16:10), aby nigdy nie rozciągać ani nie zniekształcać tekstur.
  - Pozycję myszy dla UI pobieraj przez `app.mouse_virtual_pos()`, a w świecie gry przez `scene.mouse_world_pos()`.
  - Klawisz `F11` zawsze przełącza pełny ekran / okno (`RESIZABLE`).
- **Delta Time (`dt`):** wszelki ruch, timery, cooldowny i interpolacja kamery muszą być niezależne od FPS i oparte o `dt` (w sekundach).
- **Grafika (Greyboxing):** dopóki Użytkownik nie dostarczy docelowych plików `.png`, używamy kolorowych powierzchni `pygame.Surface` / figur geometrycznych jako czytelnych placeholderów łatwych do późniejszej podmiany.
- **Język:**
  - Komunikacja z Użytkownikiem oraz komentarze i docstringi w kodzie: **język polski**.
  - Teksty widoczne w grze (UI, HUD, komunikaty, nazwy broni): **język angielski**.

---

## 3. Architektura i mapa modułów

| Plik | Odpowiedzialność |
|---|---|
| `main.py` | Punkt wejścia. Ustawia `SDL_RENDER_DRIVER = "direct3d"` i uruchamia `App().run()`. |
| `settings.py` | Stałe globalne: wymiary wirtualnego ekranu (`1920x1080`), okno, `FPS`, kolory, wymiary HUD, nazwa gracza. |
| `app.py` | Klasa `App`: inicjalizacja okna, letterboxing 16:9, przeliczanie pozycji myszy, główna pętla gry, zarządzanie aktywną sceną (`change_scene`, `go_to_menu`, `start_game`). |
| `scene.py` | Klasa bazowa `Scene` (`handle_event`, `update`, `draw`). |
| `menu.py` | `MenuScene`: lobby z animowanym placeholderem postaci, górny pasek i przycisk `PLAY`. |
| `play_menu.py` | `PlayCard`: zakładki `MULTIPLAYER` / `SINGLEPLAYER`, siatka kafelków trybów z `modes.py`, przycisk `JOIN`. |
| `modes.py` | Rejestr trybów gry (`CATEGORIES`, `GameMode`, lista `MODES`). **Dodanie nowego trybu = dopisanie wpisu do `MODES`.** |
| `loading.py` | `LoadingScene`: ekran ładowania przed wejściem do wybranego trybu. |
| `arena.py` | `ArenaScene`: wspólna klasa bazowa dla scen walki (gracz, strzelanie hitscan, kamera, `Hud`, `KillFeed`, pauza pod `ESC`). Podklasy implementują `update_world` oraz opcjonalnie `draw_floor`, `draw_overlay`, `handle_dead_event`. |
| `game.py` | `GameScene` (tryb *Debug*): otwarta arena testowa z nieruchomymi botami (`Bot1`..`Bot3`), strzelającym `Bot4` oraz ekranem `EliminatedScreen` (`Respawn` / `Quit`). |
| `deathmatch.py` | `DeathmatchScene`: tryb Deathmatch (10 min, 16 uczestników: gracz + 15 `AIBot`), zamknięta arena, losowanie spawnu z dala od wrogów, auto-respawn (2,5 s), `SpawnProtection`, punktacja wg broni, przejście do `ResultsScene`. |
| `maps.py` | `ArenaMap` i `make_dm_arena()`: definicja granic areny, przeszkód (`Obstacle`) i punktów spawnu. |
| `bot_ai.py` | `AIBot`: AI bota do Deathmatchu (patrol, wykrywanie celu przez `raycast` bez ścian, utrzymywanie dystansu, strafe, zmiana broni Pistol/Sniper wg dystansu, przeładowanie, strzelanie seriami z rozrzutem). |
| `scoring.py` | `Participant` (trwały stan gracza/bota między respawnami) oraz funkcja `ranking()`. |
| `results.py` | `ResultsScene`: ekran końcowy meczu z podium Top 3 oraz miejscem gracza. |
| `camera.py` | `Camera`: płynne podążanie za celem (`lerp` oparty o `math.exp(-FOLLOW_SPEED * dt)`). |
| `objects.py` | `Health` (komponent HP), `SpawnProtection` (ochrona po odrodzeniu), `GameObject` (klasa bazowa obiektów świata z ruchem `move_and_collide` dzielonym na małe kroki `MAX_STEP`), `Obstacle` (ściany/skały). |
| `entities.py` | `Player` (sterowanie WSAD, celowanie myszką, ekwipunek) oraz bazowy `Bot`. |
| `weapons.py` | `raycast` (hitscan z `rect.clipline`), `Tracer` (wizualna linia strzału), `Gun` (tryb auto/semi, `fire_rate`, `magazine_size`, `reload_time`, `damage`, `points`, obrót z kanałem alfa `SRCALPHA`), fabryki `make_pistol` / `make_sniper`, `Inventory`. |
| `ui.py` | `Hud` (amunicja + pochylony zielony pasek HP w stylu Fortnite), `InventoryBar` (sloty broni na dole ekranu w stylu Robloxa), `KillFeed` (`zabójca  broń  ofiara`), `NameTag`, `EliminatedScreen`, `EscMenu`, `MatchHud` (timer + portrety i punkty na górze ekranu). |
| `widgets.py` | Wspólne komponenty UI: `Button`, `draw_placeholder_image`. |

---

## 4. Wskazówki przy rozbudowie

1. **Nowy tryb gry:** utwórz klasę sceny (najczęściej dziedziczącą po `ArenaScene`) i zarejestruj ją w `MODES` w pliku `modes.py`.
2. **Nowa broń:** użyj klasy `Gun` w `weapons.py` (zwracając uwagę na `pygame.SRCALPHA` przy `base_image`, żeby obrót nie tworzył artefaktów w rogach) i dodaj funkcję fabrykującą `make_<weapon>()`.
3. **Nowy obiekt na mapie:** dziedzicz po `GameObject` (`objects.py`). Kolizje kontrolujesz flagą `collidable=True/False`, a zniszczalność parametrem `max_hp` (obiekt z `max_hp=None` jest niezniszczalny).
4. **Weryfikacja:** po każdej zmianie uruchom szybki test dymny (smoke test) przez `.venv\Scripts\python.exe`, aby upewnić się, że wszystkie moduły się importują, a sceny wykonują `update(dt)` i `draw(canvas)` bez błędów.
