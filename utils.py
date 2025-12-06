import os

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
GRAY = (100, 100, 100)


def to_pygame(p, height):
    """Convert pymunk to pygame coordinates."""
    return int(p.x), int(height - p.y)


def from_pygame(p, height):
    """Convert pygame to pymunk coordinates."""
    return to_pygame(p, height)


class Config:
    def __init__(self):
        self.env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                for line in f:
                    key, value = line.strip().split("=")
                    for t in (int, float, bool, str):
                        if t is bool:
                            if value.strip().lower() in ("true", "false", "1", "0"):
                                self.__setattr__(key.strip().lower(), t(value.strip()))
                                break
                            continue
                        else:
                            try:
                                self.__setattr__(key.strip().lower(), t(value.strip()))
                                break
                            except ValueError:
                                pass

    def __getattr__(self, name):
        return self.__dict__.get(name.strip().lower(), None)


app_config = Config()
