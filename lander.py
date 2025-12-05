import pymunk
import pygame
from utils import to_pygame, WHITE


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

    def thrust(self, dt):
        if self.fuel > 0:
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
        # Draw body
        to_pygame(self.body.position, height)
        # We need to rotate the points manually for drawing if we use simple pygame rects,
        # but since we have a poly, we can get vertices in world coordinates

        # Draw main shape
        points = []
        for v in self.main_shape.get_vertices():
            # v is local, need to rotate and translate
            # Actually get_vertices returns local vertices.
            # We can use body.local_to_world
            p_world = self.body.local_to_world(v)
            points.append(to_pygame(p_world, height))

        pygame.draw.polygon(screen, WHITE, points, 2)

        # Draw legs
        for shape in [self.leg_l, self.leg_r, self.foot_l, self.foot_r]:
            p1 = to_pygame(self.body.local_to_world(shape.a), height)
            p2 = to_pygame(self.body.local_to_world(shape.b), height)
            pygame.draw.line(screen, WHITE, p1, p2, 4)

    def get_velocity(self):
        return self.body.velocity

    def get_altitude(self):
        # Return the Y position of the lowest point (feet)
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
