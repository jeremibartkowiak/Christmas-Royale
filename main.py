import os

os.environ["SDL_RENDER_DRIVER"] = "direct3d"  # musi być przed inicjalizacją Pygame (przed importem app)

from app import App  # noqa: E402

if __name__ == "__main__":
    App().run()
