import pymunk
import pygame
from utils import to_pygame, GRAY


class Terrain:
    def __init__(self, space, width, height):
        self.space = space
        self.width = width
        self.height = height
        self.lines = []
        self.generate()

    def generate(self):
        import random
        import json
        import os

        TERRAIN_FILE = "terrain_data.json"

        terrain_data = []  # List of {'x': float, 'y': float, 'isPad': bool}

        # Check if we should load
        should_load = False
        if os.path.exists(TERRAIN_FILE):
            try:
                with open(TERRAIN_FILE, "r") as f:
                    data = json.load(f)
                    # Check for new format
                    if isinstance(data, list) and len(data) > 0 and "isPad" in data[0]:
                        terrain_data = data
                        should_load = True
                        print("Loaded terrain from file (new format).")
                    elif "points" in data:
                        # Old format, force regen
                        print("Old terrain format detected. Regenerating...")
            except Exception as e:
                print(f"Failed to load terrain: {e}")

        if not should_load:
            print("Generating new terrain with updated constraints...")

            # Constraints
            PAD_WIDTH = 120
            MIN_GAP_PADS = 200
            MIN_GAP_EDGE = 200
            PAD_Y_MIN = 50
            PAD_Y_MAX = self.height * 0.25
            MIN_SEGMENTS_BETWEEN = 30

            # 1. Generate Pad Locations
            pads = []  # List of (x_start, y)

            attempts = 0
            while len(pads) < 3 and attempts < 1000:
                x = random.uniform(MIN_GAP_EDGE, self.width - MIN_GAP_EDGE - PAD_WIDTH)

                valid = True
                for px, py in pads:
                    if not (x + PAD_WIDTH < px - MIN_GAP_PADS or x > px + PAD_WIDTH + MIN_GAP_PADS):
                        valid = False
                        break

                if valid:
                    y = random.uniform(PAD_Y_MIN, PAD_Y_MAX)
                    pads.append((x, y))

                attempts += 1

            if len(pads) < 3:
                print("Failed to generate valid pads, using fallback")
                pads = [(200, 100), (self.width / 2 - 60, 150), (self.width - 320, 120)]

            pads.sort(key=lambda p: p[0])

            # 2. Generate Terrain Points

            def generate_rough_segment(p1, p2, num_segments):
                # Generates points BETWEEN p1 and p2 (exclusive of p1, inclusive of p2?)
                # We want to append points to the list.
                # p1 is the last point added.
                # We add num_segments points.
                # The last point added should be p2.

                pts = []
                dx = (p2[0] - p1[0]) / num_segments
                current_y = p1[1]

                for i in range(1, num_segments):
                    target_x = p1[0] + i * dx

                    remaining_steps = num_segments - i + 1
                    slope_needed = (p2[1] - current_y) / remaining_steps

                    noise = random.uniform(-15, 15)
                    next_y = current_y + slope_needed + noise
                    next_y = max(20, min(next_y, self.height * 0.6))

                    # These are NOT pads
                    pts.append({"x": target_x, "y": next_y, "isPad": False})
                    current_y = next_y

                return pts

            # Start point
            start_y = random.uniform(self.height * 0.1, self.height * 0.4)
            current_point = (0, start_y)
            terrain_data.append({"x": 0, "y": start_y, "isPad": False})

            for i in range(3):
                pad_x, pad_y = pads[i]
                pad_start = (pad_x, pad_y)
                pad_end = (pad_x + PAD_WIDTH, pad_y)

                # Gap
                dist = pad_start[0] - current_point[0]
                n_segments = max(MIN_SEGMENTS_BETWEEN, int(dist / 10))

                gap_pts = generate_rough_segment(current_point, pad_start, n_segments)
                terrain_data.extend(gap_pts)

                # Add Pad Start
                # The segment STARTING at pad_start is a pad.
                terrain_data.append({"x": pad_start[0], "y": pad_start[1], "isPad": True})

                # Add Pad End
                # The segment STARTING at pad_end is NOT a pad (it's the start of the next gap)
                terrain_data.append({"x": pad_end[0], "y": pad_end[1], "isPad": False})

                current_point = pad_end

            # Final gap
            end_target = (self.width, random.uniform(self.height * 0.1, self.height * 0.4))
            dist = end_target[0] - current_point[0]
            n_segments = max(MIN_SEGMENTS_BETWEEN, int(dist / 10))

            gap_pts = generate_rough_segment(current_point, end_target, n_segments)
            terrain_data.extend(gap_pts)

            # Add final point
            terrain_data.append({"x": end_target[0], "y": end_target[1], "isPad": False})

            # Save
            with open(TERRAIN_FILE, "w") as f:
                json.dump(terrain_data, f, indent=4)
                print(f"Terrain saved to {TERRAIN_FILE}")

        # Create Pymunk segments
        self.lines = []
        for i in range(len(terrain_data) - 1):
            p1_data = terrain_data[i]
            p2_data = terrain_data[i + 1]

            p1 = (p1_data["x"], p1_data["y"])
            p2 = (p2_data["x"], p2_data["y"])

            segment = pymunk.Segment(self.space.static_body, p1, p2, 2)
            segment.elasticity = 0.5
            segment.friction = 1.0
            segment.collision_type = 2

            # Use the stored bool
            segment.is_pad = p1_data["isPad"]

            self.space.add(segment)
            self.lines.append(segment)

    def draw(self, screen, height):
        for line in self.lines:
            p1 = to_pygame(line.a, height)
            p2 = to_pygame(line.b, height)

            if getattr(line, "is_pad", False):
                # Draw thick pad
                pygame.draw.line(screen, (184, 115, 51), p1, p2, 10)
            else:
                pygame.draw.line(screen, GRAY, p1, p2, 3)
