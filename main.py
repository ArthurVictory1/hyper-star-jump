from array import array
import colorsys
import json
import math
import os
import random
import pygame

# ─────────── Инициализация ───────────
pygame.init()
WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
render_surf = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Hyper Star Jump")
clock = pygame.time.Clock()

# ─────────── Процедурный синтез звуков ───────────
def synth_sound(duration, vol, freq_func, noise=0.0):
    try:
        sr = 22050
        n = int(sr * duration)
        samples = array('h', [0] * n)
        phase = 0.0
        attack_samples = max(1, int(min(0.008, duration * 0.15) * sr))

        for i in range(n):
            t = i / n
            freq = freq_func(t)
            phase += 2.0 * math.pi * freq / sr

            attack = min(1.0, i / attack_samples)
            decay = 1.0 - t
            env = attack * decay

            wave = math.sin(phase)
            if noise > 0:
                wave = (1.0 - noise) * wave + noise * random.uniform(-1.0, 1.0)

            sample = int(vol * 32767 * env * wave)
            samples[i] = max(-32768, min(32767, sample))

        return pygame.mixer.Sound(buffer=samples.tobytes())
    except Exception:
        return None


def make_coin_sound():
    try:
        sr = 22050
        dur1, dur2 = 0.05, 0.16
        n1, n2 = int(sr * dur1), int(sr * dur2)
        samples = array('h', [0] * (n1 + n2))

        phase = 0.0
        for i in range(n1):
            phase += 2.0 * math.pi * 987 / sr
            env = (1.0 - (i / n1) * 0.2)
            val = int(0.18 * 32767 * env * math.sin(phase))
            samples[i] = max(-32768, min(32767, val))

        phase = 0.0
        for i in range(n2):
            phase += 2.0 * math.pi * 1318 / sr
            env = 1.0 - (i / n2)
            val = int(0.18 * 32767 * env * math.sin(phase))
            samples[n1 + i] = max(-32768, min(32767, val))

        return pygame.mixer.Sound(buffer=samples.tobytes())
    except Exception:
        return None


STAR_CHANNEL = None
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1)
    pygame.mixer.set_num_channels(12)
    STAR_CHANNEL = pygame.mixer.Channel(0)

    SND_JUMP       = synth_sound(0.08, 0.20, lambda t: 160 + 260 * (t ** 0.6))
    SND_SPRING     = synth_sound(0.15, 0.24, lambda t: 200 + 450 * (t ** 0.5), 0.05)
    SND_SHOOT      = synth_sound(0.06, 0.18, lambda t: 850 * math.exp(-3.2 * t))
    SND_KILL       = synth_sound(0.13, 0.32, lambda t: max(40, 260 * (1.0 - t * 0.85)), 0.38)
    SND_STAR       = synth_sound(0.28, 0.25, lambda t: 320 + 900 * (t ** 0.8), 0.08)
    SND_BUY        = make_coin_sound()
    SND_BOSS_HIT   = synth_sound(0.12, 0.35, lambda t: 140 * (1.0 - t * 0.5), 0.5)
    SND_BOSS_SHOOT = synth_sound(0.09, 0.22, lambda t: 350 + 150 * math.sin(t * 15), 0.1)
    SND_WIN        = synth_sound(0.45, 0.35, lambda t: 440 + 440 * (t ** 0.5))
    SND_ACHIEVE    = synth_sound(0.35, 0.30, lambda t: 523 + 523 * (t ** 0.4), 0.05)
except Exception:
    SND_JUMP = SND_SPRING = SND_SHOOT = SND_KILL = SND_STAR = SND_BUY = None
    SND_BOSS_HIT = SND_BOSS_SHOOT = SND_WIN = SND_ACHIEVE = None


def play_sound(snd):
    if snd:
        try:
            snd.play()
        except Exception:
            pass


# ─────────── Графические векторные стикеры ───────────
def draw_star_sticker(surface, cx, cy, size, color=(255, 225, 40), outline=(200, 140, 10), rotation=0.0):
    r_out = size * 0.5
    r_in = r_out * 0.42
    pts = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2 + rotation
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    pygame.draw.polygon(surface, color, pts)
    if outline:
        pygame.draw.polygon(surface, outline, pts, max(1, int(size * 0.08)))


def draw_check_sticker(surface, cx, cy, size, color=(120, 255, 120)):
    pts = [
        (cx - size * 0.38, cy - size * 0.02),
        (cx - size * 0.10, cy + size * 0.32),
        (cx + size * 0.38, cy - size * 0.34)
    ]
    pygame.draw.lines(surface, color, False, pts, max(2, int(size * 0.18)))


