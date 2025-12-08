import pygame
import sys
from .physics import PhysicsWorld
from .lander import Lander
from .terrain import Terrain
from .ui import HUD, Menu, GameOverMenu
from .editor import TerrainEditor
from .utils import WHITE
import pymunk

SCREEN_WIDTH, SCREEN_HEIGHT = 1800, 900


def to_pygame(p, height):
    """Convert pymunk coordinates to pygame coordinates."""
    return int(p.x), int(height - p.y)


def start_game(gravity, difficulty):
    physics_space = PhysicsWorld(gravity)
    terrain = Terrain(physics_space.space, SCREEN_WIDTH, SCREEN_HEIGHT, difficulty)
    lander = Lander(physics_space.space, pos=(SCREEN_WIDTH // 5, SCREEN_HEIGHT - 100), starting_fuel=0.1)
    return physics_space, terrain, lander


def main():
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Lunar Lander")
    clock = pygame.time.Clock()

    physics_space = None
    terrain = None
    lander = None
    hud = HUD()
    menu = Menu()
    game_over_menu = GameOverMenu()
    editor = TerrainEditor(SCREEN_WIDTH, SCREEN_HEIGHT)

    state = "MENU"
    crash_timer = 0.0
    crash_fuel = 0.0
    crash_vel = pymunk.Vec2d(0, 0)
    crash_angle = 0.0
    result_text = ""
    mouse_origin_y = 0
    total_time = 0.0
    fps = 30

    running = True

    while running:
        dt = 1.0 / fps
        total_time += dt

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        if state == "MENU":
            action = menu.handle_input(events)
            if action == "GAME":
                state = "GAME"
                physics_space, terrain, lander = start_game(menu.gravity, menu.difficulty)
                mouse_origin_y = pygame.mouse.get_pos()[1]
                total_time = 0.0
            elif action == "EDITOR":
                state = "EDITOR"

            screen.fill((0, 0, 0))  # Clear screen for menu
            menu.draw(screen)

        elif state == "EDITOR":
            action = editor.handle_input(events)
            if action == "MENU":
                state = "MENU"
            elif action == "QUIT":
                running = False

            editor.update()
            editor.draw(screen)

        elif state == "GAME":
            # Input
            keys = pygame.key.get_pressed()

            # Prevent thrust if space is still held from menu
            if not hasattr(physics_space, "space_released"):
                if not keys[pygame.K_SPACE]:
                    physics_space.space_released = True

            if lander and getattr(physics_space, "space_released", False):
                lander.is_thrusting = False

                # Mouse control
                current_mouse_y = pygame.mouse.get_pos()[1]
                # Up is negative in pygame, so origin - current gives positive for upward movement
                mouse_delta = mouse_origin_y - current_mouse_y
                throttle_pct = max(0.0, min(1.0, mouse_delta / 200.0))  # 200 pixels range

                if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                    throttle_pct = 1.0

                if throttle_pct > 0:
                    lander.thrust(throttle_pct, dt)

                if keys[pygame.K_LEFT]:
                    lander.rotate(1)
                elif keys[pygame.K_RIGHT]:
                    lander.rotate(-1)
                else:
                    lander.stop_rotation()

            # Check for pause/menu
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    state = "MENU"

            # Physics
            physics_space.step(dt)

            # Check game state
            if physics_space.crashed:
                print("CRASHED!")
                # Capture stats
                crash_fuel = lander.fuel_remaining
                crash_vel = lander.get_velocity()
                crash_angle = lander.body.angle * (180.0 / 3.14159)  # Convert to degrees

                lander.explode()
                physics_space.crashed = False
                lander = None  # Disable control
                state = "CRASH_ANIMATION"
                crash_timer = 4.0
                result_text = "CRASHED!"

            elif physics_space.landed:
                lander.landed = True
                print("Level Complete!")
                physics_space.landed = False
                state = "GAME_OVER"
                result_text = "SUCCESSFUL LANDING!"

            # Render
            screen.fill((0, 0, 0))
            terrain.draw(screen, SCREEN_HEIGHT)

            if lander:
                lander.draw(screen, SCREEN_HEIGHT)

                # HUD
                vel = lander.get_velocity()
                alt = lander.get_altitude()

                # Ensure we pass the current fuel value
                hud.draw(
                    screen,
                    vel,
                    lander.fuel_remaining,
                    lander.fuel_capacity,
                    alt,
                    lander.throttle_pct,
                    total_time,
                )
            else:
                # Draw debris
                for body in physics_space.space.bodies:
                    if body.body_type == pymunk.Body.DYNAMIC:
                        for shape in body.shapes:
                            if isinstance(shape, pymunk.Poly):
                                points = []
                                for v in shape.get_vertices():
                                    p_world = body.local_to_world(v)
                                    points.append(to_pygame(p_world, SCREEN_HEIGHT))
                                pygame.draw.polygon(screen, WHITE, points, 2)

        elif state == "CRASH_ANIMATION":
            # Step physics to animate debris
            physics_space.step(dt)
            crash_timer -= dt

            if crash_timer <= 0:
                state = "GAME_OVER"

            # Render
            screen.fill((0, 0, 0))
            terrain.draw(screen, SCREEN_HEIGHT)

            # Draw debris
            for body in physics_space.space.bodies:
                if body.body_type == pymunk.Body.DYNAMIC:
                    for shape in body.shapes:
                        if isinstance(shape, pymunk.Poly):
                            points = []
                            for v in shape.get_vertices():
                                p_world = body.local_to_world(v)
                                points.append(to_pygame(p_world, SCREEN_HEIGHT))
                            pygame.draw.polygon(screen, shape.color, points, 0)

        elif state == "GAME_OVER":
            # Render game background (frozen)
            # We need to render the game objects but not step physics
            screen.fill((0, 0, 0))
            terrain.draw(screen, SCREEN_HEIGHT)

            if lander:
                lander.draw(screen, SCREEN_HEIGHT)
            else:
                # Draw debris
                for body in physics_space.space.bodies:
                    if body.body_type == pymunk.Body.DYNAMIC:
                        for shape in body.shapes:
                            if isinstance(shape, pymunk.Poly):
                                points = []
                                for v in shape.get_vertices():
                                    p_world = body.local_to_world(v)
                                    points.append(to_pygame(p_world, SCREEN_HEIGHT))
                                pygame.draw.polygon(screen, shape.color, points, 0)

            # Draw Game Over Menu
            stats = None
            if result_text == "CRASHED!":
                stats = {
                    "fuel": crash_fuel,
                    "vx": crash_vel.x,
                    "vy": crash_vel.y,
                    "angle": crash_angle,
                }
            game_over_menu.draw(screen, result_text, stats)

            action = game_over_menu.handle_input(events)
            if action == "RESTART":
                state = "GAME"
                physics_space, terrain, lander = start_game(menu.gravity, menu.difficulty)
                mouse_origin_y = pygame.mouse.get_pos()[1]
                total_time = 0.0
            elif action == "MENU":
                state = "MENU"

        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
