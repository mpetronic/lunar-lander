import pymunk
import pygame
from utils import to_pygame, WHITE

class Lander:
    def __init__(self, space, pos):
        self.space = space
        self.fuel = 100.0
        
        # Create body
        self.body = pymunk.Body(mass=1, moment=10)
        self.body.position = pos
        
        # Shapes
        # Main body
        self.main_shape = pymunk.Poly.create_box(self.body, (20, 30))
        self.main_shape.elasticity = 0.0
        self.main_shape.friction = 0.5
        
        # Legs (simple lines or small boxes)
        # Left leg
        self.leg_l = pymunk.Segment(self.body, (-10, -15), (-15, -25), 2)
        self.leg_l.elasticity = 0.0
        self.leg_l.friction = 1.0
        
        # Right leg
        self.leg_r = pymunk.Segment(self.body, (10, -15), (15, -25), 2)
        self.leg_r.elasticity = 0.0
        self.leg_r.friction = 1.0
        
        # Footpads
        self.foot_l = pymunk.Segment(self.body, (-18, -25), (-12, -25), 2)
        self.foot_l.elasticity = 0.0
        self.foot_l.friction = 1.0
        
        self.foot_r = pymunk.Segment(self.body, (12, -25), (18, -25), 2)
        self.foot_r.elasticity = 0.0
        self.foot_r.friction = 1.0
        
        self.shapes = [self.main_shape, self.leg_l, self.leg_r, self.foot_l, self.foot_r]
        for shape in self.shapes:
            shape.collision_type = 1 # COLLISION_LANDER
            
        self.space.add(self.body, *self.shapes)
        
    def thrust(self, dt):
        if self.fuel > 0:
            # Apply impulse in local Y direction
            force = (0, 300) # Adjust force magnitude
            self.body.apply_impulse_at_local_point(force, (0, 0))
            self.fuel -= 10.0 * dt
            return True
        return False
        
    def rotate(self, direction):
        # Apply torque
        torque = 2000 * direction
        self.body.apply_force_at_local_point((torque, 0), (0, 10)) # Apply sideways force at top? No, torque is better but Pymunk uses torque on body
        self.body.torque = torque
        
    def stop_rotation(self):
        self.body.torque = 0
        self.body.angular_velocity *= 0.95 # Damping
        
    def draw(self, screen, height):
        # Draw body
        p = to_pygame(self.body.position, height)
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
            pygame.draw.line(screen, WHITE, p1, p2, 2)
            
    def get_velocity(self):
        return self.body.velocity
        
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
        shape.collision_type = 0 # Default, no special handling needed or maybe debris type
        
        self.space.add(body, shape)
        return body, shape

class Terrain:
    def __init__(self, space, width, height):
        self.space = space
        self.width = width
        self.height = height
        self.lines = []
        self.generate()
        
    def generate(self):
        import random
        
        # Terrain parameters
        num_points = 100
        segment_width = self.width / (num_points - 1)
        points = []
        
        # Landing pads (start_index, length)
        # We want 3 pads. Let's place them somewhat randomly but ensuring they don't overlap too close
        pad_width_indices = 5 # roughly 5 segments wide
        pad_indices = []
        
        # Simple logic to place 3 pads
        attempts = 0
        while len(pad_indices) < 3 and attempts < 100:
            idx = random.randint(10, num_points - 10 - pad_width_indices)
            valid = True
            for existing_idx in pad_indices:
                if abs(idx - existing_idx) < 15: # Minimum distance between pads
                    valid = False
                    break
            if valid:
                pad_indices.append(idx)
            attempts += 1
            
        pad_indices.sort()
        
        # Generate heights
        current_height = self.height / 4
        
        for i in range(num_points):
            # Check if we are in a pad
            in_pad = False
            pad_height = 0
            
            for pid in pad_indices:
                if pid <= i < pid + pad_width_indices:
                    in_pad = True
                    # If it's the start of the pad, set the height for the whole pad
                    if i == pid:
                        # Flatten
                        pass 
                    break
            
            if in_pad:
                # Keep height constant
                pass
            else:
                # Random variation
                change = random.uniform(-20, 20)
                current_height += change
                # Clamp height
                current_height = max(50, min(current_height, self.height / 2))
            
            points.append((i * segment_width, current_height))
            
        # Fix pad heights (make them flat)
        for pid in pad_indices:
            # Get height at start of pad
            h = points[pid][1]
            for k in range(pad_width_indices):
                points[pid + k] = (points[pid + k][0], h)
                
        # Create Pymunk segments
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            segment = pymunk.Segment(self.space.static_body, p1, p2, 2)
            segment.elasticity = 0.5
            segment.friction = 1.0
            segment.collision_type = 2 # COLLISION_TERRAIN
            
            # Check if this segment is part of a pad
            # We know pads are flat, so p1.y == p2.y
            # And we can check if it was generated as a pad
            # But simpler: we know the indices.
            # Let's just check if it's flat? No, flat areas could exist naturally (unlikely with random float)
            # Let's use the pad_indices logic again or just check slope
            if p1[1] == p2[1]:
                segment.is_pad = True
            else:
                segment.is_pad = False
                
            self.space.add(segment)
            self.lines.append(segment)
        
    def draw(self, screen, height):
        for line in self.lines:
            p1 = to_pygame(line.a, height)
            p2 = to_pygame(line.b, height)
            pygame.draw.line(screen, WHITE, p1, p2, 2)
