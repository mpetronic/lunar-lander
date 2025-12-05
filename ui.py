import pygame
from utils import WHITE

from utils import WHITE, RED, GREEN, YELLOW, ORANGE

class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 16)
        
    def draw(self, screen, velocity, fuel):
        # velocity is a pymunk Vec2d
        vx = velocity.x
        vy = velocity.y
        
        # Velocity Readout
        # Limits: vx <= 3, vy <= 5 (downwards, so >= -5)
        # But wait, vy is negative when falling.
        # So "safe" is vy >= -5.
        # Warning: approaching limits.
        
        # Horizontal
        vx_color = WHITE
        if abs(vx) > 3.0:
            vx_color = RED
        elif abs(vx) > 2.0:
            vx_color = YELLOW
            
        vx_text = self.font.render(f"H. Vel: {abs(vx):.1f} m/s", True, vx_color)
        screen.blit(vx_text, (10, 10))
        
        # Vertical
        vy_color = WHITE
        # vy is positive up, negative down.
        # Safe landing is usually small downward velocity.
        # Say -5 to 0.
        # If vy < -5 (falling fast), it's bad.
        if vy < -5.0:
            vy_color = RED
        elif vy < -3.0:
            vy_color = YELLOW
            
        vy_text = self.font.render(f"V. Vel: {abs(vy):.1f} m/s", True, vy_color)
        screen.blit(vy_text, (10, 30))
        
        # Fuel Gauge
        # Bar at top right
        bar_width = 100
        bar_height = 20
        x = screen.get_width() - bar_width - 10
        y = 10
        
        # Background
        pygame.draw.rect(screen, (50, 50, 50), (x, y, bar_width, bar_height))
        
        # Fill
        fill_width = int((fuel / 100.0) * bar_width)
        fill_color = GREEN
        if fuel < 20:
            fill_color = RED
        elif fuel < 50:
            fill_color = ORANGE
            
        pygame.draw.rect(screen, fill_color, (x, y, fill_width, bar_height))
        
        # Text
        fuel_text = self.font.render("Fuel", True, WHITE)
        screen.blit(fuel_text, (x - 40, y))

class Menu:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 24)
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.gravity_val = 100.0
        
    def draw(self, screen):
        screen.fill((0, 0, 0))
        
        title = self.title_font.render("LUNAR LANDER", True, WHITE)
        screen.blit(title, (screen.get_width()//2 - title.get_width()//2, 100))
        
        start_text = self.font.render("Press SPACE to Start", True, WHITE)
        screen.blit(start_text, (screen.get_width()//2 - start_text.get_width()//2, 300))
        
        grav_text = self.font.render(f"Gravity: {self.gravity_val:.0f} (Left/Right to adjust)", True, WHITE)
        screen.blit(grav_text, (screen.get_width()//2 - grav_text.get_width()//2, 350))
        
    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.gravity_val = max(10, self.gravity_val - 10)
                elif event.key == pygame.K_RIGHT:
                    self.gravity_val = min(500, self.gravity_val + 10)
                elif event.key == pygame.K_SPACE:
                    return "START"
        return None
