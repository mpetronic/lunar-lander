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
        self.crash_reason = ""
        self.crash_reasons = []

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
        total_tilt_deg = abs(math.degrees(body.angle))

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
                    f"Missed pad bounds: Pad({pad_l:.1f}, {pad_r:.1f}) Lander({leg_l:.1f}, {leg_r:.1f})"
                )

        reasons = self.get_crash_reasons(vv, vh, total_tilt_deg, is_pad, safe_position)

        if not reasons and is_pad and safe_position:
            self.landed = True
            self.crashed = False
            self.crash_reason = ""
            self.crash_reasons = []
            print("LANDED SAFE!")
        else:
            self.crashed = True
            self.landed = False
            self.crash_reasons = reasons if reasons else ["Impact threshold exceeded"]
            self.crash_reason = " • ".join(self.crash_reasons)
            print(f"CRASHED! Reason: {self.crash_reason}")

        return True

    def set_gravity(self, val):
        self.space.gravity = (0.0, -val)

    def step(self, dt):
        self.space.step(dt)

    def get_crash_reasons(self, vv_ms, vh_ms, total_tilt_deg, is_pad, safe_position):
        """Evaluate touchdown parameters and return list of specific failure reasons."""
        reasons = []
        if vv_ms > 3.05:
            reasons.append(f"Excessive vertical sink rate ({vv_ms:.1f} m/s > 3.0 m/s max)")
        if vh_ms > 1.22:
            reasons.append(f"Excessive horizontal speed ({vh_ms:.1f} m/s > 1.2 m/s max)")
        elif vv_ms > 2.13 and vv_ms <= 3.05:
            max_vh = (4.0 / 3.0) * (3.05 - vv_ms)
            if vh_ms > max_vh:
                reasons.append(
                    f"Velocity envelope exceeded (H: {vh_ms:.1f} m/s exceeds safe limit for V: {vv_ms:.1f} m/s)"
                )
        if total_tilt_deg > 12.0:
            reasons.append(f"Excessive tilt angle ({total_tilt_deg:.1f}° > 12.0° max)")

        if not is_pad:
            reasons.append("Touchdown on rough terrain (Missed landing pad)")
        elif not safe_position:
            reasons.append("Landed off pad edge (Footpad outside pad bounds)")

        return reasons

    def doghouse_safe_landing(self, vv_ms, vh_ms, total_tilt_deg):
        """Full Apollo LM safe landing check (Doghouse + Tilt)."""
        reasons = self.get_crash_reasons(
            vv_ms, vh_ms, total_tilt_deg, is_pad=True, safe_position=True
        )
        return len(reasons) == 0
