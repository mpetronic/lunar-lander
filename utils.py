import pygame
import math

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
