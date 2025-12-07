import math
import pymunk


class PhysicsWorld:
    def __init__(self, gravity):
        self.space = pymunk.Space()
        self.space.gravity = (0.0, -gravity)

        self.COLLISION_LANDER = 1
        self.COLLISION_TERRAIN = 2

        self.space.on_collision(
            self.COLLISION_LANDER, self.COLLISION_TERRAIN, begin=self.handle_collision
        )

        self.landed = False
        self.crashed = False

    def handle_collision(self, arbiter, space, data):
        # Get shapes
        landing_pad = arbiter.shapes[0]
        terrain = arbiter.shapes[1]

        # Ensure correct order
        if landing_pad.collision_type != self.COLLISION_LANDER:
            landing_pad, terrain = terrain, landing_pad

        # Check if already handled
        if self.crashed or self.landed:
            return True

        # Get Lander body
        body = landing_pad.body

        # Check velocity
        vv = abs(body.velocity.y)
        vh = abs(body.velocity.x)
        total_tilt_deg = math.degrees(body.angle)

        self.crashed = not self.doghouse_safe_landing(vv, vh, total_tilt_deg)

        if self.crashed:
            print(f"CRASHED! vh={vh:.1f}, vv={vv:.1f}, angle={total_tilt_deg:.2f}")
            return True

        # Check if terrain is pad
        is_pad = getattr(terrain, "is_pad", False)
        safe_position = False
        if is_pad:
            # Check if lander is fully within pad bounds
            # Pad is a segment from a to b
            pad_l = min(terrain.a.x, terrain.b.x)
            pad_r = max(terrain.a.x, terrain.b.x)
            leg_l = body.local_to_world(body.left_foot.a).x
            leg_r = body.local_to_world(body.right_foot.a).x

            if leg_l >= pad_l and leg_r <= pad_r:
                safe_position = True
            else:
                print(
                    "Missed pad bounds: Pad({pad_l:.1f}, {pad_r:.1f}) Lander({leg_l:.1f}, {leg_r:.1f})"
                )

        if is_pad and safe_position:
            self.landed = True
            print("LANDED SAFE!")
        else:
            self.crashed = True
            print(
                f"CRASHED OFF PAD! vx={vh:.1f}, vy={vv:.1f}, angle={total_tilt_deg:.2f}, pad={is_pad}, pos={safe_position}"
            )

        return True

    def set_gravity(self, val):
        self.space.gravity = (0.0, -val)

    def step(self, dt):
        self.space.step(dt)

    def doghouse_safe_landing(self, vv_ms, vh_ms, total_tilt_deg):
        """
        Full Apollo LM safe landing check (Doghouse + Tilt).
        vv_ms = abs(lander.body.velocity.y)  # downward
        vh_ms = abs(lander.body.velocity.x)  # horizontal
        total_tilt_deg = math.degrees(math.atan2(  # or from pitch/roll
            math.sqrt(body_pitch_rad**2 + body_roll_rad**2), 1))
        """
        # Velocity Doghouse (unchanged)
        if vv_ms > 3.05 or vh_ms > 1.22:
            print(f"vv_ms ({vv_ms}) > 3.05 or vh_ms ({vh_ms}) > 1.22")
            return False
        if vv_ms <= 2.13:
            max_vh = 1.22
        else:  # Linear to 0 at 3.05 m/s
            max_vh = (4.0 / 3.0) * (3.05 - vv_ms)
        if vh_ms > max_vh:
            print(f"vh_ms ({vh_ms}) > max_vh ({max_vh})")
            return False
        # Tilt limit
        if total_tilt_deg > 12.0:
            print(f"total_tilt_deg ({total_tilt_deg}) > 12.0")
            return False
        return True
