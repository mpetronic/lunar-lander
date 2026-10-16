import math
import pygame
import sys
from .physics import PhysicsWorld
from .lander import Lander
from .terrain import Terrain
from .ui import HUD, Menu, GameOverMenu
from .editor import TerrainEditor
from .camera import Camera
from .utils import WHITE
import pymunk

SCREEN_WIDTH, SCREEN_HEIGHT = 1800, 900


def to_pygame(p, height):
    """Convert pymunk coordinates to pygame coordinates."""
    return int(p.x), int(height - p.y)


def get_agl(physics_space, lander):
    """Calculate lander radar altitude Above Ground Level (AGL) via downward raycast."""
    if not lander or not physics_space:
        return None
    pos = lander.body.position
    query = physics_space.space.segment_query_first(
        pos,
        pymunk.Vec2d(pos.x, 0),
        1,
        pymunk.ShapeFilter(mask=0b10),
    )
    if query:
        ground_y = query.point.y
        feet_y = pos.y - 25.0
        return max(0.0, feet_y - ground_y)
    return max(0.0, lander.get_altitude())


def start_game(gravity, difficulty):
    physics_space = PhysicsWorld(gravity)
    terrain = Terrain(physics_space.space, SCREEN_WIDTH, SCREEN_HEIGHT, difficulty)

    # Scale starting fuel based on selected difficulty (1 = 100% full, down to 25% for diff 5)
    difficulty_fuel_map = {
        1: 1.0,   # 100% fuel (Difficulty 1)
        2: 0.8,   # 80% fuel  (Difficulty 2)
        3: 0.6,   # 60% fuel  (Difficulty 3)
        4: 0.4,   # 40% fuel  (Difficulty 4)
        5: 0.25,  # 25% fuel  (Difficulty 5)
    }
    starting_fuel = difficulty_fuel_map.get(
        difficulty, max(0.2, 1.0 - (difficulty - 1) * 0.2)
    )

    lander = Lander(
        physics_space.space,
        pos=(SCREEN_WIDTH // 5, SCREEN_HEIGHT - 100),
        starting_fuel=starting_fuel,
    )
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
    camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    pause_font = pygame.font.SysFont("Arial", 36, bold=True)
    pause_sub_font = pygame.font.SysFont("Arial", 18)

    state = "MENU"
    crash_timer = 0.0
    crash_fuel = 0.0
    crash_vel = pymunk.Vec2d(0, 0)
    crash_angle = 0.0
    crash_reason = ""
    crash_reasons = []
    result_text = ""
    mouse_origin_y = 0
    total_time = 0.0
    throttle_trim = 0.0
    agl = None
    fps = 30

    running = True

    while running:
        dt = 1.0 / fps
        if state == "GAME":
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
                throttle_trim = 0.0
                camera.reset()
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

                # Mouse control with wheel trim
                current_mouse_y = pygame.mouse.get_pos()[1]
                # Up is negative in pygame, so origin - current gives positive for upward movement
                mouse_delta = mouse_origin_y - current_mouse_y
                coarse_throttle = mouse_delta / 200.0  # 200 pixels range
                throttle_pct = max(0.0, min(1.0, coarse_throttle + throttle_trim))

                if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                    throttle_pct = 1.0

                if throttle_pct > 0:
                    lander.thrust(throttle_pct, dt)

                # Tilt control (Left/Right arrows or A/D keys)
                # Hold Shift for fine-trim micro-adjustments (~35% sensitivity) to easily nail 0.0° attitude
                tilt_scale = 0.35 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    lander.rotate(1, scale=tilt_scale)
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    lander.rotate(-1, scale=tilt_scale)
                else:
                    lander.stop_rotation()

            # Check for pause/menu and mouse wheel trim
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = "MENU"
                    elif event.key == pygame.K_p:
                        state = "PAUSED"
                elif event.type == pygame.MOUSEWHEEL:
                    # Fine-tune thrust: 3x more sensitive than raw mouse movement
                    # Raw mouse movement is 1.0 / 200.0 per pixel = 0.005 (0.5% per pixel)
                    # 3x more sensitive (finer increment) = 1.0 / (200.0 * 3.0) = ~0.001667 per notch (0.167% per notch)
                    trim_step = 1.0 / (200.0 * 3.0)
                    throttle_trim += event.y * trim_step
                    throttle_trim = max(-1.0, min(1.0, throttle_trim))

            # Physics
            physics_space.step(dt)

            # Calculate radar altitude Above Ground Level (AGL) and update camera
            agl = get_agl(physics_space, lander)
            camera.update(lander.body.position if lander else None, agl, dt)

            # Check game state
            if physics_space.crashed:
                print("CRASHED!")
                # Capture stats and detailed failure reasons
                crash_fuel = lander.fuel_remaining
                crash_vel = lander.get_velocity()
                crash_angle = lander.body.angle * (180.0 / 3.14159)  # Convert to degrees

                crash_reasons = list(getattr(physics_space, "crash_reasons", []))
                if crash_fuel <= 0 and not any("depleted" in r for r in crash_reasons):
                    crash_reasons.append("Propellant completely depleted (Out of fuel)")

                crash_reason = (
                    " • ".join(crash_reasons)
                    if crash_reasons
                    else getattr(physics_space, "crash_reason", "Impact threshold exceeded")
                )

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
            terrain.draw(screen, SCREEN_HEIGHT, camera)

            if lander:
                lander.draw(screen, SCREEN_HEIGHT, camera)

                # HUD
                vel = lander.get_velocity()
                hud_alt = agl if agl is not None else lander.get_altitude()

                # Ensure we pass current velocity, fuel, alt, throttle, time, attitude angle, trim, and zoom
                hud.draw(
                    screen,
                    vel,
                    lander.fuel_remaining,
                    lander.fuel_capacity,
                    hud_alt,
                    lander.throttle_pct,
                    total_time,
                    angle=lander.body.angle,
                    trim_pct=throttle_trim,
                    zoom=camera.zoom,
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
                                    points.append(camera.to_screen(p_world))
                                pygame.draw.polygon(screen, WHITE, points, 2)

        elif state == "PAUSED":
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        state = "GAME"
                        # Re-sync mouse origin so throttle doesn't jump
                        mouse_origin_y = pygame.mouse.get_pos()[1]
                    elif event.key == pygame.K_ESCAPE:
                        state = "MENU"

            # Render frozen game frame
            screen.fill((0, 0, 0))
            terrain.draw(screen, SCREEN_HEIGHT, camera)

            if lander:
                lander.draw(screen, SCREEN_HEIGHT, camera)

                # HUD
                vel = lander.get_velocity()
                hud_alt = agl if agl is not None else lander.get_altitude()

                hud.draw(
                    screen,
                    vel,
                    lander.fuel_remaining,
                    lander.fuel_capacity,
                    hud_alt,
                    lander.throttle_pct,
                    total_time,
                    angle=lander.body.angle,
                    trim_pct=throttle_trim,
                    zoom=camera.zoom,
                )
            else:
                for body in physics_space.space.bodies:
                    if body.body_type == pymunk.Body.DYNAMIC:
                        for shape in body.shapes:
                            if isinstance(shape, pymunk.Poly):
                                points = []
                                for v in shape.get_vertices():
                                    p_world = body.local_to_world(v)
                                    points.append(camera.to_screen(p_world))
                                pygame.draw.polygon(screen, WHITE, points, 2)

            # Draw PAUSED overlay banner
            banner_w, banner_h = 420, 110
            overlay = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
            overlay.fill((12, 18, 28, 225))
            pygame.draw.rect(
                overlay, (60, 140, 220), (0, 0, banner_w, banner_h), width=2, border_radius=8
            )

            p_surf = pause_font.render("GAME PAUSED", True, (240, 245, 255))
            s_surf = pause_sub_font.render("Press 'P' to Resume  •  ESC for Menu", True, (160, 185, 215))

            overlay.blit(p_surf, (banner_w // 2 - p_surf.get_width() // 2, 22))
            overlay.blit(s_surf, (banner_w // 2 - s_surf.get_width() // 2, 68))

            screen.blit(
                overlay,
                ((SCREEN_WIDTH - banner_w) // 2, (SCREEN_HEIGHT - banner_h) // 2),
            )

        elif state == "CRASH_ANIMATION":
            # Step physics to animate debris
            physics_space.step(dt)
            crash_timer -= dt

            # Keep camera updated
            camera.update(None, None, dt)

            if crash_timer <= 0:
                state = "GAME_OVER"

            # Render
            screen.fill((0, 0, 0))
            terrain.draw(screen, SCREEN_HEIGHT, camera)

            # Draw debris
            for body in physics_space.space.bodies:
                if body.body_type == pymunk.Body.DYNAMIC:
                    for shape in body.shapes:
                        if isinstance(shape, pymunk.Poly):
                            points = []
                            for v in shape.get_vertices():
                                p_world = body.local_to_world(v)
                                points.append(camera.to_screen(p_world))
                            pygame.draw.polygon(screen, shape.color, points, 0)

            # Draw live crash reason banner during explosion animation
            banner_w = 640
            banner_h = 70 + (len(crash_reasons) * 24 if crash_reasons else 24)
            overlay = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
            overlay.fill((30, 10, 15, 230))
            pygame.draw.rect(
                overlay, (245, 75, 75), (0, 0, banner_w, banner_h), width=2, border_radius=8
            )

            c_surf = pause_font.render("CRASH DETECTED", True, (255, 80, 80))
            overlay.blit(c_surf, (banner_w // 2 - c_surf.get_width() // 2, 10))

            cur_y = 48
            for r in (crash_reasons if crash_reasons else [crash_reason]):
                r_surf = pause_sub_font.render(f"•  {r}", True, (255, 205, 205))
                overlay.blit(r_surf, (banner_w // 2 - r_surf.get_width() // 2, cur_y))
                cur_y += 24

            screen.blit(overlay, ((SCREEN_WIDTH - banner_w) // 2, 130))

        elif state == "GAME_OVER":
            # Render game background (frozen)
            # We need to render the game objects but not step physics
            screen.fill((0, 0, 0))
            terrain.draw(screen, SCREEN_HEIGHT, camera)

            if lander:
                lander.draw(screen, SCREEN_HEIGHT, camera)
            else:
                # Draw debris
                for body in physics_space.space.bodies:
                    if body.body_type == pymunk.Body.DYNAMIC:
                        for shape in body.shapes:
                            if isinstance(shape, pymunk.Poly):
                                points = []
                                for v in shape.get_vertices():
                                    p_world = body.local_to_world(v)
                                    points.append(camera.to_screen(p_world))
                                pygame.draw.polygon(screen, shape.color, points, 0)

            # Draw Game Over Menu
            stats = None
            if result_text == "CRASHED!":
                stats = {
                    "fuel": crash_fuel,
                    "vx": crash_vel.x,
                    "vy": crash_vel.y,
                    "angle": crash_angle,
                    "reason": crash_reason,
                    "reasons": crash_reasons,
                }
            elif result_text == "SUCCESSFUL LANDING!":
                stats = {
                    "fuel": lander.fuel_remaining if lander else 0.0,
                    "vx": lander.get_velocity().x if lander else 0.0,
                    "vy": lander.get_velocity().y if lander else 0.0,
                    "angle": math.degrees(lander.body.angle) if lander else 0.0,
                }
            game_over_menu.draw(screen, result_text, stats)

            action = game_over_menu.handle_input(events)
            if action == "RESTART":
                state = "GAME"
                physics_space, terrain, lander = start_game(menu.gravity, menu.difficulty)
                mouse_origin_y = pygame.mouse.get_pos()[1]
                total_time = 0.0
                throttle_trim = 0.0
                camera.reset()
            elif action == "MENU":
                state = "MENU"

        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