def draw_badge_sticker(surface, cx, cy, size, is_unlocked):
    r = size // 2
    if is_unlocked:
        pygame.draw.circle(surface, (255, 210, 45), (cx, cy), r)
        pygame.draw.circle(surface, (210, 145, 15), (cx, cy), r, 2)
        draw_star_sticker(surface, cx, cy, int(size * 0.65), color=(255, 255, 255), outline=(190, 130, 10))
    else:
        pygame.draw.circle(surface, (40, 50, 70), (cx, cy), r)
        pygame.draw.circle(surface, (70, 85, 110), (cx, cy), r, 2)
        pygame.draw.circle(surface, (90, 110, 135), (cx, cy), max(2, r // 3))


# ─────────── Адаптивный рендерер текста ───────────
def draw_bounded_text(surface, text, font, color, x, y, max_width=None, align="left", shadow=False):
    surf = font.render(text, True, color)
    if max_width and surf.get_width() > max_width:
        ratio = max_width / surf.get_width()
        new_w = int(max_width)
        new_h = max(1, int(surf.get_height() * ratio))
        surf = pygame.transform.smoothscale(surf, (new_w, new_h))

    w, h = surf.get_size()
    if align == "center":
        draw_x = int(x - w // 2)
    elif align == "right":
        draw_x = int(x - w)
    else:
        draw_x = int(x)
    draw_y = int(y)

    if shadow:
        s_surf = font.render(text, True, (0, 0, 0))
        if max_width and s_surf.get_width() > max_width:
            s_surf = pygame.transform.smoothscale(s_surf, (w, h))
        s_surf.set_alpha(120)
        surface.blit(s_surf, (draw_x + 2, draw_y + 2))

    surface.blit(surf, (draw_x, draw_y))
    return pygame.Rect(draw_x, draw_y, w, h)


# ─────────── Баланс и параметры ───────────
GRAVITY        = 0.48
JUMP_FORCE     = -13.5
SPRING_FORCE   = -21.0
RAINBOW_FORCE  = -68.0
MOVE_SPEED     = 6.5
JETPACK_FRAMES = 160
JETPACK_VY     = -22

PEA_SPEED      = -14
SHOOT_COOLDOWN = 18
SAVE_FILE      = "game_save.json"

MAX_PARTICLES        = 300
SCORE_PER_LEVEL      = 450
JETPACK_EVERY_LEVELS = 10
LEVEL_CAP            = 25

POINTS_PER_ENEMY = 50
BOSS_REWARD      = 2500
MILESTONE_REWARDS = {
    10: 200,
    25: 500,
    50: 1500,
    100: 5000,
}

# ─────────── Палитра и шрифты ───────────
SCORE_COLOR = (30, 40, 55)
PEA_COLOR   = (90, 200, 70)

C_NORMAL    = (130, 95, 55)
C_MOVING    = (50, 135, 225)
C_BREAKING  = (175, 75, 55)
C_SPRING    = (45, 175, 95)
ENEMY_COLOR = (195, 45, 115)

FONT      = pygame.font.SysFont("Arial", 20, bold=True)
BIG_FONT  = pygame.font.SysFont("Arial", 34, bold=True)
MID_FONT  = pygame.font.SysFont("Arial", 24, bold=True)
TINY_FONT = pygame.font.SysFont("Arial", 13, bold=True)

THEME_TITLES = {
    "day": "ДЕНЬ",
    "sunset": "ЗАКАТ",
    "night": "НОЧЬ",
    "dawn": "РАССВЕТ",
    "desert": "ПУСТЫНЯ",
    "mountain": "ГОРЫ",
}

ACHIEVEMENTS_LIST = [
    {"id": "first_star",    "title": "Звёздный странник", "desc": "Поймайте радужную суперзвезду", "reward": 250},
    {"id": "first_jetpack", "title": "К взлёту готов!",   "desc": "Найдите и наденьте джетпак",     "reward": 250},
    {"id": "kill_10",       "title": "Охотник на монстров","desc": "Уничтожьте 10 летающих врагов",  "reward": 500},
    {"id": "reach_10",      "title": "Покоритель облаков", "desc": "Поднимитесь до 10 уровня",      "reward": 400},
    {"id": "reach_25",      "title": "У порога космоса",  "desc": "Доберитесь до арены со Стражем", "reward": 1000},
    {"id": "beat_boss",     "title": "Падение титана",    "desc": "Одолейте Космического Стража",   "reward": 5000},
    {"id": "first_skin",    "title": "Первая обновка",    "desc": "Купите любой скин в гардеробе",   "reward": 300},
    {"id": "score_3000",    "title": "Легенда высоты",    "desc": "Наберите 3000 высоты за раунд",   "reward": 1500},
]

SKINS = {
    "classic": {"name": "Классика",  "price": 0,     "body": (120, 195, 50), "snout": (95, 165, 40),  "acc": "none"},
    "ninja":   {"name": "Ниндзя",    "price": 500,   "body": (45, 50, 60),   "snout": (35, 40, 50),   "acc": "headband"},
    "alien":   {"name": "Пришелец",  "price": 900,   "body": (155, 55, 235), "snout": (70, 220, 90),  "acc": "antenna"},
    "gold":    {"name": "Золотой",   "price": 1500,  "body": (255, 215, 30), "snout": (220, 180, 20), "acc": "wings"},
    "space":   {"name": "Астронавт", "price": 2500,  "body": (230, 238, 248),"snout": (170, 185, 205),"acc": "helmet"},
    "cyber":   {"name": "Кибер",     "price": 3500,  "body": (30, 200, 240), "snout": (20, 160, 200), "acc": "visor"},
    "phantom": {"name": "Призрак",   "price": 4500,  "body": (175, 220, 255),"snout": (130, 180, 225),"acc": "halo"},
    "inferno": {"name": "Инферно",   "price": 6000,  "body": (240, 70, 30),  "snout": (190, 40, 20),  "acc": "horns"},
    "neon":    {"name": "Неон",      "price": 8000,  "body": (35, 25, 55),   "snout": (245, 40, 150), "acc": "shades"},
    "royal":   {"name": "Король",    "price": 10000, "body": (145, 65, 210), "snout": (115, 45, 175), "acc": "crown"},
    "galaxy":  {"name": "Галактика", "price": 15000, "body": (25, 15, 40),   "snout": (170, 80, 240), "acc": "crystals"},
}
SKIN_KEYS = list(SKINS.keys())


# ─────────── Сохранение данных ───────────
def load_game_data():
    data = {
        "highscore": 0,
        "coins": 0,
        "selected_skin": "classic",
        "unlocked_skins": ["classic"],
        "achievements": {},
        "total_kills": 0
    }
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                data.update(loaded)
        except Exception:
            pass

    if "unlocked_skins" not in data or not isinstance(data["unlocked_skins"], list):
        data["unlocked_skins"] = ["classic"]
    if "classic" not in data["unlocked_skins"]:
        data["unlocked_skins"].append("classic")
    if data["selected_skin"] not in SKINS or data["selected_skin"] not in data["unlocked_skins"]:
        data["selected_skin"] = "classic"
    if "achievements" not in data or not isinstance(data["achievements"], dict):
        data["achievements"] = {}
    return data


def save_game_data(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_rainbow_color(offset=0.0, speed=0.0004):
    hue = (pygame.time.get_ticks() * speed + offset) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def add_particle(particles, *args):
    if len(particles) < MAX_PARTICLES:
        particles.append(Particle(*args))


def burst(particles, x, y, color, count=10, speed=4, rmin=3, rmax=6, decay=0.15):
    for _ in range(count):
        add_particle(
            particles, x, y,
            random.uniform(-speed, speed),
            random.uniform(-speed, speed),
            color,
            random.uniform(rmin, rmax),
            decay
        )


def lerp(a, b, t):
    return a + (b - a) * t


# ─────────── Всплывающий баннер достижения ───────────
class AchievementPopup:
    def __init__(self, title, reward):
        self.title = title
        self.reward = reward
        self.duration = 180
        self.timer = self.duration
        self.w, self.h = 330, 54

    def update(self):
        self.timer -= 1
        return self.timer > 0

    def draw(self, surface):
        if self.timer <= 0:
            return
        progress = (self.duration - self.timer) / 20.0 if self.timer > (self.duration - 20) else (self.timer / 20.0 if self.timer < 20 else 1.0)
        progress = max(0.0, min(1.0, progress))
        y = int(lerp(-self.h - 10, 16, progress))

        popup_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.rect(popup_surf, (20, 25, 40, 235), (0, 0, self.w, self.h), border_radius=12)
        pygame.draw.rect(popup_surf, (255, 215, 60, 240), (0, 0, self.w, self.h), width=2, border_radius=12)

        star_rot = (self.duration - self.timer) * 0.08

        t1_rect = draw_bounded_text(popup_surf, "ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО!", TINY_FONT, (255, 215, 80), self.w // 2, 7, max_width=250, align="center")
        draw_star_sticker(popup_surf, t1_rect.left - 12, 14, 13, color=(255, 220, 40), outline=(190, 140, 10), rotation=star_rot)
        draw_star_sticker(popup_surf, t1_rect.right + 12, 14, 13, color=(255, 220, 40), outline=(190, 140, 10), rotation=-star_rot)

        draw_star_sticker(popup_surf, self.w - 14, 38, 13, color=(255, 220, 40), outline=(190, 140, 10))
        rew_rect = draw_bounded_text(popup_surf, f"+{self.reward}", TINY_FONT, (120, 255, 120), self.w - 24, 31, align="right")

        avail_w = rew_rect.left - 24
        draw_bounded_text(popup_surf, self.title, FONT, (255, 255, 255), 14, 26, max_width=avail_w)

        surface.blit(popup_surf, (WIDTH // 2 - self.w // 2, y))


class FloatText:
    def __init__(self, x, y, text, color=(255, 220, 50), size=20, duration=50):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.duration = duration
        self.life = duration
        self.font = pygame.font.SysFont("Arial", size, bold=True)

    def update(self):
        self.y -= 1.1
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * (self.life / self.duration))
        surf = self.font.render(self.text, True, self.color)
        if surf.get_width() > WIDTH - 30:
            ratio = (WIDTH - 30) / surf.get_width()
            surf = pygame.transform.smoothscale(surf, (WIDTH - 30, max(1, int(surf.get_height() * ratio))))
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x - surf.get_width() // 2), int(self.y)))


# ─────────── Декорации фонов ───────────
STARS = [
    (random.randint(0, WIDTH), random.randint(0, HEIGHT),
     random.uniform(0.5, 2.0), random.uniform(0, math.tau))
    for _ in range(80)
]

MOUNTAINS_FAR = [
    (random.randint(-50, WIDTH + 50), random.randint(60, 160))
    for _ in range(10)
]
MOUNTAINS_NEAR = [
    (random.randint(-50, WIDTH + 50), random.randint(100, 200))
    for _ in range(8)
]

CLOUDS = [
    (random.randint(0, WIDTH), random.randint(40, 300), random.uniform(0.4, 1.0))
    for _ in range(5)
]


def theme_for_level(level):
    if level < 5:
        return "day"
    elif level < 10:
        return "sunset"
    elif level < 15:
        return "night"
    elif level < 20:
        return "dawn"
    elif level < 25:
        return "desert"
    else:
        return "mountain"


def draw_gradient(surface, top_color, bottom_color):
    grad = pygame.Surface((1, 2))
    grad.set_at((0, 0), top_color)
    grad.set_at((0, 1), bottom_color)
    surface.blit(pygame.transform.smoothscale(grad, (WIDTH, HEIGHT)), (0, 0))


def draw_stars(surface, t, bright=1.0, drift=False):
    for (sx, sy, size, phase) in STARS:
        cur_y = (sy + t * 90) % HEIGHT if drift else sy
        twinkle = 0.6 + 0.4 * math.sin(t * 3 + phase)
        alpha = min(255, max(0, int(255 * twinkle * bright)))
        r = max(1, int(size * twinkle))
        color = (alpha, alpha, min(255, alpha + 40))
        pygame.draw.circle(surface, color, (int(sx), int(cur_y)), r)


def draw_clouds(surface, offset_x=0.0, color=(255, 255, 255)):
    for (cx, cy, size) in CLOUDS:
        x = cx + offset_x
        for dx, dy, r in [(-20, 0, 18), (0, -8, 22), (20, 0, 18), (0, 6, 20)]:
            pygame.draw.circle(surface, color, (int(x + dx), int(cy + dy)), int(r * size))


def draw_mountains(surface, color, mountains, base_y=HEIGHT):
    points = [(0, base_y)]
    for (mx, mh) in mountains:
        points.append((mx, base_y - mh))
    points.append((WIDTH, base_y))
    pygame.draw.polygon(surface, color, points)


def render_theme_layer(surface, theme, t):
    if theme == "day":
        draw_gradient(surface, (170, 215, 250), (245, 248, 252))
        draw_clouds(surface, offset_x=math.sin(t * 0.3) * 10, color=(255, 255, 255))

    elif theme == "sunset":
        draw_gradient(surface, (255, 140, 80), (255, 220, 150))
        sun_y = HEIGHT - 150 + math.sin(t * 0.5) * 5
        pygame.draw.circle(surface, (255, 240, 180), (WIDTH // 2, int(sun_y)), 60)
        pygame.draw.circle(surface, (255, 200, 100), (WIDTH // 2, int(sun_y)), 45)
        draw_clouds(surface, offset_x=math.sin(t * 0.2) * 15, color=(255, 180, 140))

    elif theme == "night":
        draw_gradient(surface, (10, 15, 40), (30, 40, 80))
        draw_stars(surface, t)
        pygame.draw.circle(surface, (240, 240, 200), (WIDTH - 70, 80), 30)
        pygame.draw.circle(surface, (10, 15, 40), (WIDTH - 60, 75), 28)
        draw_mountains(surface, (15, 20, 45), MOUNTAINS_FAR)
        draw_mountains(surface, (8, 12, 30), MOUNTAINS_NEAR)
        for i in range(7):
            fx = (i * 62 + math.sin(t * 1.2 + i * 2) * 25) % WIDTH
            fy = 200 + (i * 35 + int(math.cos(t * 1.5 + i) * 20)) % 220
            glow_r = int(3 + math.sin(t * 4 + i) * 1.5)
            pygame.draw.circle(surface, (220, 255, 120), (int(fx), int(fy)), max(1, glow_r))

    elif theme == "dawn":
        draw_gradient(surface, (100, 80, 160), (255, 200, 180))
        sun_y = HEIGHT - 100 + math.sin(t * 0.4) * 8
        pygame.draw.circle(surface, (255, 200, 100), (WIDTH // 2, int(sun_y)), 40)
        draw_clouds(surface, offset_x=math.sin(t * 0.25) * 12, color=(255, 200, 200))

    elif theme == "desert":
        draw_gradient(surface, (255, 210, 130), (255, 240, 200))
        for i in range(3):
            y_base = HEIGHT - 80 + i * 30
            points = [(0, HEIGHT)]
            for x in range(0, WIDTH + 20, 20):
                dy = math.sin(x * 0.02 + i + t * 0.2) * 15
                points.append((x, y_base + dy))
            points.append((WIDTH, HEIGHT))
            color = (230, 180, 100 - i * 15)
            pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, (255, 230, 150), (WIDTH - 80, 90), 45)

    elif theme == "mountain":
        draw_gradient(surface, (140, 180, 220), (220, 230, 240))
        draw_mountains(surface, (90, 120, 150), MOUNTAINS_FAR, HEIGHT - 30)
        for (mx, mh) in MOUNTAINS_FAR[:5]:
            pygame.draw.polygon(surface, (245, 250, 255), [
                (mx, HEIGHT - 30 - mh),
                (mx - 12, HEIGHT - 30 - mh + 20),
                (mx + 12, HEIGHT - 30 - mh + 20),
            ])
        draw_mountains(surface, (60, 85, 110), MOUNTAINS_NEAR, HEIGHT)
        draw_clouds(surface, offset_x=math.sin(t * 0.15) * 8, color=(255, 255, 255))

    elif theme == "cosmos":
        draw_gradient(surface, (5, 5, 20), (20, 10, 40))
        nebula = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        t2 = t * 0.3
        for i in range(4):
            cx = WIDTH // 2 + math.sin(t2 + i) * 120
            cy = HEIGHT // 2 + math.cos(t2 + i * 1.7) * 100
            r = 80 + i * 30
            color = [(120, 40, 200), (200, 60, 140), (40, 80, 200), (200, 120, 60)][i]
            alpha = 40 + int(20 * math.sin(t + i))
            pygame.draw.circle(nebula, (*color, alpha), (int(cx), int(cy)), r)
        surface.blit(nebula, (0, 0))
        draw_stars(surface, t, bright=1.5, drift=True)


def draw_hyper_effect(surface, intensity):
    if intensity <= 0:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cx, cy = WIDTH // 2, HEIGHT // 2

    num_lines = int(30 * intensity)
    for _ in range(num_lines):
        angle = random.uniform(0, math.tau)
        length = random.uniform(80, 250) * intensity
        end_x = cx + math.cos(angle) * length
        end_y = cy + math.sin(angle) * length
        alpha = int(120 * intensity)
        pygame.draw.line(overlay, (255, 255, 255, alpha), (cx, cy), (int(end_x), int(end_y)), max(1, int(2 * intensity)))

    num_streaks = int(60 * intensity)
    for _ in range(num_streaks):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        length = random.uniform(30, 90) * intensity
        alpha = int(180 * intensity)
        pygame.draw.line(overlay, (200, 220, 255, alpha), (x, y), (x, y + length), 2)

    surface.blit(overlay, (0, 0))


# ─────────── Частицы ───────────
class Particle:
    def __init__(self, x, y, vx, vy, color, radius, decay=0.15):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.radius = float(radius)
        self.decay = float(decay)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.radius -= self.decay
        return self.radius > 0

    def draw(self, surface):
        if self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))


# ─────────── Платформа ───────────
class Platform:
    def __init__(self, x, y, kind="normal"):
        if kind == "arena":
            self.rect = pygame.Rect(0, y, WIDTH, 24)
        else:
            self.rect = pygame.Rect(x, y, 72, 16)
        self.kind = kind
        self.vx = random.choice([-2.5, 2.5]) if kind == "moving" else 0
        self.fx = float(self.rect.x)

        self.is_broken = False
        self.fall_vy = 0.0
        self.break_offset = 0.0
        self.spring_anim = 0

    def update(self):
        if self.is_broken:
            self.fall_vy += GRAVITY
            self.rect.y += int(self.fall_vy)
            self.break_offset = min(self.break_offset + 1.2, 80)
            return

        if self.kind == "moving":
            self.fx += self.vx
            if self.fx < 0 or self.fx + self.rect.width > WIDTH:
                self.vx *= -1
                self.fx += self.vx * 2
            self.rect.x = int(self.fx)

        if self.spring_anim > 0:
            self.spring_anim -= 1

    def trigger_spring(self):
        self.spring_anim = 16

    def draw(self, surface):
        if self.is_broken:
            half_w = self.rect.width // 2 - 2
            left_rect = pygame.Rect(self.rect.left - int(self.break_offset), self.rect.y + int(self.break_offset), half_w, 14)
            right_rect = pygame.Rect(self.rect.centerx + int(self.break_offset), self.rect.y + int(self.break_offset * 1.3), half_w, 14)
            pygame.draw.rect(surface, C_BREAKING, left_rect, border_radius=4)
            pygame.draw.rect(surface, C_BREAKING, right_rect, border_radius=4)
            return

        if self.kind == "arena":
            col = get_rainbow_color(speed=0.0006)
            pygame.draw.rect(surface, (15, 25, 45), self.rect, border_radius=8)
            pygame.draw.rect(surface, col, self.rect, width=3, border_radius=8)
            for gx in range(10, WIDTH, 30):
                pygame.draw.line(surface, col, (gx, self.rect.top + 3), (gx + 12, self.rect.bottom - 3), 2)
            return

        if self.kind == "rainbow":
            main_color = get_rainbow_color(speed=0.0004)
            t = pygame.time.get_ticks() * 0.005
            pulse = int(3 + math.sin(t) * 2)
            glow_rect = self.rect.inflate(pulse * 2, pulse * 2)
            pygame.draw.rect(surface, main_color, glow_rect, border_radius=8)
            pygame.draw.rect(surface, (255, 255, 255), self.rect, border_radius=6)
            inner_rect = self.rect.inflate(-6, -6)
            pygame.draw.rect(surface, main_color, inner_rect, border_radius=4)
            pygame.draw.circle(surface, (255, 255, 255), (self.rect.centerx, self.rect.centery), 4)
            return

        colors = {"normal": C_NORMAL, "moving": C_MOVING, "breaking": C_BREAKING, "spring": C_SPRING}
        pygame.draw.rect(surface, colors.get(self.kind, C_NORMAL), self.rect, border_radius=6)

        if self.kind == "spring":
            sx = self.rect.centerx - 6
            if self.spring_anim > 8:
                pygame.draw.rect(surface, (255, 215, 0), (sx, self.rect.top - 18, 12, 18), border_radius=3)
                pygame.draw.line(surface, (180, 140, 0), (sx, self.rect.top - 12), (sx + 12, self.rect.top - 12), 2)
            else:
                pygame.draw.rect(surface, (255, 215, 0), (sx, self.rect.top - 8, 12, 8), border_radius=3)
        elif self.kind == "breaking":
            pygame.draw.line(surface, (70, 25, 15), (self.rect.centerx - 3, self.rect.top + 2), (self.rect.centerx + 3, self.rect.bottom - 2), 3)


# ─────────── Босс 25-го уровня ───────────
class BossBullet:
    def __init__(self, x, y, vx=0.0, vy=4.5):
        self.rect = pygame.Rect(int(x - 6), int(y - 6), 12, 12)
        self.x = float(x - 6)
        self.y = float(y - 6)
        self.vx = float(vx)
        self.vy = float(vy)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 60, 120), self.rect.center, 6)
        pygame.draw.circle(surface, (255, 220, 240), self.rect.center, 3)


class Boss:
    def __init__(self):
        self.w, self.h = 92, 66
        self.rect = pygame.Rect(WIDTH // 2 - self.w // 2, -100, self.w, self.h)
        self.hp = 16.0
        self.max_hp = 16.0
        self.target_y = 75
        self.anim_tick = 0.0
        self.shoot_timer = 80
        self.flash_timer = 0
        self.is_alive = True
        self.bullets = []

    def get_phase(self):
        ratio = self.hp / self.max_hp
        if ratio > 0.66:
            return 1
        elif ratio > 0.33:
            return 2
        else:
            return 3

    def update(self, particles):
        phase = self.get_phase()
        speed_mult = 1.0 if phase == 1 else (1.3 if phase == 2 else 1.6)
        self.anim_tick += 0.04 * speed_mult

        if self.rect.y < self.target_y:
            self.rect.y += 2
        else:
            self.rect.centerx = int(WIDTH // 2 + math.sin(self.anim_tick * 1.5) * 115)
            self.rect.y = int(self.target_y + math.cos(self.anim_tick * 2.0) * 12)

        if self.flash_timer > 0:
            self.flash_timer -= 1

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            if phase == 1:
                self.shoot_timer = 80
                self.bullets.append(BossBullet(self.rect.centerx - 22, self.rect.bottom))
                self.bullets.append(BossBullet(self.rect.centerx + 22, self.rect.bottom))
            elif phase == 2:
                self.shoot_timer = 55
                self.bullets.append(BossBullet(self.rect.centerx - 24, self.rect.bottom, vx=-0.8))
                self.bullets.append(BossBullet(self.rect.centerx + 24, self.rect.bottom, vx=0.8))
            else:
                self.shoot_timer = 38
                self.bullets.append(BossBullet(self.rect.centerx - 28, self.rect.bottom, vx=-1.4))
                self.bullets.append(BossBullet(self.rect.centerx, self.rect.bottom, vx=0.0))
                self.bullets.append(BossBullet(self.rect.centerx + 28, self.rect.bottom, vx=1.4))

            play_sound(SND_BOSS_SHOOT)
            burst(particles, self.rect.centerx, self.rect.bottom, (255, 60, 120), count=6, speed=3)

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.rect.y < HEIGHT + 30 and -40 < b.rect.x < WIDTH + 40]

    def hit(self, dmg, particles):
        self.hp -= dmg
        self.flash_timer = 6
        play_sound(SND_BOSS_HIT)
        burst(particles, self.rect.centerx, self.rect.centery, (255, 215, 60), count=16, speed=5)
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False

    def draw(self, surface):
        for b in self.bullets:
            b.draw(surface)

        phase = self.get_phase()
        if self.flash_timer > 0:
            b_color = (255, 255, 255)
            inner_color = (255, 200, 200)
        elif phase == 1:
            b_color = (65, 30, 85)
            inner_color = (180, 50, 130)
        elif phase == 2:
            b_color = (130, 35, 75)
            inner_color = (220, 50, 90)
        else:
            b_color = (215, 35, 45)
            inner_color = (255, 120, 40)

        pygame.draw.ellipse(surface, b_color, self.rect)
        pygame.draw.ellipse(surface, inner_color, self.rect.inflate(-8, -8))

        flap = math.sin(self.anim_tick * 3.0) * 8
        pygame.draw.polygon(surface, (110, 20, 90) if phase < 3 else (160, 20, 30), [
            (self.rect.left + 15, self.rect.top + 10),
            (self.rect.left - 18, self.rect.top - 10 + int(flap)),
            (self.rect.left + 25, self.rect.bottom - 10)
        ])
        pygame.draw.polygon(surface, (110, 20, 90) if phase < 3 else (160, 20, 30), [
            (self.rect.right - 15, self.rect.top + 10),
            (self.rect.right + 18, self.rect.top - 10 + int(flap)),
            (self.rect.right - 25, self.rect.bottom - 10)
        ])

        eye_cx, eye_cy = self.rect.centerx, self.rect.centery
        pygame.draw.circle(surface, (255, 255, 255), (eye_cx, eye_cy), 14)
        pupil_x = eye_cx + int(math.sin(self.anim_tick * 2.0) * 4)
        pupil_col = (255, 0, 0) if phase == 3 else (220, 30, 30)
        pygame.draw.circle(surface, pupil_col, (pupil_x, eye_cy), 7)
        pygame.draw.circle(surface, (0, 0, 0), (pupil_x, eye_cy), 3)

        bar_w = 260
        bar_x = WIDTH // 2 - bar_w // 2
        bar_y = 20
        pygame.draw.rect(surface, (30, 20, 40), (bar_x - 3, bar_y - 3, bar_w + 6, 16), border_radius=6)
        hp_ratio = max(0.0, self.hp / self.max_hp)
        cur_bar_w = int(bar_w * hp_ratio)
        bar_col = (220, 40, 80) if phase < 3 else (255, 60, 40)
        pygame.draw.rect(surface, bar_col, (bar_x, bar_y, cur_bar_w, 10), border_radius=4)

        if abs(self.hp - round(self.hp)) < 0.05:
            hp_str = str(int(round(self.hp)))
        else:
            hp_str = f"{self.hp:.1f}"

        phase_str = " (ФАЗА 2)" if phase == 2 else (" [ЯРОСТЬ!]" if phase == 3 else "")
        draw_bounded_text(surface, f"СТРАЖ: {hp_str} / {int(self.max_hp)}{phase_str}", FONT, (255, 230, 240), WIDTH // 2, bar_y + 13, max_width=bar_w, align="center")


# ─────────── Горошина ───────────
class Pea:
    def __init__(self, x, y):
        self.rect = pygame.Rect(int(x - 4), int(y - 4), 8, 8)
        self.vy = PEA_SPEED

    def update(self):
        self.rect.y += self.vy

    def draw(self, surface):
        pygame.draw.circle(surface, PEA_COLOR, self.rect.center, 5)
        pygame.draw.circle(surface, (255, 255, 255), (self.rect.centerx - 1, self.rect.centery - 1), 2)


# ─────────── Джетпак ───────────
class Jetpack:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 36)

    def draw(self, surface):
        pygame.draw.rect(surface, (90, 95, 105), (self.rect.x + 4, self.rect.y + 8, 20, 26), border_radius=4)
        pygame.draw.rect(surface, (220, 60, 45), (self.rect.x + 7, self.rect.y, 14, 10), border_radius=3)
        pygame.draw.polygon(surface, (255, 190, 50), [
            (self.rect.x + 7, self.rect.bottom),
            (self.rect.x + 21, self.rect.bottom),
            (self.rect.centerx, self.rect.bottom + 8),
        ])


# ─────────── Игрок ───────────
class Player:
    def __init__(self, x, y, skin="classic"):
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(x, y, 38, 38)
        self.vx = 0.0
        self.vy = 0.0
        self.facing_right = True
        self.jetpack_frames = 0
        self.skin = skin

        self.rainbow_timer = 0
        self.max_rainbow_timer = 1100

        self.shoot_cooldown = 0
        self.is_aiming_up = False
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.recoil = 0
        self.flash_timer = 0
        self.slowmo_frames = 0
        self.hyper_intensity = 0.0

    def bounce(self, force, mode="normal"):
        self.vy = force
        if mode == "rainbow":
            if STAR_CHANNEL and SND_STAR:
                STAR_CHANNEL.stop()
                STAR_CHANNEL.play(SND_STAR)
            duration = 1100
            self.scale_x = 0.35
            self.scale_y = 2.0
            self.rainbow_timer = duration
            self.max_rainbow_timer = duration
            self.flash_timer = 5
            self.slowmo_frames = 20
            self.hyper_intensity = 1.0
        elif mode == "spring":
            play_sound(SND_SPRING)
            self.scale_x = 0.65
            self.scale_y = 1.45
        else:
            play_sound(SND_JUMP)
            self.scale_x = 1.35
            self.scale_y = 0.70

    def update(self, dt=1.0):
        if self.slowmo_frames > 0:
            self.slowmo_frames -= 1
            dt = 0.35

        if self.jetpack_frames > 0:
            self.vy = JETPACK_VY * dt
            self.jetpack_frames -= 1
            self.scale_x, self.scale_y = 0.85, 1.2
        else:
            self.vy += GRAVITY * dt

        if self.rainbow_timer > 0:
            self.rainbow_timer -= 1
            if self.rainbow_timer == 0:
                self.max_rainbow_timer = 1100

        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.hyper_intensity > 0:
            self.hyper_intensity = max(0.0, self.hyper_intensity - 0.025)

        self.y += self.vy * dt
        self.x += self.vx * dt
        self.vx *= 0.82 ** dt

        self.scale_x += (1.0 - self.scale_x) * 0.12
        self.scale_y += (1.0 - self.scale_y) * 0.12

        if self.vy < -8:
            self.scale_y = max(self.scale_y, 1.2)
            self.scale_x = min(self.scale_x, 0.85)

        if self.vx > 0.5:
            self.facing_right = True
        elif self.vx < -0.5:
            self.facing_right = False

        if self.x + self.rect.width < 0:
            self.x = float(WIDTH)
        elif self.x > WIDTH:
            self.x = float(-self.rect.width)

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.recoil > 0:
            self.recoil -= 1

    def draw(self, surface):
        t = pygame.time.get_ticks() * 0.001
        cur_w = max(16, int(self.rect.width * self.scale_x))
        cur_h = max(16, int(self.rect.height * self.scale_y))
        draw_x = self.rect.centerx - cur_w // 2
        draw_y = self.rect.bottom - cur_h

        body_rect = pygame.Rect(draw_x, draw_y, cur_w, cur_h)
        skin_cfg = SKINS.get(self.skin, SKINS["classic"])

        if self.rainbow_timer > 0:
            body_color = get_rainbow_color(speed=0.001)
            snout_color = get_rainbow_color(offset=0.2, speed=0.001)
        else:
            body_color = skin_cfg["body"]
            snout_color = skin_cfg["snout"]

        if self.jetpack_frames > 0:
            jp_w = 14
            jp_x = body_rect.left - jp_w + 2 if self.facing_right else body_rect.right - 2
            pygame.draw.rect(surface, (70, 75, 85), (jp_x, draw_y + 6, jp_w, 24), border_radius=4)

        acc = skin_cfg.get("acc", "none")
        if acc == "wings":
            w_span = 14
            wx1 = body_rect.left - w_span if self.facing_right else body_rect.right
            pygame.draw.polygon(surface, (255, 235, 120), [
                (body_rect.centerx, draw_y + int(cur_h * 0.4)),
                (wx1, draw_y + int(cur_h * 0.1)),
                (wx1 + 4, draw_y + int(cur_h * 0.6))
            ])
        elif acc == "crystals":
            for cx_off in (-10, cur_w + 10):
                c_x = body_rect.left + cx_off
                c_y = draw_y + int(cur_h * 0.45) + int(math.sin(t * 6 + cx_off) * 4)
                pygame.draw.polygon(surface, (200, 110, 255), [
                    (c_x, c_y - 7), (c_x + 5, c_y), (c_x, c_y + 7), (c_x - 5, c_y)
                ])
                pygame.draw.polygon(surface, (255, 255, 255), [
                    (c_x, c_y - 7), (c_x + 5, c_y), (c_x, c_y + 7), (c_x - 5, c_y)
                ], 1)

        # Тело персонажа (с полупрозрачностью для Призрака)
        if self.skin == "phantom" and self.rainbow_timer == 0:
            ghost_surf = pygame.Surface((cur_w, cur_h), pygame.SRCALPHA)
            pygame.draw.rect(ghost_surf, (*body_color, 160), (0, 0, cur_w, cur_h), border_radius=10)
            pygame.draw.rect(ghost_surf, (255, 255, 255, 220), (0, 0, cur_w, cur_h), width=2, border_radius=10)
            surface.blit(ghost_surf, body_rect.topleft)
        else:
            pygame.draw.rect(surface, body_color, body_rect, border_radius=10)

        # Аксессуары
        if acc == "headband":
            pygame.draw.rect(surface, (230, 40, 40), (body_rect.left, draw_y + int(cur_h * 0.18), cur_w, 6))
            rib_x = body_rect.left - 6 if self.facing_right else body_rect.right
            pygame.draw.rect(surface, (200, 30, 30), (rib_x, draw_y + int(cur_h * 0.22), 6, 12))
        elif acc == "crown":
            cx, cy = body_rect.centerx, draw_y - 7
            pygame.draw.polygon(surface, (255, 215, 0), [
                (cx - 10, cy + 7), (cx - 12, cy - 2), (cx - 4, cy + 3),
                (cx, cy - 6), (cx + 4, cy + 3), (cx + 12, cy - 2), (cx + 10, cy + 7)
            ])
            pygame.draw.rect(surface, (220, 40, 60), (body_rect.left + 4, draw_y + int(cur_h * 0.65), cur_w - 8, int(cur_h * 0.35)), border_radius=3)
        elif acc == "horns":
            hx1, hx2 = body_rect.left + 5, body_rect.right - 5
            pygame.draw.polygon(surface, (120, 20, 20), [(hx1, draw_y + 2), (hx1 - 4, draw_y - 8), (hx1 + 4, draw_y)])
            pygame.draw.polygon(surface, (120, 20, 20), [(hx2, draw_y + 2), (hx2 + 4, draw_y - 8), (hx2 - 4, draw_y)])
        elif acc == "antenna":
            ax, ay = body_rect.centerx, draw_y
            pygame.draw.line(surface, (130, 130, 150), (ax, ay), (ax, ay - 11), 2)
            pygame.draw.circle(surface, (90, 255, 120), (ax, ay - 13), 4)
            pygame.draw.circle(surface, (255, 255, 255), (ax, ay - 13), 2)
        elif acc == "halo":
            hx, hy = body_rect.centerx, draw_y - 8
            pygame.draw.ellipse(surface, (255, 230, 80), (hx - 15, hy - 4, 30, 8), width=2)
        elif acc == "helmet":
            vx = body_rect.left + 5
            vy = draw_y + int(cur_h * 0.20)
            pygame.draw.rect(surface, (255, 190, 40), (vx, vy, cur_w - 10, int(cur_h * 0.34)), border_radius=6)
            pygame.draw.rect(surface, (255, 240, 160), (vx + 3, vy + 2, 7, 4), border_radius=2)

        # Глаза и очки
        if self.is_aiming_up:
            snout_len = max(6, 15 - self.recoil * 2)
            snout_rect = pygame.Rect(body_rect.centerx - 4, draw_y - snout_len + 3, 8, snout_len)
            pygame.draw.rect(surface, snout_color, snout_rect, border_radius=3)

            eye1_x = body_rect.left + int(cur_w * 0.32)
            eye2_x = body_rect.left + int(cur_w * 0.68)
            eye_y = draw_y + int(cur_h * 0.35)

            for ex in (eye1_x, eye2_x):
                pygame.draw.circle(surface, (255, 255, 255), (ex, eye_y), 5)
                pygame.draw.circle(surface, (20, 20, 30), (ex, eye_y - 2), 2)

            if acc == "visor":
                vw = cur_w - 6
                vx = body_rect.left + 3
                vy = eye_y - 6
                pygame.draw.rect(surface, (15, 25, 40), (vx, vy, vw, 9), border_radius=3)
                pygame.draw.rect(surface, (0, 230, 255), (vx + 2, vy + 2, vw - 4, 5), border_radius=2)
                pygame.draw.line(surface, (255, 255, 255), (vx + 5, vy + 3), (vx + vw - 6, vy + 3), 1)
            elif acc == "shades":
                gw = cur_w - 8
                gy = eye_y - 5
                pygame.draw.rect(surface, (20, 15, 30), (body_rect.left + 4, gy, gw, 9), border_radius=3)
                pygame.draw.rect(surface, (0, 240, 255), (body_rect.left + 6, gy + 1, gw // 2 - 2, 7), border_radius=2)
                pygame.draw.rect(surface, (0, 240, 255), (body_rect.left + gw // 2 + 2, gy + 1, gw // 2 - 2, 7), border_radius=2)
        else:
            snout_len = max(6, 14 - self.recoil * 2)
            snout_y = draw_y + cur_h // 3
            if self.facing_right:
                pygame.draw.rect(surface, snout_color, (body_rect.right - 4, snout_y, snout_len, 8), border_radius=3)
                eye1_x = body_rect.left + int(cur_w * 0.45)
                eye2_x = body_rect.left + int(cur_w * 0.75)
            else:
                pygame.draw.rect(surface, snout_color, (body_rect.left - snout_len + 4, snout_y, snout_len, 8), border_radius=3)
                eye1_x = body_rect.left + int(cur_w * 0.25)
                eye2_x = body_rect.left + int(cur_w * 0.55)

            for ex in (eye1_x, eye2_x):
                pygame.draw.circle(surface, (255, 255, 255), (ex, draw_y + int(cur_h * 0.35)), 5)
                pupil_offset = 2 if self.facing_right else -2
                pygame.draw.circle(surface, (20, 20, 30), (ex + pupil_offset, draw_y + int(cur_h * 0.35)), 2)

            if acc == "visor":
                vw = cur_w - 6
                vx = body_rect.left + 3
                vy = draw_y + int(cur_h * 0.28)
                pygame.draw.rect(surface, (15, 25, 40), (vx, vy, vw, 10), border_radius=3)
                pygame.draw.rect(surface, (0, 230, 255), (vx + 2, vy + 2, vw - 4, 6), border_radius=2)
                glare_x = vx + 5 if self.facing_right else vx + vw - 14
                pygame.draw.line(surface, (255, 255, 255), (glare_x, vy + 3), (glare_x + 9, vy + 3), 2)
                led_x = vx + vw - 4 if self.facing_right else vx + 4
                pygame.draw.circle(surface, (255, 50, 70), (led_x, vy + 5), 1)
            elif acc == "shades":
                glass_y = draw_y + int(cur_h * 0.28)
                gw = cur_w - 6
                gx = body_rect.left + 3
                pygame.draw.rect(surface, (25, 20, 35), (gx, glass_y, gw, 10), border_radius=3)
                pygame.draw.rect(surface, (15, 10, 25), (gx + 2, glass_y + 1, gw // 2 - 2, 8), border_radius=2)
                pygame.draw.rect(surface, (15, 10, 25), (gx + gw // 2 + 1, glass_y + 1, gw // 2 - 2, 8), border_radius=2)
                pygame.draw.line(surface, (0, 240, 255), (gx + 4, glass_y + 7), (gx + 9, glass_y + 2), 2)
                pygame.draw.line(surface, (0, 240, 255), (gx + gw // 2 + 4, glass_y + 7), (gx + gw // 2 + 9, glass_y + 2), 2)

        # Стилизованные лапки для 11 скинов
        lx = draw_x + int(cur_w * 0.3)
        rx = draw_x + int(cur_w * 0.7)
        fy = draw_y + cur_h

        if self.rainbow_timer > 0:
            foot_col = get_rainbow_color(offset=0.4, speed=0.001)
            pygame.draw.circle(surface, foot_col, (lx, fy), 4)
            pygame.draw.circle(surface, foot_col, (rx, fy), 4)
        elif self.skin == "classic":
            pygame.draw.circle(surface, (80, 145, 30), (lx, fy), 4)
            pygame.draw.circle(surface, (80, 145, 30), (rx, fy), 4)
        elif self.skin == "ninja":
            for fx in (lx, rx):
                pygame.draw.rect(surface, (25, 28, 35), (fx - 4, fy - 2, 8, 6), border_radius=2)
                pygame.draw.line(surface, (220, 40, 40), (fx - 3, fy + 1), (fx + 3, fy + 1), 1)
        elif self.skin == "alien":
            for fx in (lx, rx):
                pygame.draw.circle(surface, (60, 200, 80), (fx, fy), 5)
                pygame.draw.circle(surface, (140, 255, 160), (fx, fy - 1), 2)
        elif self.skin == "gold":
            for fx in (lx, rx):
                pygame.draw.circle(surface, (210, 155, 10), (fx, fy), 5)
                pygame.draw.circle(surface, (255, 245, 140), (fx - 1, fy - 1), 2)
        elif self.skin == "space":
            for fx in (lx, rx):
                pygame.draw.rect(surface, (110, 125, 145), (fx - 5, fy - 2, 10, 7), border_radius=3)
                pygame.draw.rect(surface, (50, 60, 75), (fx - 5, fy + 3, 10, 2))
        elif self.skin == "cyber":
            for fx in (lx, rx):
                pygame.draw.rect(surface, (15, 30, 50), (fx - 5, fy - 2, 10, 6), border_radius=2)
                pygame.draw.line(surface, (0, 255, 255), (fx - 4, fy + 2), (fx + 4, fy + 2), 2)
        elif self.skin == "phantom":
            ghost_feet = pygame.Surface((cur_w, 14), pygame.SRCALPHA)
            flx_rel = int(cur_w * 0.3)
            frx_rel = int(cur_w * 0.7)
            pygame.draw.circle(ghost_feet, (175, 220, 255, 150), (flx_rel, 5), 4)
            pygame.draw.circle(ghost_feet, (175, 220, 255, 150), (frx_rel, 5), 4)
            pygame.draw.circle(ghost_feet, (255, 255, 255, 180), (flx_rel, 3), 2)
            pygame.draw.circle(ghost_feet, (255, 255, 255, 180), (frx_rel, 3), 2)
            surface.blit(ghost_feet, (draw_x, fy - 2))
        elif self.skin == "inferno":
            for fx in (lx, rx):
                pygame.draw.polygon(surface, (120, 20, 15), [(fx - 4, fy - 2), (fx + 4, fy - 2), (fx + 3, fy + 4), (fx - 3, fy + 4)])
                pygame.draw.circle(surface, (255, 140, 20), (fx, fy + 3), 2)
        elif self.skin == "neon":
            for fx in (lx, rx):
                pygame.draw.rect(surface, (245, 40, 150), (fx - 5, fy - 2, 10, 6), border_radius=2)
                pygame.draw.line(surface, (255, 220, 240), (fx - 4, fy + 3), (fx + 4, fy + 3), 1)
        elif self.skin == "royal":
            for fx in (lx, rx):
                pygame.draw.rect(surface, (85, 25, 130), (fx - 4, fy - 2, 9, 6), border_radius=2)
                pygame.draw.circle(surface, (255, 215, 0), (fx, fy + 1), 2)
        elif self.skin == "galaxy":
            for fx in (lx, rx):
                pygame.draw.circle(surface, (120, 50, 190), (fx, fy), 5)
                pygame.draw.circle(surface, (255, 255, 255), (fx, fy - 1), 2)
        else:
            pygame.draw.circle(surface, (80, 145, 30), (lx, fy), 4)
            pygame.draw.circle(surface, (80, 145, 30), (rx, fy), 4)


# ─────────── Враг ───────────
class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 30)
        self.vx = random.choice([-1.8, 1.8])
        self.anim_tick = random.uniform(0, 100)
        self.base_y = float(y)

    def update(self):
        self.rect.x += self.vx
        if self.rect.left < 0 or self.rect.right > WIDTH:
            self.vx *= -1
            self.rect.x += self.vx

        self.anim_tick += 0.08
        float_offset = math.sin(self.anim_tick) * 3
        self.rect.y = int(self.base_y + float_offset)

    def draw(self, surface):
        pygame.draw.ellipse(surface, ENEMY_COLOR, self.rect)
        wing_flap = math.sin(self.anim_tick * 2.5) * 6
        pygame.draw.polygon(surface, (150, 30, 90), [
            (self.rect.left + 8, self.rect.top + 4),
            (self.rect.left - 4, self.rect.top - 4 + int(wing_flap)),
            (self.rect.left + 14, self.rect.top),
        ])
        pygame.draw.polygon(surface, (150, 30, 90), [
            (self.rect.right - 8, self.rect.top + 4),
            (self.rect.right + 4, self.rect.top - 4 + int(wing_flap)),
            (self.rect.right - 14, self.rect.top),
        ])
        pygame.draw.circle(surface, (255, 255, 255), (self.rect.x + 12, self.rect.y + 12), 4)
        pygame.draw.circle(surface, (255, 255, 255), (self.rect.x + 28, self.rect.y + 12), 4)
        pygame.draw.circle(surface, (0, 0, 0), (self.rect.x + 12, self.rect.y + 12), 2)
        pygame.draw.circle(surface, (0, 0, 0), (self.rect.x + 28, self.rect.y + 12), 2)


# ─────────── Генерация и сложность ───────────
def pick_kind(level):
    weights = [
        ("normal",   max(30, 75 - level * 5)),
        ("moving",   min(35, 10 + level * 3)),
        ("breaking", min(25, 5 + level * 2)),
        ("spring",   max(5, 12 - level // 2)),
        ("rainbow",  0.35),
    ]
    total = sum(w for _, w in weights)
    r = random.uniform(0, total)
    accum = 0
    for kind, w in weights:
        accum += w
        if r <= accum:
            return kind
    return "normal"


def reset_game(selected_skin="classic"):
    player = Player(WIDTH // 2 - 19, HEIGHT - 150, skin=selected_skin)
    platforms = [Platform(WIDTH // 2 - 36, HEIGHT - 90, "normal")]
    enemies, jetpacks, peas, particles, float_texts = [], [], [], [], []
    y = HEIGHT - 90
    for _ in range(8):
        y -= random.randint(65, 85)
        platforms.append(Platform(random.randint(10, WIDTH - 82), y, "normal"))
    boss = None
    return player, platforms, enemies, jetpacks, peas, particles, float_texts, boss


def draw_touch_button(surface, rect, symbol, is_pressed, color=(255, 255, 255)):
    alpha = 140 if is_pressed else 65
    btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(btn_surf, (20, 30, 45, alpha), (0, 0, rect.width, rect.height), border_radius=rect.width // 2)
    pygame.draw.rect(btn_surf, (*color, min(255, alpha + 60)), (0, 0, rect.width, rect.height), width=3, border_radius=rect.width // 2)

    icon = BIG_FONT.render(symbol, True, (*color, min(255, alpha + 90)))
    btn_surf.blit(icon, (rect.width // 2 - icon.get_width() // 2, rect.height // 2 - icon.get_height() // 2))
    surface.blit(btn_surf, rect.topleft)


# ─────────── Интерактивная анимация туториала ───────────
def draw_tutorial_animation(surface, rect):
    t_cycle = (pygame.time.get_ticks() * 0.001) % 6.0
    demo_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

    pygame.draw.rect(demo_surf, (15, 20, 35, 220), (0, 0, rect.width, rect.height), border_radius=12)
    pygame.draw.rect(demo_surf, (60, 90, 140), (0, 0, rect.width, rect.height), width=2, border_radius=12)

    plat_y = rect.height - 45
    plat_w = 110
    plat_rect = pygame.Rect(rect.width // 2 - plat_w // 2, plat_y, plat_w, 12)
    pygame.draw.rect(demo_surf, (50, 160, 80), plat_rect, border_radius=5)

    dummy = Player(0, 0, skin="classic")
    dummy.rect.width = 32
    dummy.rect.height = 32

    # Фаза 1: 0.0 - 3.0 сек (Движение влево-вправо: сенсор и ПК)
    if t_cycle < 3.0:
        ratio = math.sin(t_cycle * math.pi * 1.0)
        char_x = rect.width // 2 + ratio * 40
        bounce = abs(math.sin(t_cycle * math.pi * 3.0)) * 40
        char_y = plat_y - 32 - bounce
        dummy.rect.x = int(char_x - 16)
        dummy.rect.y = int(char_y)
        dummy.is_aiming_up = False
        dummy.facing_right = ratio >= 0

        finger_x = rect.width // 2 + ratio * 48
        finger_y = rect.height - 18
        pygame.draw.circle(demo_surf, (0, 240, 255, 90), (int(finger_x), int(finger_y)), 16)
        pygame.draw.circle(demo_surf, (255, 255, 255, 220), (int(finger_x), int(finger_y)), 10)

        draw_bounded_text(demo_surf, "ТАЧ ВЛЕВО-ВПРАВО ИЛИ КЛАВИШИ [A] [D]", TINY_FONT, (0, 240, 255), rect.width // 2, 10, max_width=rect.width - 20, align="center")
    # Фаза 2: 3.0 - 6.0 сек (Стрельба вверх: сенсор и ПК)
    else:
        sub_t = t_cycle - 3.0
        char_x = rect.width // 2
        bounce = abs(math.sin(sub_t * math.pi * 3.0)) * 36
        char_y = plat_y - 32 - bounce
        dummy.rect.x = int(char_x - 16)
        dummy.rect.y = int(char_y)
        dummy.is_aiming_up = True

        slide_up = min(18.0, sub_t * 22.0)
        finger_x = rect.width // 2
        finger_y = rect.height - 18 - slide_up
        pygame.draw.circle(demo_surf, (255, 90, 90, 110), (int(finger_x), int(finger_y)), 16)
        pygame.draw.circle(demo_surf, (255, 230, 80, 240), (int(finger_x), int(finger_y)), 10)

        for i in range(3):
            pea_y = (char_y - 10) - ((sub_t * 180 + i * 40) % 90)
            if pea_y > 28:
                pygame.draw.circle(demo_surf, PEA_COLOR, (rect.width // 2, int(pea_y)), 4)
                pygame.draw.circle(demo_surf, (255, 255, 255), (rect.width // 2 - 1, int(pea_y - 1)), 2)

        draw_bounded_text(demo_surf, "СДВИГ ВВЕРХ ИЛИ КЛАВИША [W] [ВВЕРХ]", TINY_FONT, (255, 215, 60), rect.width // 2, 10, max_width=rect.width - 20, align="center")

    dummy.draw(demo_surf)
    surface.blit(demo_surf, rect.topleft)


# ─────────── Главный цикл ───────────
def main():
    game_data = load_game_data()
    high_score = game_data.get("highscore", 0)
    coins = game_data.get("coins", 0)
    selected_skin = game_data.get("selected_skin", "classic")

    player, platforms, enemies, jetpacks, peas, particles, float_texts, boss = reset_game(selected_skin)
    score = 0
    running = True

    game_state = "MENU"
    skin_select_idx = SKIN_KEYS.index(selected_skin) if selected_skin in SKIN_KEYS else 0
    boss_defeated = False

    jetpack_milestones = set()
    milestones_awarded = set()

    active_popup = None
    popup_queue = []

    def trigger_achievement(ach_id):
        nonlocal coins
        if not game_data["achievements"].get(ach_id, False):
            game_data["achievements"][ach_id] = True
            for a in ACHIEVEMENTS_LIST:
                if a["id"] == ach_id:
                    coins += a["reward"]
                    game_data["coins"] = coins
                    popup_queue.append(AchievementPopup(a["title"], a["reward"]))
                    play_sound(SND_ACHIEVE)
                    save_game_data(game_data)
                    break

    bg_from = pygame.Surface((WIDTH, HEIGHT))
    bg_to   = pygame.Surface((WIDTH, HEIGHT))
    current_theme = "day"
    target_theme  = "day"
    transition_prog = 1.0
    transition_speed = 0.025

    # Параметры сенсорного слайдера
    SLIDER_MARGIN   = 16
    SLIDER_CENTER_X = WIDTH // 2
    SLIDER_HALF_W   = WIDTH // 2 - SLIDER_MARGIN
    SLIDER_BASE_Y   = HEIGHT - 46
    SLIDER_MAX_UP   = 40

    def reset_slider():
        return float(SLIDER_CENTER_X), float(SLIDER_BASE_Y)

    knob_x, knob_y = reset_slider()
    screen_shake = 0

    active_touches = {}
    mouse_held = False

    BTN_PAUSE = pygame.Rect(WIDTH - 50, 14, 38, 38)
    pause_btn_surf = pygame.Surface((BTN_PAUSE.width, BTN_PAUSE.height), pygame.SRCALPHA)
    pygame.draw.rect(pause_btn_surf, (20, 30, 45, 120), (0, 0, BTN_PAUSE.width, BTN_PAUSE.height), border_radius=10)
    pygame.draw.rect(pause_btn_surf, (255, 255, 255, 160), (0, 0, BTN_PAUSE.width, BTN_PAUSE.height), width=2, border_radius=10)
    p_txt = FONT.render("||", True, (255, 255, 255))
    pause_btn_surf.blit(p_txt, (BTN_PAUSE.width // 2 - p_txt.get_width() // 2, BTN_PAUSE.height // 2 - p_txt.get_height() // 2 - 1))

    while running:
        clock.tick(60)
        t = pygame.time.get_ticks() * 0.001
        kill_sound_played = False
        tap_points = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_data["coins"] = coins
                game_data["highscore"] = high_score
                save_game_data(game_data)
                running = False

            elif event.type == pygame.FINGERDOWN:
                px, py = int(event.x * WIDTH), int(event.y * HEIGHT)
                active_touches[event.finger_id] = (px, py)
                tap_points.append((px, py))
            elif event.type == pygame.FINGERMOTION:
                px, py = int(event.x * WIDTH), int(event.y * HEIGHT)
                active_touches[event.finger_id] = (px, py)
            elif event.type == pygame.FINGERUP:
                active_touches.pop(event.finger_id, None)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_held = True
                tap_points.append(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                mouse_held = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    if game_state == "PLAY":
                        game_state = "PAUSED"
                    elif game_state == "PAUSED":
                        game_state = "PLAY"
                    elif game_state in ("WARDROBE", "ACHIEVEMENTS", "TUTORIAL"):
                        game_state = "MENU"

        current_pointers = list(active_touches.values())
        if mouse_held and not active_touches:
            current_pointers.append(pygame.mouse.get_pos())

        if active_popup:
            if not active_popup.update():
                active_popup = None
        elif popup_queue:
            active_popup = popup_queue.pop(0)

        # ═══════════════════════════════════════════════════════
        # 1. ГЛАВНОЕ МЕНЮ
        # ═══════════════════════════════════════════════════════
        if game_state == "MENU":
            draw_gradient(screen, (20, 25, 45), (10, 15, 30))
            draw_stars(screen, t, bright=0.9)

            logo1_rect = draw_bounded_text(screen, "HYPER STAR", BIG_FONT, get_rainbow_color(), WIDTH // 2, 70, max_width=290, align="center")
            draw_star_sticker(screen, logo1_rect.left - 18, logo1_rect.centery, 22, color=(255, 225, 50), outline=(190, 140, 10))
            draw_star_sticker(screen, logo1_rect.right + 18, logo1_rect.centery, 22, color=(255, 225, 50), outline=(190, 140, 10))

            draw_bounded_text(screen, "JUMP", MID_FONT, (255, 255, 255), WIDTH // 2, 115, align="center")

            info_str = f"Рекорд: {high_score // 10}   |   Звёзды: {coins}"
            info_rect = draw_bounded_text(screen, info_str, FONT, (255, 220, 100), WIDTH // 2 - 10, 160, max_width=320, align="center")
            draw_star_sticker(screen, info_rect.right + 12, info_rect.centery, 15, color=(255, 220, 50), outline=(190, 140, 10))

            btn_play    = pygame.Rect(WIDTH // 2 - 110, 215, 220, 48)
            btn_skins   = pygame.Rect(WIDTH // 2 - 110, 280, 220, 44)
            btn_achieve = pygame.Rect(WIDTH // 2 - 110, 340, 220, 44)
            btn_tutor   = pygame.Rect(WIDTH // 2 - 110, 400, 220, 44)

            for tp in tap_points:
                if btn_play.collidepoint(tp):
                    player, platforms, enemies, jetpacks, peas, particles, float_texts, boss = reset_game(player.skin)
                    score = 0
                    boss_defeated = False
                    jetpack_milestones = set()
                    milestones_awarded = set()
                    current_theme = "day"
                    target_theme  = "day"
                    transition_prog = 1.0
                    knob_x, knob_y = reset_slider()
                    game_state = "PLAY"
                elif btn_skins.collidepoint(tp):
                    game_state = "WARDROBE"
                elif btn_achieve.collidepoint(tp):
                    game_state = "ACHIEVEMENTS"
                elif btn_tutor.collidepoint(tp):
                    game_state = "TUTORIAL"

            pygame.draw.rect(screen, (50, 180, 90), btn_play, border_radius=24)
            pygame.draw.rect(screen, (255, 255, 255), btn_play, width=2, border_radius=24)
            draw_bounded_text(screen, "ИГРАТЬ", MID_FONT, (255, 255, 255), btn_play.centerx, btn_play.centery - 12, max_width=btn_play.width - 20, align="center")

            for rect, title, col in [(btn_skins, "ГАРДЕРОБ", (55, 75, 125)), 
                                     (btn_achieve, "ДОСТИЖЕНИЯ", (85, 60, 130)), 
                                     (btn_tutor, "КАК ИГРАТЬ", (45, 60, 80))]:
                pygame.draw.rect(screen, col, rect, border_radius=22)
                pygame.draw.rect(screen, (200, 220, 255), rect, width=2, border_radius=22)
                draw_bounded_text(screen, title, FONT, (255, 255, 255), rect.centerx, rect.centery - 10, max_width=rect.width - 20, align="center")

            if active_popup:
                active_popup.draw(screen)

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 2. МЕНЮ ПАУЗЫ
        # ═══════════════════════════════════════════════════════
        if game_state == "PAUSED":
            render_theme_layer(screen, target_theme, t)
            for p in platforms: p.draw(screen)
            for e in enemies: e.draw(screen)
            player.draw(screen)

            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((15, 20, 35, 200))
            screen.blit(overlay, (0, 0))

            draw_bounded_text(screen, "ПАУЗА", BIG_FONT, (255, 255, 255), WIDTH // 2, 140, align="center")

            btn_resume  = pygame.Rect(WIDTH // 2 - 110, 220, 220, 46)
            btn_restart = pygame.Rect(WIDTH // 2 - 110, 285, 220, 46)
            btn_to_menu = pygame.Rect(WIDTH // 2 - 110, 350, 220, 46)

            for tp in tap_points:
                if btn_resume.collidepoint(tp):
                    game_state = "PLAY"
                elif btn_restart.collidepoint(tp):
                    player, platforms, enemies, jetpacks, peas, particles, float_texts, boss = reset_game(player.skin)
                    score = 0
                    boss_defeated = False
                    jetpack_milestones = set()
                    milestones_awarded = set()
                    current_theme = "day"
                    target_theme  = "day"
                    transition_prog = 1.0
                    knob_x, knob_y = reset_slider()
                    game_state = "PLAY"
                elif btn_to_menu.collidepoint(tp):
                    game_data["coins"] = coins
                    game_data["highscore"] = high_score
                    save_game_data(game_data)
                    knob_x, knob_y = reset_slider()
                    game_state = "MENU"

            for rect, title, col in [(btn_resume, "ПРОДОЛЖИТЬ", (40, 160, 60)), 
                                     (btn_restart, "ЗАНОВО", (180, 120, 30)), 
                                     (btn_to_menu, "В МЕНЮ", (60, 75, 120))]:
                pygame.draw.rect(screen, col, rect, border_radius=23)
                pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=23)
                draw_bounded_text(screen, title, FONT, (255, 255, 255), rect.centerx, rect.centery - 10, max_width=rect.width - 20, align="center")

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 3. МЕНЮ ДОСТИЖЕНИЙ
        # ═══════════════════════════════════════════════════════
        if game_state == "ACHIEVEMENTS":
            draw_gradient(screen, (25, 20, 45), (10, 10, 25))
            draw_bounded_text(screen, "ДОСТИЖЕНИЯ", BIG_FONT, (255, 215, 60), WIDTH // 2, 28, max_width=340, align="center")

            unlocked_cnt = sum(1 for a in ACHIEVEMENTS_LIST if game_data["achievements"].get(a["id"], False))
            draw_bounded_text(screen, f"Открыто: {unlocked_cnt} / {len(ACHIEVEMENTS_LIST)}", FONT, (200, 220, 255), WIDTH // 2, 70, max_width=300, align="center")

            card_y = 105
            for a in ACHIEVEMENTS_LIST:
                is_done = game_data["achievements"].get(a["id"], False)
                card_rect = pygame.Rect(18, card_y, WIDTH - 36, 46)

                card_bg = (30, 45, 65, 210) if is_done else (20, 25, 35, 160)
                card_surf = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(card_surf, card_bg, (0, 0, card_rect.width, card_rect.height), border_radius=8)
                pygame.draw.rect(card_surf, (255, 215, 60) if is_done else (70, 80, 100), (0, 0, card_rect.width, card_rect.height), width=1, border_radius=8)

                draw_badge_sticker(card_surf, 22, 23, 24, is_done)

                draw_star_sticker(card_surf, card_rect.width - 12, 23, 11,
                                  color=(255, 220, 40) if is_done else (140, 150, 165),
                                  outline=(190, 140, 10) if is_done else (90, 100, 115))
                rew_rect = draw_bounded_text(card_surf, f"+{a['reward']}", TINY_FONT, (120, 255, 120) if is_done else (140, 150, 165), card_rect.width - 22, 16, align="right")

                avail_w = rew_rect.left - 48
                draw_bounded_text(card_surf, a["title"], FONT, (255, 255, 255) if is_done else (160, 170, 185), 42, 6, max_width=avail_w)
                draw_bounded_text(card_surf, a["desc"], TINY_FONT, (200, 210, 220) if is_done else (110, 120, 135), 42, 26, max_width=avail_w)

                screen.blit(card_surf, card_rect.topleft)
                card_y += 52

            btn_back = pygame.Rect(WIDTH // 2 - 80, HEIGHT - 52, 160, 38)
            pygame.draw.rect(screen, (50, 60, 80), btn_back, border_radius=19)
            draw_bounded_text(screen, "НАЗАД", FONT, (255, 255, 255), btn_back.centerx, btn_back.centery - 10, max_width=120, align="center")

            for tp in tap_points:
                if btn_back.collidepoint(tp):
                    game_state = "MENU"

            if active_popup:
                active_popup.draw(screen)

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 4. ТУТОРИАЛ (БЕЗ ЭМОДЗИ И СЛОМАННЫХ СТРЕЛОК)
        # ═══════════════════════════════════════════════════════
        if game_state == "TUTORIAL":
            draw_gradient(screen, (15, 25, 45), (10, 15, 30))
            draw_bounded_text(screen, "КАК ИГРАТЬ", BIG_FONT, (255, 255, 255), WIDTH // 2, 20, max_width=320, align="center")

            anim_box = pygame.Rect(20, 60, WIDTH - 40, 165)
            draw_tutorial_animation(screen, anim_box)

            tips = [
                ("1. СМАРТФОНЫ (СЕНСОР)", "Движение: ведите пальцем по слайдеру внизу.\nСтрельба: сдвиньте палец на слайдере вверх."),
                ("2. КОМПЬЮТЕР (ПК)", "Движение: клавиши [A] / [D] или стрелки.\nСтрельба: клавиша [W] или [ВВЕРХ]. Пауза: [P] / [ESC]."),
                ("3. БОНУСЫ И БОСС", "Радужная звезда даёт таран врагов и неуязвимость!\nНа 25 уровне откроется арена с Космическим Стражем."),
            ]

            cy = 236
            for title, desc in tips:
                card = pygame.Rect(18, cy, WIDTH - 36, 70)
                pygame.draw.rect(screen, (25, 35, 55), card, border_radius=10)
                pygame.draw.rect(screen, (80, 120, 180), card, width=1, border_radius=10)

                draw_bounded_text(screen, title, FONT, (255, 215, 70), 30, cy + 7, max_width=card.width - 24)
                lines = desc.split("\n")
                draw_bounded_text(screen, lines[0], TINY_FONT, (220, 230, 245), 30, cy + 30, max_width=card.width - 24)
                if len(lines) > 1:
                    draw_bounded_text(screen, lines[1], TINY_FONT, (185, 205, 230), 30, cy + 48, max_width=card.width - 24)

                cy += 78

            btn_ok = pygame.Rect(WIDTH // 2 - 90, HEIGHT - 50, 180, 38)
            pygame.draw.rect(screen, (50, 160, 80), btn_ok, border_radius=19)
            draw_bounded_text(screen, "ПОНЯТНО", FONT, (255, 255, 255), btn_ok.centerx, btn_ok.centery - 10, max_width=140, align="center")

            for tp in tap_points:
                if btn_ok.collidepoint(tp):
                    game_state = "MENU"

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 5. ГАРДЕРОБ
        # ═══════════════════════════════════════════════════════
        if game_state == "WARDROBE":
            preview_key = SKIN_KEYS[skin_select_idx]
            cur_skin_cfg = SKINS[preview_key]

            btn_prev   = pygame.Rect(30, 255, 60, 60)
            btn_next   = pygame.Rect(WIDTH - 90, 255, 60, 60)
            btn_action = pygame.Rect(WIDTH // 2 - 110, 335, 220, 48)
            btn_exit   = pygame.Rect(WIDTH // 2 - 90, 435, 180, 40)

            for tp in tap_points:
                if btn_prev.collidepoint(tp):
                    skin_select_idx = (skin_select_idx - 1) % len(SKIN_KEYS)
                elif btn_next.collidepoint(tp):
                    skin_select_idx = (skin_select_idx + 1) % len(SKIN_KEYS)
                elif btn_exit.collidepoint(tp):
                    game_state = "MENU"
                elif btn_action.collidepoint(tp):
                    if preview_key in game_data["unlocked_skins"]:
                        selected_skin = preview_key
                        player.skin = selected_skin
                        game_data["selected_skin"] = selected_skin
                        save_game_data(game_data)
                        play_sound(SND_BUY)
                    elif coins >= cur_skin_cfg["price"]:
                        coins -= cur_skin_cfg["price"]
                        game_data["coins"] = coins
                        if preview_key not in game_data["unlocked_skins"]:
                            game_data["unlocked_skins"].append(preview_key)
                        selected_skin = preview_key
                        player.skin = selected_skin
                        game_data["selected_skin"] = selected_skin
                        trigger_achievement("first_skin")
                        save_game_data(game_data)
                        play_sound(SND_BUY)

            base_col = cur_skin_cfg["body"]
            top_c = (max(10, base_col[0] // 5), max(15, base_col[1] // 5), max(25, base_col[2] // 5))
            bot_c = (max(5, base_col[0] // 8), max(8, base_col[1] // 8), max(15, base_col[2] // 8))
            draw_gradient(screen, top_c, bot_c)

            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 25, 140))
            screen.blit(overlay, (0, 0))

            draw_bounded_text(screen, "ГАРДЕРОБ", BIG_FONT, (255, 255, 255), WIDTH // 2, 45, max_width=320, align="center")

            bal_str = f"Баланс: {coins} звёзд"
            bal_rect = draw_bounded_text(screen, bal_str, FONT, (255, 215, 50), WIDTH // 2 - 10, 90, max_width=310, align="center")
            draw_star_sticker(screen, bal_rect.right + 12, bal_rect.centery, 15, color=(255, 215, 50), outline=(190, 140, 10))

            dummy = Player(WIDTH // 2 - 25, 175, skin=preview_key)
            dummy.rect.width = 50
            dummy.rect.height = 50
            dummy.scale_y = 1.0 + math.sin(t * 4) * 0.08
            dummy.scale_x = 1.0 - math.sin(t * 4) * 0.05
            dummy.draw(screen)

            is_unlocked = preview_key in game_data["unlocked_skins"]
            is_active = (preview_key == player.skin)
            price = cur_skin_cfg["price"]

            name_color = (120, 255, 120) if is_active else ((255, 200, 80) if not is_unlocked and coins >= price else (255, 255, 255))
            draw_bounded_text(screen, cur_skin_cfg['name'], MID_FONT, name_color, WIDTH // 2, 260, max_width=220, align="center")

            draw_touch_button(screen, btn_prev, "<", False)
            draw_touch_button(screen, btn_next, ">", False)

            price_text = "Куплено" if is_unlocked else (f"Цена: {price} звёзд" if price > 0 else "Бесплатно")
            price_color = (150, 220, 150) if is_unlocked else (255, 215, 50)
            draw_bounded_text(screen, price_text, FONT, price_color, WIDTH // 2, 300, max_width=240, align="center")

            act_color = (40, 160, 60) if is_unlocked else ((200, 140, 30) if coins >= price else (120, 50, 50))
            pygame.draw.rect(screen, act_color, btn_action, border_radius=24)
            pygame.draw.rect(screen, (255, 255, 255), btn_action, width=2, border_radius=24)

            if is_active:
                txt_rect = draw_bounded_text(screen, "НАДЕТО", FONT, (255, 255, 255), btn_action.centerx + 10, btn_action.centery - 10, max_width=150, align="center")
                draw_check_sticker(screen, txt_rect.left - 14, btn_action.centery, 16, color=(255, 255, 255))
            else:
                status_text = "НАДЕТЬ" if is_unlocked else ("КУПИТЬ" if coins >= price else "МАЛО ЗВЁЗД")
                draw_bounded_text(screen, status_text, FONT, (255, 255, 255), btn_action.centerx, btn_action.centery - 10, max_width=btn_action.width - 24, align="center")

            pygame.draw.rect(screen, (50, 60, 75), btn_exit, border_radius=20)
            draw_bounded_text(screen, "ВЫХОД", FONT, (220, 230, 240), btn_exit.centerx, btn_exit.centery - 10, max_width=130, align="center")

            if active_popup:
                active_popup.draw(screen)

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 6. ЭКРАН GAME OVER
        # ═══════════════════════════════════════════════════════
        if game_state == "GAME_OVER":
            btn_restart = pygame.Rect(WIDTH // 2 - 110, 340, 220, 44)
            btn_skins   = pygame.Rect(WIDTH // 2 - 110, 395, 220, 44)
            btn_menu    = pygame.Rect(WIDTH // 2 - 110, 450, 220, 44)

            for tp in tap_points:
                if btn_restart.collidepoint(tp):
                    player, platforms, enemies, jetpacks, peas, particles, float_texts, boss = reset_game(player.skin)
                    score = 0
                    boss_defeated = False
                    jetpack_milestones = set()
                    milestones_awarded = set()
                    current_theme = "day"
                    target_theme  = "day"
                    transition_prog = 1.0
                    knob_x, knob_y = reset_slider()
                    game_state = "PLAY"
                elif btn_skins.collidepoint(tp):
                    game_state = "WARDROBE"
                elif btn_menu.collidepoint(tp):
                    knob_x, knob_y = reset_slider()
                    game_state = "MENU"

            render_theme_layer(screen, target_theme, t)
            for p in platforms: p.draw(screen)
            for e in enemies:   e.draw(screen)
            player.draw(screen)

            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((25, 35, 50, 150))
            screen.blit(overlay, (0, 0))

            draw_bounded_text(screen, "ИГРА ОКОНЧЕНА", BIG_FONT, (255, 255, 255), WIDTH // 2, 130, max_width=340, align="center")
            draw_bounded_text(screen, f"Высота: {score // 10}", FONT, (230, 240, 255), WIDTH // 2, 195, max_width=300, align="center")
            draw_bounded_text(screen, f"Рекорд: {high_score // 10}", FONT, (255, 215, 80), WIDTH // 2, 225, max_width=300, align="center")

            c_rect = draw_bounded_text(screen, f"Звёзды: {coins}", FONT, (255, 220, 60), WIDTH // 2 - 8, 260, max_width=290, align="center")
            draw_star_sticker(screen, c_rect.right + 12, c_rect.centery, 15, color=(255, 220, 60), outline=(190, 140, 10))

            pygame.draw.rect(screen, (50, 160, 80), btn_restart, border_radius=22)
            pygame.draw.rect(screen, (255, 255, 255), btn_restart, width=2, border_radius=22)
            draw_bounded_text(screen, "ИГРАТЬ СНОВА", FONT, (255, 255, 255), btn_restart.centerx, btn_restart.centery - 10, max_width=btn_restart.width - 20, align="center")

            pygame.draw.rect(screen, (60, 75, 120), btn_skins, border_radius=22)
            pygame.draw.rect(screen, (200, 220, 255), btn_skins, width=2, border_radius=22)
            draw_bounded_text(screen, "ГАРДЕРОБ СКИНОВ", FONT, (255, 255, 255), btn_skins.centerx, btn_skins.centery - 10, max_width=btn_skins.width - 20, align="center")

            pygame.draw.rect(screen, (45, 55, 75), btn_menu, border_radius=22)
            draw_bounded_text(screen, "ГЛАВНОЕ МЕНЮ", FONT, (220, 230, 240), btn_menu.centerx, btn_menu.centery - 10, max_width=btn_menu.width - 20, align="center")

            if active_popup:
                active_popup.draw(screen)

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 7. ЭКРАН ПОБЕДЫ НАД БОССОМ
        # ═══════════════════════════════════════════════════════
        if game_state == "VICTORY":
            btn_cont = pygame.Rect(WIDTH // 2 - 110, 335, 220, 46)
            btn_menu = pygame.Rect(WIDTH // 2 - 110, 395, 220, 46)

            for tp in tap_points:
                if btn_cont.collidepoint(tp):
                    knob_x, knob_y = reset_slider()
                    game_state = "PLAY"
                elif btn_menu.collidepoint(tp):
                    knob_x, knob_y = reset_slider()
                    game_state = "MENU"

            render_theme_layer(screen, target_theme, t)
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((20, 15, 45, 190))
            screen.blit(overlay, (0, 0))

            draw_bounded_text(screen, "ПОБЕДА НАД СТРАЖЕМ!", BIG_FONT, (255, 215, 0), WIDTH // 2, 160, max_width=350, align="center")

            v_sub_rect = draw_bounded_text(screen, f"Награда за триумф: +{BOSS_REWARD} звёзд", FONT, (255, 230, 120), WIDTH // 2 - 10, 225, max_width=320, align="center")
            draw_star_sticker(screen, v_sub_rect.right + 12, v_sub_rect.centery, 15, color=(255, 220, 60), outline=(190, 140, 10))

            draw_bounded_text(screen, "Разблокирован скин: КОРОЛЬ!", FONT, (120, 255, 140), WIDTH // 2, 260, max_width=340, align="center")

            pygame.draw.rect(screen, (40, 160, 60), btn_cont, border_radius=23)
            pygame.draw.rect(screen, (255, 255, 255), btn_cont, width=2, border_radius=23)
            draw_bounded_text(screen, "ПРОДОЛЖИТЬ", FONT, (255, 255, 255), btn_cont.centerx, btn_cont.centery - 10, max_width=btn_cont.width - 20, align="center")

            pygame.draw.rect(screen, (60, 75, 140), btn_menu, border_radius=23)
            pygame.draw.rect(screen, (200, 220, 255), btn_menu, width=2, border_radius=23)
            draw_bounded_text(screen, "В ГЛАВНОЕ МЕНЮ", FONT, (255, 255, 255), btn_menu.centerx, btn_menu.centery - 10, max_width=btn_menu.width - 20, align="center")

            if active_popup:
                active_popup.draw(screen)

            pygame.display.flip()
            continue

        # ═══════════════════════════════════════════════════════
        # 8. ОСНОВНОЙ ИГРОВОЙ ПРОЦЕСС ("PLAY")
        # ═══════════════════════════════════════════════════════
        level = score // SCORE_PER_LEVEL
        desired_theme = "cosmos" if player.rainbow_timer > 0 else theme_for_level(level)

        if desired_theme != target_theme:
            if transition_prog < 1.0:
                current_theme = target_theme
            target_theme = desired_theme
            transition_prog = 0.0
            transition_speed = 0.08 if target_theme == "cosmos" else (0.04 if current_theme == "cosmos" else 0.022)
            render_theme_layer(bg_from, current_theme, t)
            render_theme_layer(bg_to, target_theme, t)

        if transition_prog < 1.0:
            transition_prog = min(1.0, transition_prog + transition_speed)
            if transition_prog >= 1.0:
                current_theme = target_theme

        # Активация Арены Босса на 25 уровне
        if level >= 25 and boss is None and not boss_defeated:
            boss = Boss()
            trigger_achievement("reach_25")
            float_texts.append(FloatText(WIDTH // 2, HEIGHT // 3, "БОЕВАЯ АРЕНА АКТИВИРОВАНА!", (255, 60, 120), size=24, duration=100))
            platforms = [
                Platform(0, HEIGHT - 55, kind="arena"),
                Platform(40, HEIGHT - 180, kind="normal"),
                Platform(WIDTH - 112, HEIGHT - 180, kind="normal"),
                Platform(WIDTH // 2 - 36, HEIGHT - 300, kind="spring"),
            ]
            enemies = []
            jetpacks = []
            peas = []
            player.y = float(HEIGHT - 120)
            player.vy = JUMP_FORCE

        if level >= 10:
            trigger_achievement("reach_10")
        if score // 10 >= 3000:
            trigger_achievement("score_3000")

        for milestone_lvl, reward_pts in MILESTONE_REWARDS.items():
            if level >= milestone_lvl and milestone_lvl not in milestones_awarded:
                milestones_awarded.add(milestone_lvl)
                coins += reward_pts
                float_texts.append(FloatText(WIDTH // 2, HEIGHT // 3, f"+{reward_pts} ЗА {milestone_lvl} УРОВЕНЬ!", (255, 230, 80), size=22, duration=90))

        for tp in tap_points:
            if BTN_PAUSE.collidepoint(tp):
                game_state = "PAUSED"
                break

        # Сенсорный слайдер управления
        slider_touches = [p for p in current_pointers if p[1] >= HEIGHT - 130]
        top_touches    = [p for p in current_pointers if p[1] < HEIGHT - 130 and not BTN_PAUSE.collidepoint(p)]

        shoot_from_slider = False

        if slider_touches:
            touch_x, touch_y = slider_touches[0]
            target_knob_x = min(SLIDER_CENTER_X + SLIDER_HALF_W, max(SLIDER_CENTER_X - SLIDER_HALF_W, touch_x))
            knob_x += (target_knob_x - knob_x) * 0.75

            target_knob_y = min(SLIDER_BASE_Y + 8, max(SLIDER_BASE_Y - SLIDER_MAX_UP, touch_y))
            knob_y += (target_knob_y - knob_y) * 0.75

            if (SLIDER_BASE_Y - knob_y) > 14:
                shoot_from_slider = True
        else:
            knob_x += (SLIDER_CENTER_X - knob_x) * 0.35
            knob_y += (SLIDER_BASE_Y - knob_y) * 0.35
            if abs(knob_x - SLIDER_CENTER_X) < 1.0:
                knob_x = float(SLIDER_CENTER_X)
            if abs(knob_y - SLIDER_BASE_Y) < 1.0:
                knob_y = float(SLIDER_BASE_Y)

        move_ratio = (knob_x - SLIDER_CENTER_X) / SLIDER_HALF_W

        keys = pygame.key.get_pressed()
        key_move = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            key_move -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            key_move += 1.0

        if key_move != 0:
            player.vx = key_move * MOVE_SPEED
        elif abs(move_ratio) > 0.03:
            player.vx = move_ratio * MOVE_SPEED

        shoot_held = shoot_from_slider or bool(top_touches) or keys[pygame.K_UP] or keys[pygame.K_w]
        player.is_aiming_up = shoot_held

        if shoot_held and player.shoot_cooldown == 0:
            peas.append(Pea(player.rect.centerx, player.rect.top - 8))
            player.shoot_cooldown = SHOOT_COOLDOWN
            player.recoil = 5
            play_sound(SND_SHOOT)

        is_boss_fight = (boss and boss.is_alive)
        if is_boss_fight:
            if player.vy < -25.0:
                player.vy = -25.0
            if player.rect.top < 35:
                player.rect.top = 35
                player.y = float(player.rect.y)
                player.vy = max(0.0, player.vy)

        prev_bottom = player.rect.bottom
        player.update()

        if player.jetpack_frames > 0:
            jp_x = player.rect.left - 4 if player.facing_right else player.rect.right + 4
            add_particle(particles, jp_x, player.rect.bottom - 6, random.uniform(-1, 1), random.uniform(4, 8), (255, random.randint(120, 200), 20), random.uniform(4, 7))

        if player.rainbow_timer > 0:
            for _ in range(2):
                add_particle(particles, player.rect.centerx + random.uniform(-10, 10), player.rect.bottom + random.uniform(0, 8), random.uniform(-2, 2), random.uniform(1, 4), get_rainbow_color(offset=random.random(), speed=0.001), random.uniform(4, 7), 0.2)

        particles = [pt for pt in particles if pt.update()]
        float_texts = [ft for ft in float_texts if ft.update()]

        for p in platforms: p.update()
        for e in enemies:   e.update()
        for pea in peas:    pea.update()

        if boss and boss.is_alive:
            boss.update(particles)

        # ─── Приземление на платформы ───
        bounced_this_frame = False

        if player.vy > 0 and player.jetpack_frames == 0:
            for p in platforms:
                if (not p.is_broken and
                    prev_bottom <= p.rect.top and
                    player.rect.bottom >= p.rect.top and
                    player.rect.right > p.rect.left and
                    player.rect.left < p.rect.right):

                    player.rect.bottom = p.rect.top
                    player.y = float(player.rect.y)
                    bounced_this_frame = True

                    if p.kind == "rainbow":
                        player.jetpack_frames = 0
                        player.bounce(RAINBOW_FORCE, mode="rainbow")
                        trigger_achievement("first_star")
                        for _ in range(40):
                            add_particle(particles, p.rect.centerx, p.rect.top, random.uniform(-8, 8), random.uniform(-11, -2), get_rainbow_color(offset=random.random(), speed=0.001), random.uniform(4, 9), 0.12)
                    elif p.kind == "breaking":
                        p.is_broken = True
                        player.bounce(JUMP_FORCE)
                        burst(particles, p.rect.centerx, p.rect.centery, C_BREAKING, count=8, speed=3, rmin=3, rmax=5)
                    elif p.kind == "spring":
                        p.trigger_spring()
                        player.bounce(SPRING_FORCE, mode="spring")
                        for _ in range(12):
                            add_particle(particles, p.rect.centerx, p.rect.top, random.uniform(-2, 2), random.uniform(-5, -2), (255, 215, 0), random.uniform(3, 6))
                    else:
                        player.bounce(JUMP_FORCE)
                        for _ in range(5):
                            add_particle(particles, player.rect.centerx, player.rect.bottom, random.uniform(-1.5, 1.5), random.uniform(0.5, 2), C_NORMAL, random.uniform(2, 4))

        # ─── Столкновения пуль (Урон 0.5 HP) ───
        for pea in peas[:]:
            hit = False
            if boss and boss.is_alive and pea.rect.colliderect(boss.rect):
                hit = True
                boss.hit(0.5, particles)
                screen_shake = max(screen_shake, 4)
                float_texts.append(FloatText(boss.rect.centerx, boss.rect.bottom, "-0.5", (255, 80, 80)))
                if not boss.is_alive:
                    coins += BOSS_REWARD
                    if "royal" not in game_data["unlocked_skins"]:
                        game_data["unlocked_skins"].append("royal")
                    game_data["coins"] = coins
                    trigger_achievement("beat_boss")
                    save_game_data(game_data)
                    play_sound(SND_WIN)
                    screen_shake = 16
                    burst(particles, boss.rect.centerx, boss.rect.centery, (255, 215, 0), count=60, speed=8)
                    boss_defeated = True
                    game_state = "VICTORY"

            if not hit:
                for e in enemies[:]:
                    if pea.rect.colliderect(e.rect):
                        enemies.remove(e)
                        hit = True
                        coins += POINTS_PER_ENEMY
                        game_data["total_kills"] = game_data.get("total_kills", 0) + 1
                        if game_data["total_kills"] >= 10:
                            trigger_achievement("kill_10")
                        if not kill_sound_played:
                            play_sound(SND_KILL)
                            kill_sound_played = True
                        float_texts.append(FloatText(e.rect.centerx, e.rect.top, f"+{POINTS_PER_ENEMY}", (255, 220, 60)))
                        burst(particles, e.rect.centerx, e.rect.centery, ENEMY_COLOR, count=12, speed=4, rmin=3, rmax=6)
                        break

            if hit and pea in peas:
                peas.remove(pea)

        # ─── Контакт с монстрами ───
        for e in enemies[:]:
            if player.rect.colliderect(e.rect):
                if player.rainbow_timer > 0:
                    enemies.remove(e)
                    coins += POINTS_PER_ENEMY
                    game_data["total_kills"] = game_data.get("total_kills", 0) + 1
                    if game_data["total_kills"] >= 10:
                        trigger_achievement("kill_10")
                    if not kill_sound_played:
                        play_sound(SND_KILL)
                        kill_sound_played = True
                    float_texts.append(FloatText(e.rect.centerx, e.rect.top, f"+{POINTS_PER_ENEMY}", (255, 220, 60)))
                    burst(particles, e.rect.centerx, e.rect.centery, get_rainbow_color(offset=random.random(), speed=0.001), count=16, speed=5, rmin=3, rmax=6)
                elif player.jetpack_frames > 0:
                    enemies.remove(e)
                    coins += POINTS_PER_ENEMY
                    game_data["total_kills"] = game_data.get("total_kills", 0) + 1
                    if game_data["total_kills"] >= 10:
                        trigger_achievement("kill_10")
                    if not kill_sound_played:
                        play_sound(SND_KILL)
                        kill_sound_played = True
                    float_texts.append(FloatText(e.rect.centerx, e.rect.top, f"+{POINTS_PER_ENEMY}", (255, 220, 60)))
                    burst(particles, e.rect.centerx, e.rect.centery, ENEMY_COLOR, count=16, speed=5, rmin=3, rmax=6)
                elif prev_bottom <= e.rect.top and player.vy > 0:
                    enemies.remove(e)
                    coins += POINTS_PER_ENEMY
                    game_data["total_kills"] = game_data.get("total_kills", 0) + 1
                    if game_data["total_kills"] >= 10:
                        trigger_achievement("kill_10")
                    if not kill_sound_played:
                        play_sound(SND_KILL)
                        kill_sound_played = True
                    float_texts.append(FloatText(e.rect.centerx, e.rect.top, f"+{POINTS_PER_ENEMY}", (255, 220, 60)))
                    player.bounce(JUMP_FORCE)
                    burst(particles, e.rect.centerx, e.rect.centery, ENEMY_COLOR, count=14, speed=5, rmin=3, rmax=6)
                elif not bounced_this_frame:
                    game_state = "GAME_OVER"
                    if score > high_score:
                        high_score = score
                    game_data["highscore"] = high_score
                    game_data["coins"] = coins
                    save_game_data(game_data)

        # ─── Контакт с Боссом (Таран сносит 3 HP) ───
        if boss and boss.is_alive:
            if player.rect.colliderect(boss.rect):
                if player.rainbow_timer > 0:
                    boss.hit(3.0, particles)
                    player.vy = 12.0
                    screen_shake = max(screen_shake, 8)
                    float_texts.append(FloatText(boss.rect.centerx, boss.rect.bottom, "-3 ТАРАН!", (255, 215, 0), size=24))
                    if not boss.is_alive:
                        coins += BOSS_REWARD
                        if "royal" not in game_data["unlocked_skins"]:
                            game_data["unlocked_skins"].append("royal")
                        game_data["coins"] = coins
                        trigger_achievement("beat_boss")
                        save_game_data(game_data)
                        play_sound(SND_WIN)
                        screen_shake = 16
                        burst(particles, boss.rect.centerx, boss.rect.centery, (255, 215, 0), count=60, speed=8)
                        boss_defeated = True
                        game_state = "VICTORY"
                else:
                    game_state = "GAME_OVER"

            for bb in boss.bullets[:]:
                if player.rect.colliderect(bb.rect):
                    if player.rainbow_timer > 0 or player.jetpack_frames > 0:
                        boss.bullets.remove(bb)
                        burst(particles, bb.rect.centerx, bb.rect.centery, (255, 80, 80), count=8)
                    else:
                        game_state = "GAME_OVER"
                        if score > high_score:
                            high_score = score
                        game_data["highscore"] = high_score
                        game_data["coins"] = coins
                        save_game_data(game_data)

        # Подбор джетпака
        for j in jetpacks[:]:
            if player.rect.colliderect(j.rect):
                jetpacks.remove(j)
                trigger_achievement("first_jetpack")
                if player.rainbow_timer > 0:
                    player.vy = min(player.vy - 20, -75.0)
                    player.rainbow_timer = min(player.rainbow_timer + 300, player.max_rainbow_timer)
                    player.scale_y = 2.2
                    player.scale_x = 0.4
                    player.hyper_intensity = 1.0
                    player.flash_timer = 8
                    player.slowmo_frames = max(player.slowmo_frames, 25)
                    burst(particles, j.rect.centerx, j.rect.centery, (255, 160, 30), count=30, speed=7, rmin=4, rmax=8)
                else:
                    player.jetpack_frames = JETPACK_FRAMES

        # Скролл мира
        if player.rect.y < HEIGHT // 3 and not is_boss_fight:
            shift = HEIGHT // 3 - player.rect.y
            player.y = float(HEIGHT // 3)
            player.rect.y = HEIGHT // 3
            for p in platforms: p.rect.y += shift
            for e in enemies:
                e.base_y += shift
                e.rect.y += shift
            for j in jetpacks:     j.rect.y += shift
            for pea in peas:       pea.rect.y += shift
            for pt in particles:   pt.y += shift
            for ft in float_texts: ft.y += shift
            score += shift

        platforms = [p for p in platforms if p.rect.y < HEIGHT + 50 or p.kind == "arena"]
        enemies   = [e for e in enemies   if e.rect.y < HEIGHT + 50]
        jetpacks  = [j for j in jetpacks  if j.rect.y < HEIGHT + 50]
        peas      = [pea for pea in peas  if -60 < pea.rect.y < HEIGHT + 50]

        # Генерация мира
        if not is_boss_fight:
            level_capped = min(LEVEL_CAP, level)
            highest_y = min(p.rect.y for p in platforms)
            while highest_y > -100:
                gap = random.randint(70, 85 + level_capped * 4)
                highest_y -= gap
                x = random.randint(10, WIDTH - 82)
                kind = pick_kind(level_capped)
                new_p = Platform(x, highest_y, kind)
                platforms.append(new_p)

                if kind == "normal" and random.random() < 0.05 + level_capped * 0.02:
                    ex = min(max(10, new_p.rect.x + random.randint(-15, 30)), WIDTH - 45)
                    enemies.append(Enemy(ex, new_p.rect.y + gap // 2))

            milestone = score // (SCORE_PER_LEVEL * JETPACK_EVERY_LEVELS)
            if milestone > 0 and milestone not in jetpack_milestones:
                jetpack_milestones.add(milestone)
                jetpacks.append(Jetpack(random.randint(20, WIDTH - 45), -70))

        # Падение
        if player.rect.top > HEIGHT:
            game_state = "GAME_OVER"
            if score > high_score:
                high_score = score
            game_data["highscore"] = high_score
            game_data["coins"] = coins
            save_game_data(game_data)

        # ─── Отрисовка кадра на буфер render_surf ───
        if transition_prog >= 1.0 or current_theme == target_theme:
            render_theme_layer(render_surf, target_theme, t)
        elif transition_prog <= 0.02:
            render_theme_layer(render_surf, current_theme, t)
        else:
            render_surf.blit(bg_from, (0, 0))
            bg_to.set_alpha(int(255 * transition_prog))
            render_surf.blit(bg_to, (0, 0))
            bg_to.set_alpha(None)

        for p in platforms: p.draw(render_surf)
        for pt in particles: pt.draw(render_surf)
        for e in enemies:   e.draw(render_surf)
        for j in jetpacks:  j.draw(render_surf)
        for pea in peas:    pea.draw(render_surf)
        if boss and boss.is_alive:
            boss.draw(render_surf)
        player.draw(render_surf)
        for ft in float_texts: ft.draw(render_surf)

        if player.hyper_intensity > 0:
            draw_hyper_effect(render_surf, player.hyper_intensity)

        if player.flash_timer > 0:
            alpha = int(200 * player.flash_timer / 8)
            flash = pygame.Surface((WIDTH, HEIGHT))
            flash.fill((255, 255, 255))
            flash.set_alpha(alpha)
            render_surf.blit(flash, (0, 0))

        # Баннер биома
        if 0.05 < transition_prog < 0.95 and target_theme != "cosmos":
            title_text = THEME_TITLES.get(target_theme, "")
            banner_alpha = int(255 * math.sin(transition_prog * math.pi))
            if banner_alpha > 10 and title_text:
                banner_surf = BIG_FONT.render(title_text, True, (255, 255, 255))
                banner_surf.set_alpha(banner_alpha)
                pad_w, pad_h = banner_surf.get_width() + 36, banner_surf.get_height() + 14
                pad = pygame.Surface((pad_w, pad_h), pygame.SRCALPHA)
                pad.fill((20, 25, 35, int(banner_alpha * 0.65)))

                slide = int((1.0 - math.sin(transition_prog * math.pi)) * 10)
                bx = WIDTH // 2 - pad_w // 2
                by = HEIGHT // 4 + slide
                render_surf.blit(pad, (bx, by))
                render_surf.blit(banner_surf, (WIDTH // 2 - banner_surf.get_width() // 2, by + 7))

        # UI
        is_dark = (player.rainbow_timer > 0) or (target_theme in ("night", "cosmos") and transition_prog > 0.5) or (current_theme in ("night", "cosmos") and transition_prog <= 0.5)
        ui_color = (240, 245, 255) if is_dark else SCORE_COLOR

        draw_bounded_text(render_surf, f"ВЫСОТА: {score // 10}", FONT, ui_color, 15, 12, max_width=180, shadow=True)
        draw_bounded_text(render_surf, f"УРОВЕНЬ: {level + 1}", FONT, ui_color, 15, 36, max_width=180, shadow=True)

        prog_in_lvl = (score % SCORE_PER_LEVEL) / SCORE_PER_LEVEL
        bar_w = 120
        pygame.draw.rect(render_surf, (100, 110, 125), (15, 58, bar_w, 4), border_radius=2)
        pygame.draw.rect(render_surf, (90, 210, 110), (15, 58, int(bar_w * prog_in_lvl), 4), border_radius=2)

        draw_bounded_text(render_surf, f"РЕКОРД: {high_score // 10}", FONT, (255, 215, 80) if is_dark else (120, 130, 145), 15, 68, max_width=180, shadow=True)

        star_hud_x = WIDTH - 20
        draw_star_sticker(render_surf, star_hud_x, 62, 14, color=(255, 220, 50), outline=(190, 140, 10))
        draw_bounded_text(render_surf, f"ЗВЁЗДЫ: {coins}", FONT, (255, 215, 50), star_hud_x - 10, 52, max_width=165, align="right", shadow=True)

        render_surf.blit(pause_btn_surf, BTN_PAUSE.topleft)

        if player.rainbow_timer > 0:
            secs = player.rainbow_timer // 60 + 1
            draw_star_sticker(render_surf, 24, 108, 16, color=(255, 230, 60), outline=(190, 140, 10))
            draw_bounded_text(render_surf, f"HYPER STAR: {secs}с", FONT, get_rainbow_color(speed=0.001), 38, 96, max_width=170)
            progress = player.rainbow_timer / player.max_rainbow_timer
            bar_w_star = int(200 * max(0.0, min(1.0, progress)))
            pygame.draw.rect(render_surf, (220, 220, 220), (15, 122, 200, 8), border_radius=4)
            pygame.draw.rect(render_surf, get_rainbow_color(speed=0.001), (15, 122, bar_w_star, 8), border_radius=4)

        elif player.jetpack_frames > 0:
            draw_bounded_text(render_surf, "JETPACK", FONT, (220, 90, 20), 15, 96, max_width=180)
            bar_w_jet = int(200 * (player.jetpack_frames / JETPACK_FRAMES))
            pygame.draw.rect(render_surf, (220, 220, 220), (15, 122, 200, 8), border_radius=4)
            pygame.draw.rect(render_surf, (220, 90, 20), (15, 122, bar_w_jet, 8), border_radius=4)

        # Полупрозрачный слайдер управления внизу экрана
        slider_surf = pygame.Surface((WIDTH, 85), pygame.SRCALPHA)
        track_w = SLIDER_HALF_W * 2
        track_h = 8
        track_rect = pygame.Rect(SLIDER_MARGIN, 45, track_w, track_h)
        pygame.draw.rect(slider_surf, (255, 255, 255, 30), track_rect, border_radius=4)
        pygame.draw.rect(slider_surf, (255, 255, 255, 65), track_rect, width=1, border_radius=4)
        pygame.draw.line(slider_surf, (255, 255, 255, 75), (SLIDER_CENTER_X, 42), (SLIDER_CENTER_X, 55), 2)

        rel_knob_x = int(knob_x)
        rel_knob_y = int(knob_y - (HEIGHT - 85))

        is_firing = (SLIDER_BASE_Y - knob_y) > 14
        knob_glow = (255, 215, 60, 160) if is_firing else (255, 255, 255, 65)
        knob_core = (255, 190, 40, 220) if is_firing else (220, 230, 255, 130)

        pygame.draw.circle(slider_surf, knob_glow, (rel_knob_x, rel_knob_y), 17)
        pygame.draw.circle(slider_surf, knob_core, (rel_knob_x, rel_knob_y), 13)
        pygame.draw.circle(slider_surf, (255, 255, 255, 240), (rel_knob_x, rel_knob_y), 4)

        render_surf.blit(slider_surf, (0, HEIGHT - 85))

        if active_popup:
            active_popup.draw(render_surf)

        # Вывод со Screen Shake
        if screen_shake > 0:
            ox = random.randint(-screen_shake, screen_shake)
            oy = random.randint(-screen_shake, screen_shake)
            screen.fill((10, 10, 20))
            screen.blit(render_surf, (ox, oy))
            screen_shake -= 1
        else:
            screen.blit(render_surf, (0, 0))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
