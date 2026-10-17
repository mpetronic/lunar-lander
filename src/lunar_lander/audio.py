import io
import math
import random
import struct
import wave
from pathlib import Path
import pygame


def _pcm_to_sound(samples: list[float], sample_rate: int = 22050) -> pygame.mixer.Sound:
    """Converts a list of normalized float audio samples (-1.0 to 1.0) into a pygame Sound."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray()
        for s in samples:
            val = int(max(-32767, min(32767, s * 32767)))
            raw.extend(struct.pack("<h", val))
        wf.writeframes(raw)
    buf.seek(0)
    return pygame.mixer.Sound(buf)


def _generate_thrust_sound(sample_rate: int = 22050, duration: float = 1.0) -> pygame.mixer.Sound:
    """Generates a seamless looping rocket thruster roar with deep sub-bass and turbulence."""
    n = int(sample_rate * duration)
    samples = [0.0] * n
    lp = 0.0

    # Filtered brown noise + low frequency sub harmonics
    for i in range(n):
        wn = random.uniform(-1.0, 1.0)
        # 1-pole low pass filter
        lp += 0.07 * (wn - lp)
        t = i / sample_rate
        sub1 = 0.30 * math.sin(2.0 * math.pi * 50.0 * t)
        sub2 = 0.20 * math.sin(2.0 * math.pi * 92.0 * t)
        sub3 = 0.12 * math.sin(2.0 * math.pi * 145.0 * t)
        samples[i] = (lp * 0.75 + sub1 + sub2 + sub3) * 0.70

    # Crossfade ends (first and last 2500 samples) for clickless seamless looping
    fade_len = min(2500, n // 4)
    for i in range(fade_len):
        w = i / fade_len
        samples[i] = (1.0 - w) * samples[n - fade_len + i] + w * samples[i]

    return _pcm_to_sound(samples, sample_rate)


def _generate_rcs_sound(sample_rate: int = 22050, duration: float = 0.4) -> pygame.mixer.Sound:
    """Generates a cold-gas RCS attitude control thruster hiss."""
    n = int(sample_rate * duration)
    samples = [0.0] * n
    lp = 0.0

    for i in range(n):
        wn = random.uniform(-1.0, 1.0)
        # Bandpass by subtracting low-pass from mid-pass
        lp += 0.35 * (wn - lp)
        hp = wn - lp
        samples[i] = hp * 0.45

    fade_len = min(800, n // 4)
    for i in range(fade_len):
        w = i / fade_len
        samples[i] = (1.0 - w) * samples[n - fade_len + i] + w * samples[i]

    return _pcm_to_sound(samples, sample_rate)


def _generate_crash_sound(sample_rate: int = 22050, duration: float = 1.6) -> pygame.mixer.Sound:
    """Generates a heavy impact explosion with crunch and decaying rumble."""
    n = int(sample_rate * duration)
    samples = [0.0] * n
    lp = 0.0

    for i in range(n):
        t = i / n
        decay = math.exp(-3.2 * t)
        wn = random.uniform(-1.0, 1.0)
        lp += (0.18 - 0.12 * t) * (wn - lp)
        thump = math.sin(2.0 * math.pi * (65.0 * (1.0 - 0.5 * t)) * (i / sample_rate)) * decay
        samples[i] = (lp * 0.85 + thump * 0.65) * decay

    return _pcm_to_sound(samples, sample_rate)


def _generate_landing_sound(sample_rate: int = 22050, duration: float = 1.2) -> pygame.mixer.Sound:
    """Generates a pleasant 3-note ascending chime (C5 -> E5 -> G5) on touchdown."""
    n = int(sample_rate * duration)
    samples = [0.0] * n
    notes = [523.25, 659.25, 783.99]
    note_len = n // len(notes)

    for idx, freq in enumerate(notes):
        start = idx * note_len
        for i in range(note_len):
            cur = start + i
            if cur >= n:
                break
            t_note = i / note_len
            env = (1.0 - t_note) ** 1.6
            val = (
                math.sin(2.0 * math.pi * freq * (i / sample_rate))
                + 0.25 * math.sin(4.0 * math.pi * freq * (i / sample_rate))
            ) * env
            samples[cur] = val * 0.35

    return _pcm_to_sound(samples, sample_rate)


class SoundManager:
    """Manages audio playback for engine thrusters, RCS attitude control, and events."""

    def __init__(self):
        self.available = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(8)

            self.thrust_channel = pygame.mixer.Channel(0)
            self.rcs_channel = pygame.mixer.Channel(1)
            self.sfx_channel = pygame.mixer.Channel(2)

            audio_dir = Path(__file__).parent / "audio"
            thrust_mp3 = audio_dir / "thrust.mp3"
            if thrust_mp3.exists():
                try:
                    self.thrust_sound = pygame.mixer.Sound(str(thrust_mp3))
                except Exception as e:
                    print(f"[SoundManager] Could not load thrust.mp3 ({e}), using procedural synthesis")
                    self.thrust_sound = _generate_thrust_sound()
            else:
                self.thrust_sound = _generate_thrust_sound()

            explosion_mp3 = audio_dir / "explosion.mp3"
            if explosion_mp3.exists():
                try:
                    self.crash_sound = pygame.mixer.Sound(str(explosion_mp3))
                except Exception as e:
                    print(f"[SoundManager] Could not load explosion.mp3 ({e}), using procedural synthesis")
                    self.crash_sound = _generate_crash_sound()
            else:
                self.crash_sound = _generate_crash_sound()

            self.rcs_sound = _generate_rcs_sound()
            self.landing_sound = _generate_landing_sound()

            self.is_thrust_playing = False
            self.is_rcs_playing = False
            self.available = True
        except Exception as e:
            print(f"[SoundManager] Audio initialization disabled: {e}")

    def update_thrust(self, throttle_pct: float, is_thrusting: bool, fuel_remaining: float):
        """Updates main thruster sound playback and scales volume to throttle."""
        if not self.available:
            return

        should_play = is_thrusting and throttle_pct > 0.0 and fuel_remaining > 0.0
        if should_play:
            # Scaled volume: low audible rumble at idle, full roar at 100%
            vol = max(0.12, min(1.0, 0.15 + 0.85 * (throttle_pct**1.1)))
            self.thrust_channel.set_volume(vol)
            if not self.is_thrust_playing:
                self.thrust_channel.play(self.thrust_sound, loops=-1)
                self.is_thrust_playing = True
        else:
            if self.is_thrust_playing:
                self.thrust_channel.stop()
                self.is_thrust_playing = False

    def update_rcs(self, is_rotating: bool, fuel_remaining: float):
        """Updates RCS attitude thruster hiss."""
        if not self.available:
            return

        should_play = is_rotating and fuel_remaining > 0.0
        if should_play:
            if not self.is_rcs_playing:
                self.rcs_channel.set_volume(0.35)
                self.rcs_channel.play(self.rcs_sound, loops=-1)
                self.is_rcs_playing = True
        else:
            if self.is_rcs_playing:
                self.rcs_channel.stop()
                self.is_rcs_playing = False

    def play_crash(self):
        """Plays explosion sound and silences engines."""
        self.stop_engines()
        if self.available:
            self.sfx_channel.set_volume(0.85)
            self.sfx_channel.play(self.crash_sound)

    def play_landing(self):
        """Plays safe landing chime and silences engines."""
        self.stop_engines()
        if self.available:
            self.sfx_channel.set_volume(0.70)
            self.sfx_channel.play(self.landing_sound)

    def stop_engines(self):
        """Immediately silences thruster and RCS channels."""
        if not self.available:
            return
        if self.is_thrust_playing:
            self.thrust_channel.stop()
            self.is_thrust_playing = False
        if self.is_rcs_playing:
            self.rcs_channel.stop()
            self.is_rcs_playing = False

    def pause(self):
        """Pauses mixer playback."""
        if self.available:
            pygame.mixer.pause()

    def unpause(self):
        """Unpauses mixer playback."""
        if self.available:
            pygame.mixer.unpause()

    def stop_all(self):
        """Stops all active audio."""
        if self.available:
            self.stop_engines()
            self.sfx_channel.stop()
