import os

# Load .env manually to avoid dependencies
DEBUG = False
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("DEBUG="):
                val = line.strip().split("=")[1].lower()
                DEBUG = val == "true"
                break
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
