import os
import pymunk
import pygame
import random
from utils import DEBUG

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


class Lander:
    def __init__(self, space, pos):
        self.space = space
        self.fuel = 100.0
        self.max_fuel = 100.0

        self.thrust_force = 1.2
        self.torque_force = 40.0
        self.damping_factor = 0.75
        self.fuel_consumption_rate = 5.0

        # Create body
        self.body = pymunk.Body(mass=1, moment=10)
        self.body.position = pos

        # Footpads for collision detection. These must be placed such that they are aligned with the
        # landing pads on the sprite image
        self.foot_l = pymunk.Segment(self.body, (-50, -47), (-45, -47), radius=4)
        self.foot_r = pymunk.Segment(self.body, (45, -47), (50, -47), radius=4)

        self.shapes = [
            self.foot_l,
            self.foot_r,
        ]
        for shape in self.shapes:
            shape.elasticity = 0.0
            shape.friction = 1.0
            shape.collision_type = 1

        self.space.add(self.body, *self.shapes)
        self.is_thrusting = False

        self.image = pygame.image.load(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "lander.png")
        )
        self.image = pygame.transform.scale(self.image, (100, 100))
        self.landed = False

    def thrust(self, dt):
        if self.fuel > 0:
            self.is_thrusting = True
            # Apply impulse in local Y direction
            force = (0, self.thrust_force)
            self.body.apply_impulse_at_local_point(force, (0, 0))
            self.fuel -= self.thrust_force * self.fuel_consumption_rate * dt
            return True
        return False

    def rotate(self, direction):
        # Apply torque
        torque = self.torque_force * direction
        # self.body.apply_force_at_local_point((torque, 0), (0, 20))
        self.body.torque = torque

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
        if DEBUG:
            for shape in [self.foot_l, self.foot_r]:
                p1 = to_pygame(self.body.local_to_world(shape.a))
                p2 = to_pygame(self.body.local_to_world(shape.b))
                pygame.draw.line(screen, (255, 255, 255), p1, p2, 2)

        # Draw thrust flame
        if self.is_thrusting and self.fuel > 0 and not self.landed:
            flame_y = -40
            flame_x_offset = 5
            flame_width = 5
            # Flame point relative to body: bottom center is (0, -30)
            # Flame goes down from there.
            # Triangle: (-10, -30), (10, -30), (0, -30 - length)
            flame_len = random.uniform(10, 50)

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
        self.space.remove(self.body, *self.shapes)
        # Create debris
        for n in range(1, 100):
            mass = 0.2
            s = int(n / 8.0) + 1
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
            shape.fill = random.choice(explosion_palette)
            self.space.add(body, shape)
