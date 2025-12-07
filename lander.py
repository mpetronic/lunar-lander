import math
import pymunk
import pygame
import random
from pathlib import Path
from utils import app_config

explosion_palette = [
    (255, 200, 100),  # hot white core (still bright but reduced)
    (255, 180, 80),
    (255, 160, 60),
    (255, 140, 40),
    (255, 120, 30),
    (255, 100, 20),
    (240, 90, 15),
    (220, 80, 10),
    (200, 70, 8),
    (180, 65, 5),  # strong dark orange
    (160, 60, 5),
    (140, 55, 5),
    (120, 50, 5),  # deep red-orange
    (100, 45, 5),
    (90, 40, 5),
    (80, 35, 5),
    (70, 30, 8),  # very dark red with slight purple hint
    (60, 25, 8),
    (50, 20, 10),
    (40, 15, 10),  # almost black, perfect for smoke/fade-out]
]

# G₀ = 9.80665 m/s² is used — even on the Moon — because Specific Impulse (Isp) is defined and
# measured using Earth-standard gravity. This makes Isp a universal constant for a given engine in
# vacuum, regardless of where you are (Earth, Moon, Mars, deep space).
EARTH_G0 = 9.80665


class Lander:
    def __init__(self, space, pos, starting_fuel=1.0):
        self.space = space
        self.max_thrust = 45050
        self.max_torque = self.max_thrust
        self.dry_mass = 6853
        self.fuel_capacity = 8212
        self.fuel_remaining = self.fuel_capacity * starting_fuel
        self.throttle_pct = 0.0
        self.damping_factor = 0.75
        self.is_thrusting = False
        self.specific_impulse = 305

        # Create body
        total_mass = self.dry_mass + self.fuel_remaining
        moment = 40000
        self.body = pymunk.Body(mass=total_mass, moment=moment)

        self.body.position = pos
        lander_size = (50, 50)

        # Footpads for collision detection. These must be placed such that they are aligned with the
        # landing pads on the sprite image which should be at the bottom corners of the sprite
        self.body.left_foot = pymunk.Segment(
            self.body,
            (-lander_size[0] / 2, -lander_size[1] / 2),
            (-lander_size[0] / 2, -lander_size[1] / 2),
            radius=0,
        )
        self.body.right_foot = pymunk.Segment(
            self.body,
            (lander_size[0] / 2, -lander_size[1] / 2),
            (lander_size[0] / 2, -lander_size[1] / 2),
            radius=0,
        )

        self.landing_pads = [
            self.body.left_foot,
            self.body.right_foot,
        ]
        for pad in self.landing_pads:
            pad.elasticity = 0.0
            pad.friction = 1.0
            pad.collision_type = 1

        self.space.add(self.body, *self.landing_pads)
        self.is_thrusting = False

        self.image = pygame.image.load(Path(__file__).parent / "sprites" / "lander.png")
        self.image = pygame.transform.scale(self.image, lander_size)
        self.landed = False

        print("mass={:.0f} moment={:.0f}".format(self.body.mass, self.body.moment))

    def thrust(self, throttle_pct, dt):
        if self.fuel_remaining <= 0:
            self.is_thrusting = False
            return

        self.throttle_pct = throttle_pct
        desired_thrust_magnitude = self.max_thrust * throttle_pct  # Newtons

        # Direction: up in local coordinates (0, positive)
        thrust_vector = pymunk.Vec2d(0, desired_thrust_magnitude) * dt

        # Apply the full thrust impulse
        self.body.apply_impulse_at_local_point(thrust_vector)

        # Fuel burn
        propellant_flow_rate = desired_thrust_magnitude / (self.specific_impulse * EARTH_G0)
        propellant_used = propellant_flow_rate * dt
        self.fuel_remaining = max(0, self.fuel_remaining - propellant_used)
        self.body.mass = self.dry_mass + self.fuel_remaining

        self.is_thrusting = True

    def update_attitude_control(self, keys):
        # RHC input – example from pygame keys or joystick
        pitch_command = 0.0
        if keys[pygame.K_w]:  # pitch up (nose up)
            pitch_command = -1.0
        if keys[pygame.K_s]:  # pitch down
            pitch_command = +1.0

        # Real Apollo rate command law
        max_pitch_rate = 20.0  # degrees per second (Apollo max)
        desired_rate_deg = pitch_command * max_pitch_rate

        # Convert to radians
        desired_rate_rad = math.radians(desired_rate_deg)

        # Apply torque to achieve that rate (Pymunk does the rest)
        torque_needed = (desired_rate_rad - self.body.angular_velocity) * self.body.moment * 8.0
        # The "8.0" is a damping gain – tweak until it feels snappy but not twitchy

        self.body.torque = torque_needed

    def rotate(self, direction):
        self.body.torque = self.max_torque * direction

    def stop_rotation(self):
        self.body.torque = 0
        self.body.angular_velocity *= self.damping_factor

    def draw(self, screen, height):
        # Convert pymunk coordinates to pygame
        def to_pygame(p):
            return int(p.x), int(height - p.y)

        lander_center_pygame = to_pygame(self.body.position)
        rotated_image = pygame.transform.rotate(self.image, self.body.angle * 180 / 3.14159)
        image_rect = rotated_image.get_rect(center=lander_center_pygame)
        screen.blit(rotated_image, image_rect)

        # Draw pads
        if app_config.debug:
            for shape in [self.body.left_foot, self.body.right_foot]:
                p1 = to_pygame(self.body.local_to_world(shape.a))
                p2 = to_pygame(self.body.local_to_world(shape.b))
                pygame.draw.line(screen, (255, 255, 255), p1, p2, 2)

        # Draw thrust flame
        if self.is_thrusting and self.fuel_remaining > 0 and not self.landed:
            flame_y = -25
            flame_x_offset = 3
            flame_width = 4
            # Flame point relative to body bottom center and goes down from there with a minimum
            # length then scales with throttle percentage.
            flame_len = random.uniform(10, 50) * (0.1 + (0.9 * self.throttle_pct))

            f1 = self.body.local_to_world((flame_x_offset - flame_width, flame_y))
            f2 = self.body.local_to_world((flame_x_offset + flame_width, flame_y))
            f3 = self.body.local_to_world((flame_x_offset, flame_y - flame_len))

            points = [to_pygame(f1), to_pygame(f2), to_pygame(f3)]
            pygame.draw.polygon(screen, (255, 165, 0), points)  # Orange

            # Inner flame
            flame_len_inner = flame_len * 0.6
            f1_i = self.body.local_to_world((flame_x_offset - flame_width, flame_y))
            f2_i = self.body.local_to_world((flame_x_offset + flame_width, flame_y))
            f3_i = self.body.local_to_world((flame_x_offset, flame_y - flame_len_inner))

            points_i = [to_pygame(f1_i), to_pygame(f2_i), to_pygame(f3_i)]
            pygame.draw.polygon(screen, (255, 255, 0), points_i)  # Yellow

    def get_velocity(self):
        return self.body.velocity

    def get_altitude(self):
        # Feet are at local y = -50
        # Transform (0, -50) to world
        feet_pos = self.body.local_to_world((0, -50))
        return feet_pos.y

    def explode(self):
        # Remove original body and shapes
        self.space.remove(self.body, *self.landing_pads)
        # Create debris
        for n in range(1, 100):
            mass = 0.2
            s = int(n / 15.0) + 1
            size = (random.randint(s, s), random.randint(s, s))
            moment = pymunk.moment_for_box(mass, size)
            body = pymunk.Body(mass, moment)
            body.position = self.body.position
            vel_factor = 5
            vel_x = random.uniform(-vel_factor * n, vel_factor * n)
            vel_y = random.uniform(-vel_factor * 0, vel_factor * n)
            body.velocity = self.body.velocity + (vel_x, vel_y)
            body.angular_velocity = random.uniform(-10, 10)
            shape = pymunk.Poly.create_box(body, size)
            shape.elasticity = 0.8
            shape.friction = 0.8
            shape.collision_type = 0
            shape.color = random.choice(explosion_palette)
            self.space.add(body, shape)
