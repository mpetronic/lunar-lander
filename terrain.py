import random
import json
import os
from pathlib import Path

import pymunk
import pygame
from utils import to_pygame, GRAY, app_config


class Terrain:
    def __init__(self, space, width, height, difficulty=1):
        self.space = space
        self.width = width
        self.height = height
        self.difficulty = max(1, min(5, difficulty))
        self.lines = []
        self.stars = []
        self.generate()
        self.generate_stars()

    def generate_stars(self):
        self.stars = []
        for _ in range(300):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            radius = random.randint(1, 2)
            brightness = random.randint(100, 255)
            self.stars.append({"x": x, "y": y, "r": radius, "b": brightness})

    def generate(self):
        if app_config.terrain_file:
            print("Loading test terrain...")
            terrain_filepath = app_config.terrain_file
        else:
            terrain_filepath = Path(__file__).parent / "terrain" / f"level_{self.difficulty}.json"

        terrain_data = []  # List of {'x': float, 'y': float, 'isPad': bool}

        # Check if we should load
        should_load = False
        if os.path.exists(terrain_filepath):
            try:
                with open(terrain_filepath, "r") as f:
                    data = json.load(f)
                    # Check for new format
                    if isinstance(data, list) and len(data) > 0 and "isPad" in data[0]:
                        terrain_data = data
                        should_load = True
                        print(f"Loaded terrain from {terrain_filepath}.")
                    elif "points" in data:
                        # Old format, force regen
                        print("Old terrain format detected. Regenerating...")
            except Exception as e:
                print(f"Failed to load terrain: {e}")

        if not should_load:
            print(f"Generating new terrain for level {self.difficulty}...")

            # Constraints
            PAD_WIDTH = 120
            MIN_GAP_PADS = 200
            MIN_GAP_EDGE = 200
            PAD_Y_MIN = 50
            PAD_Y_MAX = self.height * 0.25
            MIN_SEGMENTS_BETWEEN = 30

            # Difficulty settings
            # Level 1: 10% height variation
            # Level 5: 50% height variation
            # We apply this to the max change per segment or total range?
            # User said "use up to 10% of screen height in variation of segment height"
            # This implies the noise/slope can be larger.

            variation_pct = 0.1 * self.difficulty
            max_variation = self.height * variation_pct
            # We'll use this to scale the noise/slope

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
                pts = []
                dx = (p2[0] - p1[0]) / num_segments
                current_y = p1[1]

                # Scale noise based on difficulty
                # User requirement: Level 1 = 10% height variation, Level 5 = 50% height variation.
                # This variation applies to segment height differences.
                # max_variation is the total allowed variation, but per segment we should scale it.
                # Let's say the max random jump per segment is a fraction of this.
                # If we just use max_variation directly as the range, it might be too chaotic.
                # But "variation of segment height" implies the delta y.

                # Let's use max_variation as the bounds for the noise.
                # But since noise is added to slope, we should be careful.
                # Let's try setting noise_range to a fraction of max_variation, e.g., 1/3.
                # For Level 1 (90px), range is +/- 30.
                # For Level 5 (450px), range is +/- 150.

                noise_range = max_variation * 0.3

                for i in range(1, num_segments):
                    target_x = p1[0] + i * dx

                    remaining_steps = num_segments - i + 1
                    slope_needed = (p2[1] - current_y) / remaining_steps

                    noise = random.uniform(-noise_range, noise_range)
                    next_y = current_y + slope_needed + noise

                    # Clamp y to keep it somewhat reasonable, but allow higher peaks with higher difficulty
                    # Level 1: 60% height max
                    # Level 5: 90% height max?
                    max_h = self.height * (0.5 + 0.1 * self.difficulty)
                    next_y = max(20, min(next_y, max_h))

                    pts.append({"x": target_x, "y": next_y, "isPad": False})
                    current_y = next_y

                return pts

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
            with open(terrain_filepath, "w") as f:
                json.dump(terrain_data, f, indent=2)
                print(f"Terrain saved to: {terrain_filepath}")

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
        # Draw stars first
        for star in self.stars:
            color = (star["b"], star["b"], star["b"])
            pygame.draw.circle(screen, color, (star["x"], star["y"]), star["r"])

        # Create a polygon for the ground
        # Points: (0, 0), all terrain points, (width, 0)
        # Note: Pygame coordinates have (0,0) at top-left.
        # Our terrain points are in Pymunk coordinates (y up).
        # We need to convert them.

        poly_points = []
        # Start at bottom-left
        poly_points.append((0, height))

        # Add all terrain points
        # We can iterate through lines to get points in order
        # lines[0].a is the first point
        # lines[i].b is the next point

        if not self.lines:
            return

        first_pt = self.lines[0].a
        poly_points.append(to_pygame(first_pt, height))

        for line in self.lines:
            poly_points.append(to_pygame(line.b, height))

        # End at bottom-right
        poly_points.append((self.width, height))

        # Draw filled polygon
        pygame.draw.polygon(screen, (50, 50, 50), poly_points)

        # Draw surface lines
        for line in self.lines:
            p1 = to_pygame(line.a, height)
            p2 = to_pygame(line.b, height)

            if getattr(line, "is_pad", False):
                # Draw thick pad
                pygame.draw.line(screen, (70, 150, 80), p1, p2, 5)
            else:
                pygame.draw.line(screen, GRAY, p1, p2, 3)
