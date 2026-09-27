#!/usr/bin/env python3
"""Pyrope Plunge — neon gem-diver arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "PYROPE PLUNGE"
HANDLE = "x.com/ElbowOS"
INK = (255, 236, 220)
VOID = (10, 4, 8)
EMBER = (255, 72, 48)
GOLD = (255, 196, 64)
TEAL = (32, 230, 196)
ROSE = (255, 96, 140)
WINE = (92, 16, 36)
SHAFT = (28, 8, 16)
BLADE = (255, 48, 72)
RING = (255, 214, 96)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Ring:
    __slots__ = ("y", "cx", "rad", "gap", "ang", "spin", "scored")

    def __init__(self, y, cx, rad, gap, ang, spin):
        self.y, self.cx, self.rad = y, cx, rad
        self.gap, self.ang, self.spin = gap, ang, spin
        self.scored = False


class Hazard:
    __slots__ = ("y", "x", "r", "ang", "spin")

    def __init__(self, y, x, r, ang, spin):
        self.y, self.x, self.r, self.ang, self.spin = y, x, r, ang, spin


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 64)
        self.font_md = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 32)
        self.reset()

    def reset(self) -> None:
        self.px = W * 0.5
        self.py = 620.0
        self.vx = 0.0
        self.fall = 420.0
        self.depth = 0.0
        self.score = 0
        self.lives = 3
        self.pulse = 0.0
        self.cool = 0.0
        self.over = False
        self.shake = 0.0
        self.sparks: list[Spark] = []
        self.rings: list[Ring] = []
        self.haz: list[Hazard] = []
        self.wall_bits = [(random.uniform(0, H), random.choice((-1, 1)), random.uniform(18, 48))
                          for _ in range(28)]
        y = 900
        for i in range(8):
            self.rings.append(self._mk_ring(y + i * 340))
        y = 1080
        for i in range(6):
            self.haz.append(self._mk_haz(y + i * 430))

    def _mk_ring(self, y: float) -> Ring:
        return Ring(y, random.uniform(280, W - 280), random.uniform(92, 128),
                    random.uniform(0.72, 1.05), random.random() * 6.28,
                    random.choice((-1, 1)) * random.uniform(1.1, 2.4))

    def _mk_haz(self, y: float) -> Hazard:
        return Hazard(y, random.uniform(220, W - 220), random.uniform(34, 52),
                      random.random() * 6.28, random.choice((-1, 1)) * 3.2)

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.random() * 6.283
            s = random.uniform(80, 360)
            self.sparks.append(Spark(x, y, s * math.cos(a), s * math.sin(a),
                                     random.uniform(0.18, 0.5), col, random.randint(3, 8)))

    def autoplay(self) -> None:
        if self.over:
            if self.cool <= 0:
                self.reset()
            return
        target = None
        best = 1e9
        for rg in self.rings:
            dy = rg.y - self.py
            if 40 < dy < 520:
                d = abs(rg.cx - self.px) + dy * 0.15
                if d < best:
                    best, target = d, rg.cx
        threat = None
        for hz in self.haz:
            dy = hz.y - self.py
            if 0 < dy < 280 and abs(hz.x - self.px) < 140:
                threat = hz
                break
        aim = target if target is not None else W * 0.5
        if threat is not None:
            aim = self.px + (90 if threat.x < self.px else -90)
        if aim > self.px + 10:
            self.vx = min(520, self.vx + 48)
        elif aim < self.px - 10:
            self.vx = max(-520, self.vx - 48)
        else:
            self.vx *= 0.82

    def update(self, dt: float) -> None:
        self.pulse += dt
        self.cool = max(0.0, self.cool - dt)
        self.shake = max(0.0, self.shake - dt)
        if self.record:
            self.autoplay()
        if self.over:
            self._tick_fx(dt)
            return
        self.fall = min(760, self.fall + 18 * dt)
        scroll = self.fall * dt
        self.depth += scroll
        self.px += self.vx * dt
        self.vx *= 0.92
        self.px = max(90, min(W - 90, self.px))
        for rg in self.rings:
            rg.y -= scroll
            rg.ang += rg.spin * dt
            if rg.y < -80:
                rg.y += 8 * 340
                rg.cx = random.uniform(280, W - 280)
                rg.scored = False
            if (not rg.scored) and abs(rg.y - self.py) < 22:
                if abs(self.px - rg.cx) < rg.rad * 0.72:
                    rg.scored = True
                    self.score += 40
                    self.burst(self.px, self.py, GOLD, 16)
                else:
                    self._hit()
        for hz in self.haz:
            hz.y -= scroll
            hz.ang += hz.spin * dt
            if hz.y < -80:
                hz.y += 6 * 430
                hz.x = random.uniform(220, W - 220)
            if abs(hz.y - self.py) < hz.r + 18 and abs(hz.x - self.px) < hz.r + 18:
                self._hit()
        self.score += int(scroll * 0.08)
        self._tick_fx(dt)

    def _hit(self) -> None:
        if self.cool > 0:
            return
        self.lives -= 1
        self.shake = 0.35
        self.cool = 0.55
        self.burst(self.px, self.py, BLADE, 22)
        if self.lives <= 0:
            self.over = True
            self.cool = 1.5

    def _tick_fx(self, dt: float) -> None:
        alive = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sp.vy += 180 * dt
            alive.append(sp)
        self.sparks = alive

    def handle(self, ev) -> None:
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key == pygame.K_r:
            self.reset()

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        ox = int(math.sin(self.pulse * 42) * 14 * self.shake)
        pygame.draw.rect(s, SHAFT, (0, 0, 86, H))
        pygame.draw.rect(s, SHAFT, (W - 86, 0, 86, H))
        pygame.draw.rect(s, WINE, (78, 0, 10, H))
        pygame.draw.rect(s, WINE, (W - 88, 0, 10, H))
        off = (self.depth * 0.45) % 70
        for i in range(32):
            y = int(i * 70 - off)
            pygame.draw.line(s, (48, 10, 18), (0, y), (86, y + 28), 3)
            pygame.draw.line(s, (48, 10, 18), (W, y), (W - 86, y + 28), 3)
        for i, (by, side, br) in enumerate(self.wall_bits):
            yy = (by + self.depth * 0.7) % (H + 40) - 20
            xx = 40 if side < 0 else W - 40
            pygame.draw.circle(s, (70, 16, 24), (xx + ox, int(yy)), int(br * 0.15))
        for rg in self.rings:
            if rg.y < -60 or rg.y > H + 60:
                continue
            cx, cy = int(rg.cx) + ox, int(rg.y)
            pts_o, pts_i = [], []
            for k in range(18):
                a = rg.ang + k * (6.283 / 18)
                pts_o.append((cx + int(math.cos(a) * rg.rad), cy + int(math.sin(a) * rg.rad * 0.38)))
                pts_i.append((cx + int(math.cos(a) * rg.rad * 0.62), cy + int(math.sin(a) * rg.rad * 0.24)))
            col = GOLD if not rg.scored else TEAL
            pygame.draw.polygon(s, col, pts_o, 5)
            pygame.draw.polygon(s, ROSE, pts_i, 2)
        for hz in self.haz:
            if hz.y < -50 or hz.y > H + 50:
                continue
            hx, hy = int(hz.x) + ox, int(hz.y)
            pygame.draw.circle(s, BLADE, (hx, hy), int(hz.r * 0.42))
            for arm in range(3):
                a = hz.ang + arm * 2.094
                x2 = hx + int(math.cos(a) * hz.r)
                y2 = hy + int(math.sin(a) * hz.r)
                pygame.draw.line(s, EMBER, (hx, hy), (x2, y2), 7)
                pygame.draw.circle(s, GOLD, (x2, y2), 6)
        px, py = int(self.px) + ox, int(self.py)
        glow = 22 + int(6 * math.sin(self.pulse * 8))
        pygame.draw.circle(s, (80, 12, 20), (px, py + 6), glow + 10)
        pygame.draw.circle(s, EMBER, (px, py), 28)
        pygame.draw.circle(s, GOLD, (px - 4, py - 6), 14)
        pygame.draw.circle(s, INK, (px - 8, py - 4), 4)
        pygame.draw.circle(s, INK, (px + 6, py - 4), 4)
        for t in range(6):
            pygame.draw.circle(s, ROSE, (px, py - 34 - t * 16), max(2, 10 - t))
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x) + ox, int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        title = self.font_lg.render(TITLE, True, GOLD)
        s.blit(title, title.get_rect(center=(W // 2, 78)))
        handle = self.font_sm.render(HANDLE, True, ROSE)
        s.blit(handle, handle.get_rect(center=(W // 2, 128)))
        meta = self.font_md.render(
            f"SCORE  {self.score}    LIVES  {max(0, self.lives)}    {int(self.depth)}m", True, TEAL
        )
        s.blit(meta, meta.get_rect(center=(W // 2, 188)))
        hint = self.font_sm.render("A / D  steer    R reset", True, GOLD)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 48)))
        if self.over:
            over = self.font_md.render("GEODE SHATTERED", True, BLADE)
            s.blit(over, over.get_rect(center=(W // 2, 240)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            keys = pygame.key.get_pressed()
            if not self.over:
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    self.vx = max(-560, self.vx - 70)
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    self.vx = min(560, self.vx + 70)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/PYROPE_PLUNGE_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
