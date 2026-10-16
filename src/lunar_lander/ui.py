import pygame
from .utils import BLACK, WHITE, RED, GREEN, YELLOW, ORANGE, app_config, GRAVITY_MOON


import math

# Instrument panel color palette
COLOR_BG = (12, 16, 24, 230)
COLOR_BORDER = (45, 62, 85)
COLOR_TEXT_DIM = (130, 150, 175)
COLOR_TEXT_BRIGHT = (240, 245, 252)
COLOR_SAFE = (60, 220, 130)
COLOR_CAUTION = (255, 190, 45)
COLOR_WARN = (255, 75, 75)
COLOR_SKY = (22, 38, 62)
COLOR_GROUND = (52, 45, 40)
COLOR_HORIZON = (245, 245, 255)
COLOR_CRAFT = (255, 215, 0)


class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 16)
        self.font_title = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_lbl = pygame.font.SysFont("Arial", 11)
        self.font_val = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_badge = pygame.font.SysFont("Arial", 10, bold=True)

        self.panel_w = 530
        self.panel_h = 145

        # Pre-create circular mask for the Attitude Indicator (FDAI) ball
        self.ai_r = 27
        self.ai_mask = pygame.Surface((self.ai_r * 2, self.ai_r * 2), pygame.SRCALPHA)
        self.ai_mask.fill((0, 0, 0, 0))
        pygame.draw.circle(
            self.ai_mask, (255, 255, 255, 255), (self.ai_r, self.ai_r), self.ai_r
        )

    def format_met(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        hundredths = int((seconds * 100) % 100)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{hundredths:02d}"

    def _draw_threshold_gauge(
        self,
        surface,
        x,
        y,
        w,
        h,
        current_val,
        safe_limit,
        max_scale,
        is_outside,
        blink_active,
    ):
        """
        Draw horizontal threshold gauge with green (safe) and red (danger) segments,
        and a sliding pip indicator that lightly blinks when outside the green range.
        """
        # Background track
        pygame.draw.rect(surface, (15, 20, 30), (x, y, w, h), border_radius=3)

        # Green segment (safe range)
        safe_ratio = max(0.0, min(1.0, safe_limit / max_scale))
        green_w = int(w * safe_ratio)
        if green_w > 0:
            pygame.draw.rect(
                surface,
                (45, 180, 100),
                (x, y, green_w, h),
                border_top_left_radius=3,
                border_bottom_left_radius=3,
            )

        # Red segment (crash hazard range)
        red_w = w - green_w
        if red_w > 0:
            pygame.draw.rect(
                surface,
                (190, 45, 45),
                (x + green_w, y, red_w, h),
                border_top_right_radius=3,
                border_bottom_right_radius=3,
            )

        # Border
        pygame.draw.rect(
            surface, (55, 75, 100), (x, y, w, h), width=1, border_radius=3
        )

        # White threshold boundary marker
        notch_x = x + green_w
        pygame.draw.line(
            surface, (255, 255, 255), (notch_x, y - 2), (notch_x, y + h + 1), 1
        )

        # Sliding Pip indicator
        pip_ratio = max(0.0, min(1.0, current_val / max_scale))
        pip_cx = x + int(w * pip_ratio)

        # Blinking logic: lightly blink when outside the green range
        show_pip = True
        pip_color = (255, 255, 255)
        if is_outside:
            if not blink_active:
                show_pip = False
            else:
                pip_color = (255, 230, 230)

        if show_pip:
            pip_w = 4
            pip_h = h + 6
            pip_rect = pygame.Rect(pip_cx - pip_w // 2, y - 3, pip_w, pip_h)
            pygame.draw.rect(surface, pip_color, pip_rect, border_radius=2)
            pygame.draw.rect(surface, (20, 20, 20), pip_rect, width=1, border_radius=2)

    def draw(
        self,
        screen,
        velocity,
        fuel,
        max_fuel,
        altitude,
        throttle_pct,
        total_time,
        angle=0.0,
        trim_pct=0.0,
        zoom=1.0,
    ):
        """
        Draw unified avionics instrument panel at top middle of the screen.
        Includes:
        - Attitude indicator (FDAI ball) showing tilt in degrees with envelope markers.
        - Horizontal velocity gauge with red/green segments and sliding blinking pip.
        - Vertical velocity gauge with red/green segments and sliding blinking pip.
        - Integrated fuel gauge with low-fuel warnings.
        - Vertical thrust gauge showing engine throttle level.
        - Integrated altitude and mission elapsed time (MET).
        """
        panel_w, panel_h = self.panel_w, self.panel_h
        # Position at the top middle of the screen
        x = (screen.get_width() - panel_w) // 2
        y = 12

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        # Background chassis
        pygame.draw.rect(
            panel_surf, COLOR_BG, (0, 0, panel_w, panel_h), border_radius=8
        )
        pygame.draw.rect(
            panel_surf, COLOR_BORDER, (0, 0, panel_w, panel_h), width=1, border_radius=8
        )

        # Calculations
        tilt_deg = math.degrees(angle)
        abs_tilt = abs(tilt_deg)
        vel_x = velocity.x
        vel_y = velocity.y
        vv = max(0.0, -vel_y)  # downward descent velocity in m/s
        vh = abs(vel_x)        # horizontal velocity in m/s

        # Apollo LM Doghouse maximum safe horizontal speed
        if vv > 3.05:
            max_vh = 0.0
        elif vv <= 2.13:
            max_vh = 1.22
        else:
            max_vh = max(0.0, (4.0 / 3.0) * (3.05 - vv))

        # Crash landing threshold checks
        tilt_crash = abs_tilt > 12.0
        tilt_caution = not tilt_crash and abs_tilt > 9.0

        v_crash = vel_y < -3.05
        v_caution = not v_crash and vel_y < -2.13

        h_crash = vh > max_vh or vh > 1.22
        h_caution = not h_crash and vh > (max_vh * 0.75)

        # Fuel thresholds
        fuel_pct = max(0.0, min(1.0, fuel / max_fuel)) if max_fuel > 0 else 0.0
        fuel_low = fuel_pct <= 0.20
        fuel_caution = not fuel_low and fuel_pct <= 0.30

        any_crash = tilt_crash or v_crash or h_crash

        # Subtle blink timing (2 Hz, smooth pulse)
        ticks = pygame.time.get_ticks()
        blink_phase = (ticks % 500) / 500.0
        sine_val = 0.5 + 0.5 * math.sin(blink_phase * 2 * math.pi)
        blink_active = (ticks // 250) % 2 == 0

        color_warn_pulse = (
            int(220 + 35 * sine_val),
            int(50 + 40 * sine_val),
            int(50 + 40 * sine_val),
        )

        # --- Header Row ---
        header_title = self.font_title.render("AVIONICS FLIGHT DISPLAY", True, COLOR_TEXT_DIM)
        panel_surf.blit(header_title, (14, 7))

        # Master Status Beacon
        if any_crash:
            status_txt = "▲ CRASH RISK" if blink_active else "▲ CAUTION"
            status_col = color_warn_pulse
        elif fuel_low:
            status_txt = "▲ LOW FUEL"
            status_col = color_warn_pulse if blink_active else COLOR_CAUTION
        elif tilt_caution or v_caution or h_caution or fuel_caution:
            status_txt = "● CAUTION"
            status_col = COLOR_CAUTION
        else:
            status_txt = "● NOMINAL"
            status_col = COLOR_SAFE

        status_render = self.font_badge.render(status_txt, True, status_col)
        panel_surf.blit(
            status_render, (panel_w - status_render.get_width() - 14, 7)
        )

        # Header dividing line
        pygame.draw.line(panel_surf, COLOR_BORDER, (10, 22), (panel_w - 10, 22), 1)

        # =========================================================================
        # 1. ATTITUDE INDICATOR (Left Column: x = 12 to 105)
        # =========================================================================
        ai_cx, ai_cy = 54, 60
        ai_r = self.ai_r

        ai_surf = pygame.Surface((ai_r * 2, ai_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(ai_surf, COLOR_SKY, (ai_r, ai_r), ai_r)

        rot_rad = -angle
        cos_a = math.cos(rot_rad)
        sin_a = math.sin(rot_rad)

        gw = ai_r * 2.5
        gh = ai_r * 2.5
        hx = ai_r
        hy = ai_r

        p1 = (hx - cos_a * gw, hy - sin_a * gw)
        p2 = (hx + cos_a * gw, hy + sin_a * gw)
        p3 = (p2[0] + sin_a * gh, p2[1] - cos_a * gh)
        p4 = (p1[0] + sin_a * gh, p1[1] - cos_a * gh)

        pygame.draw.polygon(ai_surf, COLOR_GROUND, [p1, p2, p3, p4])
        pygame.draw.line(ai_surf, COLOR_HORIZON, p1, p2, 2)

        # Pitch ticks
        for tick_deg in (-10, 10):
            t_rad = rot_rad + math.radians(tick_deg)
            tx = ai_r + math.cos(t_rad) * (ai_r - 4)
            ty = ai_r + math.sin(t_rad) * (ai_r - 4)
            tx2 = ai_r + math.cos(t_rad) * (ai_r - 8)
            ty2 = ai_r + math.sin(t_rad) * (ai_r - 8)
            pygame.draw.line(ai_surf, (180, 200, 220), (tx, ty), (tx2, ty2), 1)

        # Center reticle craft symbol
        pygame.draw.line(
            ai_surf, COLOR_CRAFT, (ai_r - 10, ai_r), (ai_r - 4, ai_r), 2
        )
        pygame.draw.line(
            ai_surf, COLOR_CRAFT, (ai_r + 4, ai_r), (ai_r + 10, ai_r), 2
        )
        pygame.draw.circle(ai_surf, COLOR_CRAFT, (ai_r, ai_r), 2)
        pygame.draw.line(
            ai_surf, COLOR_CRAFT, (ai_r - 5, ai_r), (ai_r - 7, ai_r + 4), 1
        )
        pygame.draw.line(
            ai_surf, COLOR_CRAFT, (ai_r + 5, ai_r), (ai_r + 7, ai_r + 4), 1
        )

        # Apply circular mask
        ai_surf.blit(self.ai_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        panel_surf.blit(ai_surf, (ai_cx - ai_r, ai_cy - ai_r))

        bezel_color = (
            color_warn_pulse
            if tilt_crash
            else COLOR_CAUTION
            if tilt_caution
            else (70, 95, 125)
        )
        pygame.draw.circle(panel_surf, bezel_color, (ai_cx, ai_cy), ai_r + 1, width=2)

        # 0 deg upright top marker
        pygame.draw.polygon(
            panel_surf,
            COLOR_TEXT_BRIGHT,
            [
                (ai_cx, ai_cy - ai_r - 2),
                (ai_cx - 3, ai_cy - ai_r - 5),
                (ai_cx + 3, ai_cy - ai_r - 5),
            ],
        )

        # Safe landing limits (+/- 12 deg)
        for limit_deg in (-12, 12):
            mark_angle = -math.pi / 2 + math.radians(limit_deg)
            mx1 = ai_cx + math.cos(mark_angle) * ai_r
            my1 = ai_cy + math.sin(mark_angle) * ai_r
            mx2 = ai_cx + math.cos(mark_angle) * (ai_r + 3)
            my2 = ai_cy + math.sin(mark_angle) * (ai_r + 3)
            pygame.draw.line(panel_surf, COLOR_WARN, (mx1, my1), (mx2, my2), 2)

        # Digital Tilt Readout
        tilt_dir = "L" if tilt_deg > 0.05 else "R" if tilt_deg < -0.05 else " "
        tilt_str = f"{abs_tilt:4.1f}° {tilt_dir}"
        tilt_color = (
            color_warn_pulse
            if tilt_crash
            else COLOR_CAUTION
            if tilt_caution
            else COLOR_TEXT_BRIGHT
        )

        panel_surf.blit(
            self.font_lbl.render("TILT", True, COLOR_TEXT_DIM), (ai_cx - 38, ai_cy + ai_r + 5)
        )
        panel_surf.blit(
            self.font_val.render(tilt_str, True, tilt_color), (ai_cx - 10, ai_cy + ai_r + 4)
        )

        if tilt_crash:
            if blink_active:
                w_badge = self.font_badge.render("! MAX 12°", True, (255, 255, 255))
                badge_bg = pygame.Rect(ai_cx - 38, ai_cy + ai_r + 20, 76, 13)
                pygame.draw.rect(
                    panel_surf, (200, 30, 30), badge_bg, border_radius=3
                )
                panel_surf.blit(
                    w_badge,
                    (
                        badge_bg.centerx - w_badge.get_width() // 2,
                        badge_bg.centery - w_badge.get_height() // 2,
                    ),
                )
        else:
            panel_surf.blit(
                self.font_badge.render("LIM 12°", True, (80, 105, 130)),
                (ai_cx - 16, ai_cy + ai_r + 20),
            )

        # Divider between AI and center gauges
        pygame.draw.line(panel_surf, COLOR_BORDER, (108, 26), (108, panel_h - 10), 1)

        # =========================================================================
        # 2. V/H VELOCITY HORIZONTAL GAUGES & FUEL (Center Section)
        # =========================================================================
        c_x = 118
        gauge_w = 150
        gauge_h = 7
        gauge_x = c_x + 130

        # --- Horizontal Velocity (H-VEL) ---
        h_y = 28
        panel_surf.blit(self.font_lbl.render("H-VEL", True, COLOR_TEXT_DIM), (c_x, h_y))

        h_arrow = "→" if vel_x > 0.05 else "←" if vel_x < -0.05 else "•"
        h_col = (
            color_warn_pulse
            if h_crash
            else COLOR_CAUTION
            if h_caution
            else COLOR_TEXT_BRIGHT
        )
        panel_surf.blit(
            self.font_val.render(f"{h_arrow} {vh:4.1f} m/s", True, h_col),
            (c_x + 44, h_y - 1),
        )

        # Horizontal threshold gauge (Green safe, Red crash, sliding pip)
        self._draw_threshold_gauge(
            panel_surf,
            gauge_x,
            h_y + 3,
            gauge_w,
            gauge_h,
            current_val=vh,
            safe_limit=max_vh,
            max_scale=2.5,
            is_outside=h_crash,
            blink_active=blink_active,
        )

        if h_crash:
            if blink_active:
                panel_surf.blit(
                    self.font_badge.render("! LIM", True, COLOR_WARN), (gauge_x + gauge_w + 8, h_y + 1)
                )
        else:
            panel_surf.blit(
                self.font_badge.render(f"MAX {max_vh:.1f}", True, (80, 105, 130)),
                (gauge_x + gauge_w + 8, h_y + 1),
            )

        # --- Vertical Velocity (V-VEL) ---
        v_y = 50
        panel_surf.blit(self.font_lbl.render("V-VEL", True, COLOR_TEXT_DIM), (c_x, v_y))

        v_arrow = "↓" if vel_y < -0.05 else "↑" if vel_y > 0.05 else "•"
        v_col = (
            color_warn_pulse
            if v_crash
            else COLOR_CAUTION
            if v_caution
            else COLOR_TEXT_BRIGHT
        )
        panel_surf.blit(
            self.font_val.render(f"{v_arrow} {abs(vel_y):4.1f} m/s", True, v_col),
            (c_x + 44, v_y - 1),
        )

        # Horizontal threshold gauge (Green safe, Red crash, sliding pip)
        self._draw_threshold_gauge(
            panel_surf,
            gauge_x,
            v_y + 3,
            gauge_w,
            gauge_h,
            current_val=vv,
            safe_limit=3.05,
            max_scale=5.0,
            is_outside=v_crash,
            blink_active=blink_active,
        )

        if v_crash:
            if blink_active:
                panel_surf.blit(
                    self.font_badge.render("! SINK", True, COLOR_WARN), (gauge_x + gauge_w + 8, v_y + 1)
                )
        else:
            panel_surf.blit(
                self.font_badge.render("MAX 3.0", True, (80, 105, 130)),
                (gauge_x + gauge_w + 8, v_y + 1),
            )

        # --- Fuel Gauge ---
        f_y = 72
        panel_surf.blit(self.font_lbl.render("FUEL", True, COLOR_TEXT_DIM), (c_x, f_y))

        f_col = (
            color_warn_pulse
            if fuel_low
            else COLOR_CAUTION
            if fuel_caution
            else COLOR_TEXT_BRIGHT
        )
        panel_surf.blit(
            self.font_val.render(f"{int(fuel_pct * 100)}%", True, f_col),
            (c_x + 44, f_y - 1),
        )

        fuel_bar_w = gauge_w
        fuel_bar_h = gauge_h
        pygame.draw.rect(
            panel_surf,
            (15, 20, 30),
            (gauge_x, f_y + 3, fuel_bar_w, fuel_bar_h),
            border_radius=3,
        )
        ffill_w = max(0, int(fuel_bar_w * fuel_pct))
        f_bar_col = (
            color_warn_pulse
            if fuel_low
            else COLOR_CAUTION
            if fuel_caution
            else COLOR_SAFE
        )
        if ffill_w > 0:
            pygame.draw.rect(
                panel_surf,
                f_bar_col,
                (gauge_x, f_y + 3, ffill_w, fuel_bar_h),
                border_radius=3,
            )
        pygame.draw.rect(
            panel_surf,
            color_warn_pulse if fuel_low and blink_active else (55, 75, 100),
            (gauge_x, f_y + 3, fuel_bar_w, fuel_bar_h),
            width=1,
            border_radius=3,
        )

        if fuel_low:
            if blink_active:
                panel_surf.blit(
                    self.font_badge.render("! LOW", True, COLOR_WARN), (gauge_x + gauge_w + 8, f_y + 1)
                )
        else:
            panel_surf.blit(
                self.font_badge.render(f"{int(fuel)}kg", True, (80, 105, 130)),
                (gauge_x + gauge_w + 8, f_y + 1),
            )

        # Bottom context row: ALT & MET
        pygame.draw.line(panel_surf, COLOR_BORDER, (c_x, 93), (440, 93), 1)

        row4_y = 98
        panel_surf.blit(self.font_lbl.render("ALT", True, COLOR_TEXT_DIM), (c_x, row4_y))
        panel_surf.blit(
            self.font_val.render(f"{int(altitude)} m", True, COLOR_TEXT_BRIGHT),
            (c_x + 30, row4_y - 1),
        )

        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        secs = int(total_time % 60)
        met_str = f"T+ {hours:02d}:{minutes:02d}:{secs:02d}"
        panel_surf.blit(
            self.font_badge.render(met_str, True, (120, 145, 175)), (c_x + 115, row4_y + 2)
        )

        # Camera Zoom badge
        zoom_text = f"CAM {zoom:.1f}x"
        zoom_col = (100, 220, 140) if zoom >= 2.5 else (100, 200, 255) if zoom >= 1.4 else (130, 145, 165)
        panel_surf.blit(
            self.font_badge.render(zoom_text, True, zoom_col), (c_x + 205, row4_y + 2)
        )

        # Divider between center gauges and right vertical thrust gauge
        pygame.draw.line(panel_surf, COLOR_BORDER, (448, 26), (448, panel_h - 10), 1)

        # =========================================================================
        # 3. VERTICAL THRUST GAUGE (Right Column)
        # =========================================================================
        vg_x = 472
        vg_w = 20
        vg_h = 75
        vg_y = 38

        thr_lbl = self.font_lbl.render("THRUST", True, COLOR_TEXT_DIM)
        panel_surf.blit(thr_lbl, (vg_x - 11, 24))

        pygame.draw.rect(
            panel_surf, (15, 20, 30), (vg_x, vg_y, vg_w, vg_h), border_radius=3
        )

        t_fill_h = max(0, int(vg_h * throttle_pct))
        if t_fill_h > 0:
            fill_rect = pygame.Rect(
                vg_x, vg_y + vg_h - t_fill_h, vg_w, t_fill_h
            )
            pygame.draw.rect(
                panel_surf,
                (60, 160, 240),
                fill_rect,
                border_bottom_left_radius=3,
                border_bottom_right_radius=3,
            )

        # Segment divider lines
        seg_spacing = 6
        for sy in range(vg_y + seg_spacing, vg_y + vg_h, seg_spacing):
            pygame.draw.line(
                panel_surf, (12, 16, 24), (vg_x, sy), (vg_x + vg_w - 1, sy), 1
            )

        pygame.draw.rect(
            panel_surf, (55, 75, 100), (vg_x, vg_y, vg_w, vg_h), width=1, border_radius=3
        )

        thr_pct_str = f"{int(throttle_pct * 100)}%"
        thr_val_surf = self.font_val.render(thr_pct_str, True, COLOR_TEXT_BRIGHT)
        panel_surf.blit(
            thr_val_surf,
            (vg_x + vg_w // 2 - thr_val_surf.get_width() // 2, vg_y + vg_h + 3),
        )

        # Trim readout below thrust percentage
        if abs(trim_pct) > 0.0005:
            trim_sign = "+" if trim_pct > 0 else ""
            trim_str = f"TRM {trim_sign}{trim_pct * 100:.1f}%"
            trim_col = (100, 200, 255)
        else:
            trim_str = "TRM 0%"
            trim_col = (110, 135, 160)

        trim_surf = self.font_badge.render(trim_str, True, trim_col)
        panel_surf.blit(
            trim_surf,
            (vg_x + vg_w // 2 - trim_surf.get_width() // 2, vg_y + vg_h + 16),
        )

        # Blit instrument panel to top center of screen
        screen.blit(panel_surf, (x, y))


class Menu:
    def __init__(self):
        self.font_title = pygame.font.SysFont("Arial", 50)
        self.font_option = pygame.font.SysFont("Arial", 25)
        self.gravity = app_config.gravity if app_config.gravity else GRAVITY_MOON
        self.difficulty = app_config.difficulty if app_config.difficulty else 1

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font_title.render("L U N A R  L A N D E R", True, WHITE)
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 200))

        start_text = self.font_option.render("Press SPACE to Start", True, GREEN)
        screen.blit(start_text, (screen.get_width() // 2 - start_text.get_width() // 2, 400))

        grav_text = self.font_option.render(f"< Gravity: {self.gravity:.3f} >", True, WHITE)
        screen.blit(grav_text, (screen.get_width() // 2 - grav_text.get_width() // 2, 500))

        diff_text = self.font_option.render(f"^ Difficulty: {self.difficulty} v", True, WHITE)
        screen.blit(diff_text, (screen.get_width() // 2 - diff_text.get_width() // 2, 550))

        editor_text = self.font_option.render("Press E for Terrain Editor", True, YELLOW)
        screen.blit(editor_text, (screen.get_width() // 2 - editor_text.get_width() // 2, 650))

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return "GAME"
                elif event.key == pygame.K_e:
                    return "EDITOR"
                elif event.key == pygame.K_LEFT:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.gravity = max(1, self.gravity - 1)
                    else:
                        self.gravity = max(1, self.gravity - 0.1)
                elif event.key == pygame.K_RIGHT:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.gravity = min(10, self.gravity + 1)
                    else:
                        self.gravity = min(10, self.gravity + 0.1)
                elif event.key == pygame.K_UP:
                    self.difficulty = min(5, self.difficulty + 1)
                elif event.key == pygame.K_DOWN:
                    self.difficulty = max(1, self.difficulty - 1)
        return "MENU"


class InputBox:
    def __init__(self, x, y, w, h, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color("lightskyblue3")
        self.color_active = pygame.Color("dodgerblue2")
        self.color = self.color_inactive
        self.text = text
        self.font = pygame.font.Font(None, 32)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False
        self.done = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.done = True
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = self.font.render(self.text, True, self.color)
        return None

    def update(self):
        # Resize the box if the text is too long.
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width

    def draw(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)


class GameOverMenu:
    def __init__(self):
        self.title_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.reason_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 16)
        self.val_font = pygame.font.SysFont("Arial", 18, bold=True)

    def draw(self, screen, result_text, stats=None):
        is_crash = result_text == "CRASHED!"

        reasons_list = []
        if is_crash and stats:
            if "reasons" in stats and stats["reasons"]:
                reasons_list = stats["reasons"]
            elif "reason" in stats and stats["reason"]:
                reasons_list = stats["reason"].split(" • ")

        # Calculate dynamic panel height
        panel_w = 720
        base_h = 210
        extra_h = len(reasons_list) * 26 if reasons_list else 0
        panel_h = base_h + extra_h

        panel_x = (screen.get_width() - panel_w) // 2
        panel_y = (screen.get_height() - panel_h) // 2

        overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg_col = (20, 10, 15, 235) if is_crash else (10, 22, 16, 235)
        border_col = (245, 75, 75) if is_crash else (75, 215, 120)
        overlay.fill(bg_col)
        pygame.draw.rect(
            overlay, border_col, (0, 0, panel_w, panel_h), width=2, border_radius=10
        )

        # Header Title
        title_str = (
            "MISSION FAILED — LANDER DESTROYED" if is_crash else "TOUCHDOWN CONFIRMED!"
        )
        title_surf = self.title_font.render(title_str, True, border_col)
        overlay.blit(title_surf, (panel_w // 2 - title_surf.get_width() // 2, 18))

        curr_y = 62

        # Crash reasons section
        if is_crash and reasons_list:
            lbl_surf = self.header_font.render("CAUSE OF CRASH:", True, (255, 185, 80))
            overlay.blit(lbl_surf, (35, curr_y))
            curr_y += 26
            for r in reasons_list:
                bullet_surf = self.reason_font.render(f"•  {r}", True, (255, 115, 115))
                overlay.blit(bullet_surf, (45, curr_y))
                curr_y += 24
            curr_y += 6
            pygame.draw.line(overlay, (70, 35, 42), (35, curr_y), (panel_w - 35, curr_y), 1)
            curr_y += 10
        elif is_crash:
            lbl_surf = self.reason_font.render(
                "CAUSE: Impact safety thresholds exceeded", True, (255, 115, 115)
            )
            overlay.blit(lbl_surf, (panel_w // 2 - lbl_surf.get_width() // 2, curr_y))
            curr_y += 32

        # Telemetry stats row
        if stats:
            col_w = (panel_w - 70) // 3
            # Col 1: Vertical Speed
            vv = abs(stats.get("vy", 0.0))
            vv_col = (100, 230, 140) if vv <= 3.05 else (255, 90, 90)
            overlay.blit(
                self.small_font.render("TOUCHDOWN V-VEL", True, (150, 165, 185)), (35, curr_y)
            )
            overlay.blit(self.val_font.render(f"{vv:.1f} m/s", True, vv_col), (35, curr_y + 18))

            # Col 2: Horizontal Speed
            vh = abs(stats.get("vx", 0.0))
            vh_col = (100, 230, 140) if vh <= 1.22 else (255, 90, 90)
            overlay.blit(
                self.small_font.render("TOUCHDOWN H-VEL", True, (150, 165, 185)),
                (35 + col_w, curr_y),
            )
            overlay.blit(
                self.val_font.render(f"{vh:.1f} m/s", True, vh_col),
                (35 + col_w, curr_y + 18),
            )

            # Col 3: Attitude Tilt
            tilt = abs(stats.get("angle", 0.0))
            tilt_col = (100, 230, 140) if tilt <= 12.0 else (255, 90, 90)
            overlay.blit(
                self.small_font.render("IMPACT TILT", True, (150, 165, 185)),
                (35 + col_w * 2, curr_y),
            )
            overlay.blit(
                self.val_font.render(f"{tilt:.1f}°", True, tilt_col),
                (35 + col_w * 2, curr_y + 18),
            )

            curr_y += 48

        # Footer action buttons
        pygame.draw.line(overlay, (50, 60, 75), (35, curr_y), (panel_w - 35, curr_y), 1)
        curr_y += 12

        actions_str = "Press  < SPACE >  to Fly Again    •    < ESC >  for Menu"
        act_surf = self.small_font.render(actions_str, True, (200, 215, 235))
        overlay.blit(act_surf, (panel_w // 2 - act_surf.get_width() // 2, curr_y))

        screen.blit(overlay, (panel_x, panel_y))

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return "RESTART"
                elif event.key == pygame.K_ESCAPE:
                    return "MENU"
        return None
