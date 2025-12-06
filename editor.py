import pygame
import json
import math
from ui import InputBox, WHITE, GREEN, RED


class TerrainEditor:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.points = []  # List of {'x', 'y', 'isPad'}
        self.selected_point_idx = -1
        self.dragging = False
        self.mode = "EDIT"  # EDIT, SAVE_FILENAME, PAD_WIDTH

        # Input boxes
        self.filename_box = InputBox(width // 2 - 100, height // 2, 200, 32)
        self.pad_width_box = InputBox(width // 2 - 100, height // 2, 200, 32)
        self.editing_pad_idx = -1

        # Initial point
        self.points.append({"x": 0, "y": height // 2, "isPad": False})

    def handle_input(self, events):
        for event in events:
            if self.mode == "SAVE_FILENAME":
                filename = self.filename_box.handle_event(event)
                if filename is not None:
                    self.save_terrain(filename)
                    self.mode = "EDIT"
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.mode = "EDIT"
                return "EDITOR"

            if self.mode == "PAD_WIDTH":
                width_str = self.pad_width_box.handle_event(event)
                if width_str is not None:
                    try:
                        width = float(width_str)
                        self.update_pad_width(width)
                    except ValueError:
                        pass
                    self.mode = "EDIT"
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.mode = "EDIT"
                return "EDITOR"

            if event.type == pygame.QUIT:
                return "QUIT"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "MENU"
                elif event.key == pygame.K_s:
                    self.mode = "SAVE_FILENAME"
                    self.filename_box.text = "custom_terrain.json"
                    self.filename_box.txt_surface = self.filename_box.font.render(
                        self.filename_box.text, True, self.filename_box.color
                    )
                    self.filename_box.active = True

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if event.button == 1:  # Left click
                    # Check if clicking existing point
                    clicked_idx = self.get_point_at(pos)
                    if clicked_idx != -1:
                        self.selected_point_idx = clicked_idx
                        self.dragging = True
                    else:
                        # Add new point if not dragging
                        # Insert based on x coordinate to keep sorted?
                        # Or just append? Terrain generation usually goes left to right.
                        # Let's enforce left-to-right for simplicity or just insert.
                        self.add_point(pos)

                elif event.button == 3:  # Right click
                    # Check if clicking a segment or pad
                    # If clicking a point?
                    # Let's check segments first.
                    seg_idx = self.get_segment_at(pos)
                    if seg_idx != -1:
                        # Toggle pad
                        self.toggle_pad(seg_idx)
                    else:
                        # Check if clicking a pad to edit width?
                        # Actually toggle_pad handles creation.
                        # If it is already a pad, maybe right click opens width editor?
                        # Let's check if we clicked a pad segment
                        pad_idx = self.get_pad_at(pos)
                        if pad_idx != -1:
                            self.mode = "PAD_WIDTH"
                            self.editing_pad_idx = pad_idx
                            self.pad_width_box.text = "100"  # Default or calculate current
                            self.pad_width_box.active = True

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
                    self.selected_point_idx = -1

            if event.type == pygame.MOUSEMOTION:
                if self.dragging and self.selected_point_idx != -1:
                    self.points[self.selected_point_idx]["x"] = event.pos[0]
                    self.points[self.selected_point_idx]["y"] = event.pos[1]
                    # Sort points by x?
                    # self.points.sort(key=lambda p: p['x'])
                    # If we sort, the index changes, dragging breaks.
                    # Maybe don't sort while dragging, but sort after?

        return "EDITOR"

    def update(self):
        if self.mode == "SAVE_FILENAME":
            self.filename_box.update()
        elif self.mode == "PAD_WIDTH":
            self.pad_width_box.update()

    def draw(self, screen):
        screen.fill((0, 0, 0))

        # Draw segments
        if len(self.points) > 1:
            # Sort for drawing lines correctly?
            # It's better if points are always sorted by X.
            sorted_points = sorted(self.points, key=lambda p: p["x"])

            for i in range(len(sorted_points) - 1):
                p1 = sorted_points[i]
                p2 = sorted_points[i + 1]

                color = (100, 100, 100)
                width = 2
                if p1.get("isPad", False):
                    color = (184, 115, 51)  # Brown
                    width = 6

                pygame.draw.line(screen, color, (p1["x"], p1["y"]), (p2["x"], p2["y"]), width)

        # Draw points
        for i, p in enumerate(self.points):
            color = GREEN
            if i == self.selected_point_idx:
                color = RED
            pygame.draw.circle(screen, color, (int(p["x"]), int(p["y"])), 5)

        # Draw UI
        if self.mode == "SAVE_FILENAME":
            pygame.draw.rect(
                screen,
                (0, 0, 0),
                (self.filename_box.rect.x, self.filename_box.rect.y - 30, 200, 60),
            )
            self.filename_box.draw(screen)
            msg = pygame.font.Font(None, 24).render("Enter Filename:", True, WHITE)
            screen.blit(msg, (self.filename_box.rect.x, self.filename_box.rect.y - 25))

        elif self.mode == "PAD_WIDTH":
            pygame.draw.rect(
                screen,
                (0, 0, 0),
                (self.pad_width_box.rect.x, self.pad_width_box.rect.y - 30, 200, 60),
            )
            self.pad_width_box.draw(screen)
            msg = pygame.font.Font(None, 24).render("Enter Width:", True, WHITE)
            screen.blit(msg, (self.pad_width_box.rect.x, self.pad_width_box.rect.y - 25))

        # Instructions
        info = pygame.font.Font(None, 24).render(
            "L-Click: Add/Move | R-Click Segment: Toggle Pad | R-Click Pad: Edit Width | S: Save | ESC: Menu",
            True,
            WHITE,
        )
        screen.blit(info, (10, 10))

    def get_point_at(self, pos):
        for i, p in enumerate(self.points):
            dist = math.hypot(p["x"] - pos[0], p["y"] - pos[1])
            if dist < 10:
                return i
        return -1

    def add_point(self, pos):
        self.points.append({"x": pos[0], "y": pos[1], "isPad": False})
        self.points.sort(key=lambda p: p["x"])

    def get_segment_at(self, pos):
        # Find segment closest to click
        sorted_points = sorted(self.points, key=lambda p: p["x"])
        for i in range(len(sorted_points) - 1):
            p1 = sorted_points[i]
            p2 = sorted_points[i + 1]

            # Distance from point to line segment
            # ... simple check: x within range and y close?
            if p1["x"] <= pos[0] <= p2["x"]:
                # Interpolate y
                t = (pos[0] - p1["x"]) / (p2["x"] - p1["x"])
                y = p1["y"] + t * (p2["y"] - p1["y"])
                if abs(y - pos[1]) < 10:
                    # Need to find original index of p1
                    # Because we sorted, indices changed.
                    # But we store isPad on the point itself.
                    # So we return the index in the sorted list?
                    # Wait, isPad is stored on the START point of the segment.
                    # So we need to find p1 in self.points.
                    return self.points.index(p1)
        return -1

    def get_pad_at(self, pos):
        # Similar to get_segment_at but only returns if isPad is True
        idx = self.get_segment_at(pos)
        if idx != -1:
            if self.points[idx].get("isPad", False):
                return idx
        return -1

    def toggle_pad(self, idx):
        # Toggle isPad
        # If turning ON, flatten the segment
        p1 = self.points[idx]
        # Find p2 (next in sorted order)
        sorted_points = sorted(self.points, key=lambda p: p["x"])
        p1_sorted_idx = sorted_points.index(p1)

        if p1_sorted_idx < len(sorted_points) - 1:
            p2 = sorted_points[p1_sorted_idx + 1]

            current = p1.get("isPad", False)
            p1["isPad"] = not current

            if not current:  # Turning ON
                # Flatten: set p2.y to p1.y
                p2["y"] = p1["y"]

    def update_pad_width(self, width):
        if self.editing_pad_idx != -1:
            p1 = self.points[self.editing_pad_idx]
            sorted_points = sorted(self.points, key=lambda p: p["x"])
            p1_sorted_idx = sorted_points.index(p1)

            if p1_sorted_idx < len(sorted_points) - 1:
                p2 = sorted_points[p1_sorted_idx + 1]
                # Adjust p2.x to be p1.x + width
                p2["x"] = p1["x"] + width
                # Also ensure y matches
                p2["y"] = p1["y"]

    def save_terrain(self, filename):
        # Ensure sorted
        self.points.sort(key=lambda p: p["x"])

        # Convert to format expected by Terrain loader
        # Loader expects list of objects.
        # But wait, loader expects Pymunk coordinates (y up) or Pygame (y down)?
        # Terrain.generate uses:
        # p1 = (p1_data["x"], p1_data["y"])
        # segment = pymunk.Segment(..., p1, p2, ...)
        # Pymunk uses Y up. Pygame uses Y down.
        # The existing terrain_data.json seems to have Y values like 200, 300.
        # Screen height is 900.
        # If Y is 200 in Pygame, it's near top.
        # If Y is 200 in Pymunk, it's near bottom.
        # Let's check terrain.py draw method.
        # p1 = to_pygame(line.a, height) -> int(p.x), int(height - p.y)
        # So Pymunk stores Y up.
        # The editor works in Pygame coordinates (Y down).
        # So we need to convert Y when saving.

        save_data = []
        for p in self.points:
            save_data.append(
                {
                    "x": p["x"],
                    "y": self.height - p["y"],  # Convert to Pymunk
                    "isPad": p.get("isPad", False),
                }
            )

        try:
            with open(filename, "w") as f:
                json.dump(save_data, f, indent=4)
            print(f"Saved terrain to {filename}")
        except Exception as e:
            print(f"Error saving: {e}")
