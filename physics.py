import pymunk

class PhysicsWorld:
    def __init__(self):
        self.space = pymunk.Space()
        self.space.gravity = (0.0, -100.0)  # Reduced gravity for better playability initially
        
        self.COLLISION_LANDER = 1
        self.COLLISION_TERRAIN = 2
        
        self.space.on_collision(self.COLLISION_LANDER, self.COLLISION_TERRAIN, begin=self.handle_collision)
        
        self.landed = False
        self.crashed = False
        
    def handle_collision(self, arbiter, space, data):
        # Get shapes
        lander_shape = arbiter.shapes[0]
        terrain_shape = arbiter.shapes[1]
        
        # Ensure correct order
        if lander_shape.collision_type != self.COLLISION_LANDER:
            lander_shape, terrain_shape = terrain_shape, lander_shape
            
        # Check if already handled
        if self.crashed or self.landed:
            return True
            
        # Get Lander body
        body = lander_shape.body
        
        # Check velocity
        # Pymunk y is up, so negative vy is falling.
        vx = body.velocity.x
        vy = body.velocity.y
        
        # Check angle (in radians). 0 is upright.
        angle = body.angle
        
        # Limits
        MAX_VX = 10.0 
        MAX_VY = -5.0 # Downward velocity is negative, so we check if vy >= -5.0 (i.e. closer to 0)
        MAX_ANGLE = 0.2 # radians
        
        # Check if terrain is pad
        is_pad = getattr(terrain_shape, 'is_pad', False)
        
        # Logic
        # Note: Pymunk y-axis is up. Gravity is down (-y).
        # Falling velocity is negative.
        # "Exceeds 5 m/s" means abs(vy) > 5.
        # So safe if abs(vy) <= 5.
        safe_vertical = abs(vy) <= abs(MAX_VY)
        safe_horizontal = abs(vx) <= MAX_VX
        safe_angle = abs(angle) <= MAX_ANGLE
        
        safe_position = False
        if is_pad:
            # Check if lander is fully within pad bounds
            # Pad is a segment from a to b
            pad_x1 = min(terrain_shape.a.x, terrain_shape.b.x)
            pad_x2 = max(terrain_shape.a.x, terrain_shape.b.x)
            
            # Lander width check
            # Lander feet are at +/- 36 from center (approx)
            # Let's use a slightly wider margin to be safe or exact?
            # User said "both lander landing legs".
            # Left foot outer edge is roughly -36, Right is +36.
            lander_x = body.position.x
            lander_left = lander_x - 36
            lander_right = lander_x + 36
            
            if lander_left >= pad_x1 and lander_right <= pad_x2:
                safe_position = True
            else:
                print(f"Missed pad bounds: Pad({pad_x1:.1f}, {pad_x2:.1f}) Lander({lander_left:.1f}, {lander_right:.1f})")
        
        if is_pad and safe_vertical and safe_horizontal and safe_angle and safe_position:
            self.landed = True
            print("LANDED SAFE!")
        else:
            self.crashed = True
            print(f"CRASHED! vx={vx:.1f}, vy={vy:.1f}, angle={angle:.2f}, pad={is_pad}, pos={safe_position}")
            
        return True
        
    def set_gravity(self, val):
        self.space.gravity = (0.0, -val)

    def step(self, dt):
        self.space.step(dt)
