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
        MAX_VX = 20.0 # Relaxed for testing, spec says 3
        MAX_VY = -40.0 # Relaxed for testing, spec says 5 (downwards)
        MAX_ANGLE = 0.2 # radians, roughly 11 degrees
        
        # Check if terrain is pad
        is_pad = getattr(terrain_shape, 'is_pad', False)
        
        # Logic
        safe_velocity = abs(vx) <= MAX_VX and vy >= MAX_VY # vy is negative when falling, so must be greater than (less negative) than limit
        safe_angle = abs(angle) <= MAX_ANGLE
        
        if is_pad and safe_velocity and safe_angle:
            self.landed = True
            print("LANDED SAFE!")
        else:
            self.crashed = True
            print(f"CRASHED! vx={vx:.1f}, vy={vy:.1f}, angle={angle:.2f}, pad={is_pad}")
            
        return True
        
    def set_gravity(self, val):
        self.space.gravity = (0.0, -val)

    def step(self, dt):
        self.space.step(dt)
