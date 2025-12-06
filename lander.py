import os
import pymunk
import pygame


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

        # Shapes
        # Main body
        self.main_shape = pymunk.Poly.create_box(self.body, size=(40, 60), radius=6)
        self.main_shape.elasticity = 0.0
        self.main_shape.friction = 0.5

        # Legs (simple lines or small boxes)
        # Left leg
        self.leg_l = pymunk.Segment(self.body, (-20, -30), (-30, -50), radius=6)
        self.leg_l.elasticity = 0.0
        self.leg_l.friction = 1.0

        # Right leg
        self.leg_r = pymunk.Segment(self.body, (20, -30), (30, -50), radius=6)
        self.leg_r.elasticity = 0.0
        self.leg_r.friction = 1.0

        # Footpads
        self.foot_l = pymunk.Segment(self.body, (-36, -50), (-24, -50), radius=4)
        self.foot_l.elasticity = 0.0
        self.foot_l.friction = 1.0

        self.foot_r = pymunk.Segment(self.body, (24, -50), (36, -50), radius=4)
        self.foot_r.elasticity = 0.0
        self.foot_r.friction = 1.0

        self.shapes = [
            self.main_shape,
            self.leg_l,
            self.leg_r,
            self.foot_l,
            self.foot_r,
        ]
        for shape in self.shapes:
            shape.collision_type = 1  # COLLISION_LANDER

        self.space.add(self.body, *self.shapes)
        self.is_thrusting = False

        self.image = pygame.image.load(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "lander.png")
        )
        self.image = pygame.transform.scale_by(self.image, 1.0)

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
        torque = self.torque_force * direction  # Increased torque for larger body
        self.body.apply_force_at_local_point((torque, 0), (0, 20))
        self.body.torque = torque

    def stop_rotation(self):
        self.body.torque = 0
        self.body.angular_velocity *= self.damping_factor

    def draw(self, screen, height):
        # Convert pymunk coordinates to pygame
        def to_pygame(p):
            return int(p.x), int(height - p.y)

        # Draw main body
        # p = [to_pygame(self.body.local_to_world(v)) for v in self.main_shape.get_vertices()]
        # pygame.draw.polygon(screen, (200, 200, 200), p)
        # pygame.draw.polygon(screen, (255, 255, 255), p, 2)

        # Draw legs
        # for shape in [self.leg_l, self.leg_r, self.foot_l, self.foot_r]:
        #     p1 = to_pygame(self.body.local_to_world(shape.a))
        #     p2 = to_pygame(self.body.local_to_world(shape.b))
        #     pygame.draw.line(screen, (255, 255, 255), p1, p2, 2)

        lander_center_pygame = to_pygame(self.body.position)
        rotated_image = pygame.transform.rotate(self.image, self.body.angle * 180 / 3.14159)
        image_rect = rotated_image.get_rect(center=lander_center_pygame)
        screen.blit(rotated_image, image_rect)

        # Draw thrust flame
        if self.is_thrusting and self.fuel > 0:
            import random

            # Flame point relative to body: bottom center is (0, -30)
            # Flame goes down from there.
            # Triangle: (-10, -30), (10, -30), (0, -30 - length)
            flame_len = random.uniform(20, 40)

            f1 = self.body.local_to_world((-8, -30))
            f2 = self.body.local_to_world((8, -30))
            f3 = self.body.local_to_world((0, -30 - flame_len))

            points = [to_pygame(f1), to_pygame(f2), to_pygame(f3)]
            pygame.draw.polygon(screen, (255, 165, 0), points)  # Orange

            # Inner flame
            flame_len_inner = flame_len * 0.6
            f1_i = self.body.local_to_world((-4, -30))
            f2_i = self.body.local_to_world((4, -30))
            f3_i = self.body.local_to_world((0, -30 - flame_len_inner))

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

        # Create debris for each part
        # Main body
        self._create_debris(self.body.position, (20, 30), self.body.velocity)

        # Legs (approximate as small boxes for debris)
        self._create_debris(self.body.position + (-12, -20), (5, 10), self.body.velocity)
        self._create_debris(self.body.position + (12, -20), (5, 10), self.body.velocity)

    def _create_debris(self, pos, size, vel):
        import random

        mass = 0.2
        moment = pymunk.moment_for_box(mass, size)
        body = pymunk.Body(mass, moment)
        body.position = pos
        body.velocity = vel + (random.uniform(-50, 50), random.uniform(-50, 50))
        body.angular_velocity = random.uniform(-10, 10)

        shape = pymunk.Poly.create_box(body, size)
        shape.elasticity = 0.6
        shape.friction = 0.5
        shape.collision_type = 0  # Default, no special handling needed or maybe debris type

        self.space.add(body, shape)
        return body, shape
