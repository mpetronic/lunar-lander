import os
import pygame
import sys
from physics import PhysicsWorld
from lander import Lander
from terrain import Terrain
from ui import HUD, Menu, GameOverMenu
from editor import TerrainEditor

import pymunk

WIDTH, HEIGHT = 1800, 900
FPS = 60

WHITE = (255, 255, 255)


def to_pygame(p, height):
    """Convert pymunk coordinates to pygame coordinates."""
    return int(p.x), int(height - p.y)


def init_physics(gravity):
    physics_world = PhysicsWorld()
    physics_world.space.gravity = (0.0, 1.62 * (gravity / 100.0))
    physics_world.set_gravity(gravity)
    physics_world.crashed = False
    physics_world.landed = False
    return physics_world


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Lunar Lander")
    clock = pygame.time.Clock()

    physics_world = None  # PhysicsWorld()
    terrain = None  # Terrain(physics_world.space, WIDTH, HEIGHT)
    lander = None  # Lander(physics_world.space, (100, 500))
    hud = HUD()
    menu = Menu()
    game_over_menu = GameOverMenu()
    editor = TerrainEditor(WIDTH, HEIGHT)

    state = "MENU"  # MENU, GAME, CRASH_ANIMATION, GAME_OVER, EDITOR
    crash_timer = 0.0
    crash_fuel = 0.0
    crash_vel = pymunk.Vec2d(0, 0)
    crash_angle = 0.0
    result_text = ""

    running = True
    while running:
        dt = 1.0 / FPS

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        if state == "MENU":
            action = menu.handle_input(events)
            if action == "GAME":
                state = "GAME"
                # Re-create lander and terrain?
                # For now just ensure lander is reset
                # We need to clear space?
                # Let's just reset lander position if it exists, or create new
                # But terrain is static.
                # Ideally we should reset everything.
                # Let's simple reset:
                # Remove old lander if any
                if lander:
                    # Remove shapes?
                    # Since we don't have a clean remove method that handles everything perfectly if we lost reference
                    # But we have `lander` reference.
                    # Actually, let's just create a new physics world for a fresh game?
                    # That's cleaner.
                    pass

                physics_world = init_physics(menu.gravity_val)
                terrain = Terrain(physics_world.space, WIDTH, HEIGHT, menu.difficulty_val)
                lander = Lander(physics_world.space, (WIDTH // 4, HEIGHT - 100))

                # Fuel supply is dynamic based on gravity
                base_fuel = 500.0 * (menu.gravity_val / 100.0)

                lander.fuel = base_fuel
                lander.max_fuel = base_fuel

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
            if not hasattr(physics_world, "space_released"):
                if not keys[pygame.K_SPACE]:
                    physics_world.space_released = True

            if lander and getattr(physics_world, "space_released", False):
                lander.is_thrusting = False
                if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                    lander.thrust(dt)

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
            physics_world.step(dt)

            # Check game state
            if physics_world.crashed:
                print("CRASHED!")
                # Capture stats
                crash_fuel = lander.fuel
                crash_vel = lander.get_velocity()
                crash_angle = lander.body.angle * (180.0 / 3.14159)  # Convert to degrees

                lander.explode()
                physics_world.crashed = False
                lander = None  # Disable control
                state = "CRASH_ANIMATION"
                crash_timer = 4.0
                result_text = "CRASHED!"

            elif physics_world.landed:
                lander.landed = True
                print("Level Complete!")
                physics_world.landed = False
                state = "GAME_OVER"
                result_text = "SUCCESSFUL LANDING!"

            # Render
            screen.fill((0, 0, 0))
            terrain.draw(screen, HEIGHT)

            if lander:
                lander.draw(screen, HEIGHT)

                # HUD
                vel = lander.get_velocity()
                alt = lander.get_altitude()
                # Ensure we pass the current fuel value
                hud.draw(screen, vel, lander.fuel, lander.max_fuel, alt)
            else:
                # Draw debris
                for body in physics_world.space.bodies:
                    if body.body_type == pymunk.Body.DYNAMIC:
                        for shape in body.shapes:
                            if isinstance(shape, pymunk.Poly):
                                points = []
                                for v in shape.get_vertices():
                                    p_world = body.local_to_world(v)
                                    points.append(to_pygame(p_world, HEIGHT))
                                pygame.draw.polygon(screen, WHITE, points, 2)

        elif state == "CRASH_ANIMATION":
            # Step physics to animate debris
            physics_world.step(dt)
            crash_timer -= dt

            if crash_timer <= 0:
                state = "GAME_OVER"

            # Render
            screen.fill((0, 0, 0))
            terrain.draw(screen, HEIGHT)

            # Draw debris
            for body in physics_world.space.bodies:
                if body.body_type == pymunk.Body.DYNAMIC:
                    for shape in body.shapes:
                        if isinstance(shape, pymunk.Poly):
                            points = []
                            for v in shape.get_vertices():
                                p_world = body.local_to_world(v)
                                points.append(to_pygame(p_world, HEIGHT))
                            pygame.draw.polygon(screen, shape.color, points, 2)

        elif state == "GAME_OVER":
            # Render game background (frozen)
            # We need to render the game objects but not step physics
            screen.fill((0, 0, 0))
            terrain.draw(screen, HEIGHT)

            if lander:
                lander.draw(screen, HEIGHT)
            else:
                # Draw debris
                for body in physics_world.space.bodies:
                    if body.body_type == pymunk.Body.DYNAMIC:
                        for shape in body.shapes:
                            if isinstance(shape, pymunk.Poly):
                                points = []
                                for v in shape.get_vertices():
                                    p_world = body.local_to_world(v)
                                    points.append(to_pygame(p_world, HEIGHT))
                                pygame.draw.polygon(screen, shape.color, points, 2)

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
                # Reset game
                physics_world = init_physics(menu.gravity_val)
                terrain = Terrain(physics_world.space, WIDTH, HEIGHT, menu.difficulty_val)
                lander = Lander(physics_world.space, (WIDTH // 2, HEIGHT - 100))
                lander.fuel = base_fuel
            elif action == "MENU":
                state = "MENU"

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
