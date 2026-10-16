import pymunk


class Camera:
    """
    Dynamic camera that smoothly tracks the lander and zooms in as the lander
    approaches the lunar surface.
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.zoom = 1.0
        self.target_zoom = 1.0

        # Camera center in unzoomed screen space
        self.cx = screen_width / 2.0
        self.cy = screen_height / 2.0

        # Zoom thresholds in AGL (Above Ground Level) meters
        self.STAGE1_AGL = 260.0  # Above 260m: 1.0x (full landing area overview)
        self.STAGE2_AGL = 110.0  # 110m - 260m: 1.8x (approach descent zoom)
        # Below 110m: 3.0x (terminal touchdown zoom)

    def reset(self):
        """Reset camera to full overview."""
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.cx = self.screen_width / 2.0
        self.cy = self.screen_height / 2.0

    def update(self, lander_pos, agl, dt):
        """
        Update camera zoom and focus position based on lander altitude and position.
        """
        # Determine target zoom stage based on AGL
        if agl is None or lander_pos is None:
            self.target_zoom = 1.0
        elif agl <= self.STAGE2_AGL:
            # Stage 3: Close-in touchdown zoom
            self.target_zoom = 3.0
        elif agl <= self.STAGE1_AGL:
            # Stage 2: Intermediate approach zoom
            self.target_zoom = 1.8
        else:
            # Stage 1: Standard overview zoom
            self.target_zoom = 1.0

        # Smooth zoom transition (reduced to 1/2 speed for gentle, gradual transitions)
        zoom_rate = 1.6
        self.zoom += (self.target_zoom - self.zoom) * min(1.0, dt * zoom_rate)

        # Target center in unzoomed screen space (Pygame Y is 0 at top, screen_height at bottom)
        if lander_pos is not None:
            lander_screen_x = lander_pos.x
            lander_screen_y = self.screen_height - lander_pos.y

            # As zoom increases, bias the camera slightly below the lander so the player
            # has maximum visibility of the terrain and landing pad underneath.
            lookahead_y = 50.0 * (self.zoom - 1.0)
            target_cx = lander_screen_x
            target_cy = lander_screen_y + lookahead_y
        else:
            target_cx = self.screen_width / 2.0
            target_cy = self.screen_height / 2.0

        # Viewport boundaries: clamp camera so it never pans beyond world borders
        half_w = (self.screen_width / 2.0) / self.zoom
        half_h = (self.screen_height / 2.0) / self.zoom

        min_x = half_w
        max_x = max(half_w, self.screen_width - half_w)
        min_y = half_h
        max_y = max(half_h, self.screen_height - half_h)

        clamped_cx = max(min_x, min(max_x, target_cx))
        clamped_cy = max(min_y, min(max_y, target_cy))

        # Smooth position tracking
        pan_rate = 4.5
        self.cx += (clamped_cx - self.cx) * min(1.0, dt * pan_rate)
        self.cy += (clamped_cy - self.cy) * min(1.0, dt * pan_rate)

    def to_screen(self, world_point):
        """
        Convert a Pymunk Vec2d or (x, y) tuple in world space to screen coordinates.
        World coordinates: (0,0) bottom-left, y up.
        Screen coordinates: (0,0) top-left, y down.
        """
        if hasattr(world_point, "x"):
            wx, wy = world_point.x, world_point.y
        else:
            wx, wy = world_point[0], world_point[1]

        # Convert to unzoomed screen space
        px = wx
        py = self.screen_height - wy

        # Apply zoom centered around (self.cx, self.cy)
        sx = (px - self.cx) * self.zoom + (self.screen_width / 2.0)
        sy = (py - self.cy) * self.zoom + (self.screen_height / 2.0)

        return int(sx), int(sy)

    def world_to_screen(self, wx, wy):
        return self.to_screen((wx, wy))
