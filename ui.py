import pygame
from utils import BLACK, WHITE, RED, GREEN, YELLOW, ORANGE, app_config, GRAVITY_MOON


class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 16)

    def _draw_fuel_gauge(self, screen, fuel, max_fuel):
        gauge_width = 100
        gauge_height = 20
        x = screen.get_width() - gauge_width - 10
        y = 10

        border_thickness = 2

        # Draw border
        gauge = pygame.draw.rect(screen, WHITE, (x, y, gauge_width, gauge_height), border_thickness)

        # Draw background
        display_area = pygame.draw.rect(
            screen,
            BLACK,
            (
                gauge.x + border_thickness,
                gauge.y + border_thickness,
                gauge.width - 2 * border_thickness,
                gauge.height - 2 * border_thickness,
            ),
        )

        pct_fuel_remaining = max(0.0, min(1.0, fuel / max_fuel)) if max_fuel > 0 else 0
        fill_width = int(pct_fuel_remaining * display_area.width)
        fill_color = GREEN
        if pct_fuel_remaining < 0.2:
            fill_color = RED
        elif pct_fuel_remaining < 0.3:
            fill_color = ORANGE

        pygame.draw.rect(
            screen, fill_color, (display_area.x, display_area.y, fill_width, display_area.height)
        )

        fuel_text = self.font.render(f"Fuel: {int(fuel)}", True, WHITE)
        screen.blit(fuel_text, (x - 80, y))

    def _draw_throttle_gauge(self, screen, throttle_pct):
        gauge_width = 20
        gauge_height = 100
        x = 10
        y = 100

        # Draw border and background
        border_thickness = 2
        gauge = pygame.draw.rect(screen, WHITE, (x, y, gauge_width, gauge_height), border_thickness)
        display_area = pygame.draw.rect(
            screen,
            BLACK,
            (
                gauge.x + border_thickness,
                gauge.y + border_thickness,
                gauge.width - 2 * border_thickness,
                gauge.height - 2 * border_thickness,
            ),
        )

        # Draw segments
        segment_height = 5
        segment_margin = 1

        # Calculate available height for segments
        num_segments = display_area.height // (segment_height + segment_margin)
        active_segments = int(throttle_pct * num_segments)

        start_x = display_area.x
        start_y = display_area.bottom - segment_height

        for i in range(num_segments):
            color = (200, 200, 200) if i < active_segments else (50, 50, 50)
            seg_y = start_y - i * (segment_height + segment_margin)
            pygame.draw.rect(
                screen,
                color,
                (
                    start_x,
                    seg_y,
                    display_area.width,
                    segment_height,
                ),
            )

        throttle_text = self.font.render(f"Throttle: {int(throttle_pct * 100)}", True, WHITE)
        screen.blit(throttle_text, (x, y + gauge_height + 5))

    def format_met(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        hundredths = int((seconds * 100) % 100)
        return f"{hours:03d}:{minutes:02d}:{secs:02d}.{hundredths:02d}"

    def draw(self, screen, velocity, fuel, max_fuel, altitude, throttle_pct, total_time):
        vx = velocity.x
        vy = velocity.y

        h_dir = "→" if vx > 0 else "←" if vx < 0 else ""
        v_dir = "↓" if vy < 0 else "↑" if vy > 0 else ""
        vx_color = RED if abs(vx) > 3.0 else YELLOW if abs(vx) > 2.0 else WHITE
        vy_color = RED if vy < -5.0 else YELLOW if vy < -3.0 else WHITE

        vx_text = self.font.render(f"{h_dir:<2} {abs(vx):.1f} m/s ", True, vx_color)
        screen.blit(vx_text, (10, 10))

        vy_text = self.font.render(f"{v_dir:<2} {abs(vy):.1f} m/s ", True, vy_color)
        screen.blit(vy_text, (10, 30))

        alt_text = self.font.render(f"Alt: {int(altitude)}", True, WHITE)
        screen.blit(alt_text, (10, 50))

        met = self.font.render(f"Time: {self.format_met(total_time)}", True, WHITE)
        screen.blit(met, (10, 70))

        self._draw_fuel_gauge(screen, fuel, max_fuel)
        self._draw_throttle_gauge(screen, throttle_pct)


class Menu:
    def __init__(self):
        self.font_title = pygame.font.SysFont("Arial", 50)
        self.font_option = pygame.font.SysFont("Arial", 25)
        self.gravity = app_config.gravity if app_config.gravity else GRAVITY_MOON
        self.difficulty = app_config.difficulty if app_config.difficulty else 1

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font_title.render("L U N A R  L A N D E R", True, WHITE)
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 200))

        start_text = self.font_option.render("Press SPACE to Start", True, GREEN)
        screen.blit(start_text, (screen.get_width() // 2 - start_text.get_width() // 2, 400))

        grav_text = self.font_option.render(f"< Gravity: {self.gravity:.3f} >", True, WHITE)
        screen.blit(grav_text, (screen.get_width() // 2 - grav_text.get_width() // 2, 500))

        diff_text = self.font_option.render(f"^ Difficulty: {self.difficulty} v", True, WHITE)
        screen.blit(diff_text, (screen.get_width() // 2 - diff_text.get_width() // 2, 550))

        editor_text = self.font_option.render("Press E for Terrain Editor", True, YELLOW)
        screen.blit(editor_text, (screen.get_width() // 2 - editor_text.get_width() // 2, 650))

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return "GAME"
                elif event.key == pygame.K_e:
                    return "EDITOR"
                elif event.key == pygame.K_LEFT:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.gravity = max(1, self.gravity - 1)
                    else:
                        self.gravity = max(1, self.gravity - 0.1)
                elif event.key == pygame.K_RIGHT:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.gravity = min(10, self.gravity + 1)
                    else:
                        self.gravity = min(10, self.gravity + 0.1)
                elif event.key == pygame.K_UP:
                    self.difficulty = min(5, self.difficulty + 1)
                elif event.key == pygame.K_DOWN:
                    self.difficulty = max(1, self.difficulty - 1)
        return "MENU"


class InputBox:
    def __init__(self, x, y, w, h, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color("lightskyblue3")
        self.color_active = pygame.Color("dodgerblue2")
        self.color = self.color_inactive
        self.text = text
        self.font = pygame.font.Font(None, 32)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False
        self.done = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.done = True
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = self.font.render(self.text, True, self.color)
        return None

    def update(self):
        # Resize the box if the text is too long.
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width

    def draw(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)


class GameOverMenu:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 36)
        self.small_font = pygame.font.SysFont("Arial", 24)

    def draw(self, screen, result_text, stats=None):
        # Draw semi-transparent background?
        # Just draw text over game

        text = self.font.render(result_text, True, WHITE)
        screen.blit(
            text, (screen.get_width() // 2 - text.get_width() // 2, screen.get_height() // 2 - 100)
        )

        if stats:
            # stats = {'fuel': float, 'vx': float, 'vy': float, 'angle': float}
            stats_text1 = self.small_font.render(f"Fuel: {int(stats['fuel'])}", True, WHITE)
            stats_text2 = self.small_font.render(
                f"Impact Vel: H {stats['vx']:.1f} m/s, V {stats['vy']:.1f} m/s", True, WHITE
            )
            stats_text3 = self.small_font.render(f"Angle: {stats['angle']:.1f} deg", True, WHITE)

            screen.blit(
                stats_text1,
                (
                    screen.get_width() // 2 - stats_text1.get_width() // 2,
                    screen.get_height() // 2 - 40,
                ),
            )
            screen.blit(
                stats_text2,
                (
                    screen.get_width() // 2 - stats_text2.get_width() // 2,
                    screen.get_height() // 2 - 10,
                ),
            )
            screen.blit(
                stats_text3,
                (
                    screen.get_width() // 2 - stats_text3.get_width() // 2,
                    screen.get_height() // 2 + 20,
                ),
            )

        restart_text = self.small_font.render("Press SPACE to Play Again", True, WHITE)
        screen.blit(
            restart_text,
            (
                screen.get_width() // 2 - restart_text.get_width() // 2,
                screen.get_height() // 2 + 60,
            ),
        )

        menu_text = self.small_font.render("Press ESC for Menu", True, WHITE)
        screen.blit(
            menu_text,
            (screen.get_width() // 2 - menu_text.get_width() // 2, screen.get_height() // 2 + 90),
        )

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return "RESTART"
                elif event.key == pygame.K_ESCAPE:
                    return "MENU"
        return None
