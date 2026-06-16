import pygame
import sys
import random
import math
import json
import os
import struct

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ─── VIRTUAL CANVAS ──────────────────────────────────
VIRTUAL_W, VIRTUAL_H = 1100, 750
FPS = 60
virtual_surface = pygame.Surface((VIRTUAL_W, VIRTUAL_H))

fullscreen = False

def set_display(fs):
    global screen, SCREEN_WIDTH, SCREEN_HEIGHT, fullscreen
    fullscreen = fs
    if fs:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
    else:
        screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H))
        SCREEN_WIDTH, SCREEN_HEIGHT = VIRTUAL_W, VIRTUAL_H

def present(virtual_surf, real_screen):
    rw, rh = real_screen.get_size()
    scale = min(rw / VIRTUAL_W, rh / VIRTUAL_H)
    new_w, new_h = int(VIRTUAL_W * scale), int(VIRTUAL_H * scale)
    scaled = pygame.transform.smoothscale(virtual_surf, (new_w, new_h))
    real_screen.fill((0, 0, 0))
    real_screen.blit(scaled, ((rw - new_w) // 2, (rh - new_h) // 2))

SCREEN_WIDTH, SCREEN_HEIGHT = VIRTUAL_W, VIRTUAL_H
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Avengers Ascent: City Surge")
clock = pygame.time.Clock()

# ─── DIFFICULTY ───────────────────────────────────────────────
DIFF_EASY, DIFF_MEDIUM, DIFF_HARD = 'easy', 'medium', 'hard'
difficulty = DIFF_MEDIUM

DIFF_CONFIG = {
    DIFF_EASY:   {'water_speed': 0.5,  'water_speed_k': 3500, 'enemy_chance': 0.06, 'fall_dmg_mult': 0.25,
                  'platform_gap': (90, 55),  'enemy_speed': 1.6, 'label': 'EASY',   'color': (0, 220, 120),  'hazard': 'water',
                  'wind': 0, 'shoot': False, 'insta_crumble': False},
    DIFF_MEDIUM: {'water_speed': 1.2,  'water_speed_k': 5000, 'enemy_chance': 0.10, 'fall_dmg_mult': 0.45,
                  'platform_gap': (105, 60), 'enemy_speed': 2.2, 'label': 'MEDIUM', 'color': (255, 200, 0),  'hazard': 'water',
                  'wind': 0, 'shoot': False, 'insta_crumble': False},
    DIFF_HARD:   {'water_speed': 3.8,  'water_speed_k': 2500, 'enemy_chance': 0.24, 'fall_dmg_mult': 0.85,
                  'platform_gap': (135, 90), 'enemy_speed': 4.0, 'label': 'HARD',   'color': (255, 60, 30),  'hazard': 'lava',
                  'wind': 1.4, 'shoot': True, 'insta_crumble': True},
}

# ─── ICON ─────────────────────────────────────────────────────
def make_icon_surface():
    ico = pygame.Surface((64, 64), pygame.SRCALPHA)
    ico.fill((6, 4, 14))
    pygame.draw.rect(ico, (20, 24, 42), (2, 38, 12, 24))
    pygame.draw.rect(ico, (20, 24, 42), (16, 30, 10, 32))
    pygame.draw.rect(ico, (20, 24, 42), (38, 26, 8, 36))
    pygame.draw.rect(ico, (20, 24, 42), (48, 34, 14, 28))
    pygame.draw.rect(ico, (0, 90, 200), (0, 56, 64, 8))
    pygame.draw.circle(ico, (245, 200, 170), (32, 22), 5)
    pygame.draw.rect(ico, (40, 120, 220), (28, 27, 8, 10))
    pygame.draw.rect(ico, (50, 50, 65), (28, 37, 3, 8))
    pygame.draw.rect(ico, (50, 50, 65), (33, 37, 3, 8))
    pygame.draw.circle(ico, (0, 210, 255), (32, 32), 30, 2)
    return ico

icon_surf = make_icon_surface()
pygame.display.set_icon(icon_surf)

def save_ico(path="game_icon.ico"):
    try:
        if os.path.exists(path): return
        s32 = pygame.transform.scale(icon_surf, (32, 32))
        s16 = pygame.transform.scale(icon_surf, (16, 16))
        def s2b(surf):
            w, h = surf.get_size(); data = []
            for y in range(h - 1, -1, -1):
                for x in range(w): r, g, b, a = surf.get_at((x, y)); data += [b, g, r, a]
            return bytes(data)
        imgs = [(32, s32), (16, s16)]; ico_data = bytearray()
        ico_data += struct.pack('<HHH', 0, 1, len(imgs))
        offset = 6 + len(imgs) * 16; img_datas = []
        for sz, surf in imgs:
            px = s2b(surf)
            bmp = struct.pack('<IiiHHIIiiII', 40, sz, sz * 2, 1, 32, 0, len(px), 0, 0, 0, 0) + px
            img_datas.append(bmp)
            ico_data += struct.pack('BBBBHHII', sz, sz, 0, 0, 1, 32, len(bmp), offset)
            offset += len(bmp)
        for d in img_datas: ico_data += d
        with open(path, "wb") as f: f.write(ico_data)
    except: pass

save_ico()

# ─── PALETTE ──────────────────────────────────────────────────
CITY_NIGHT    = (6, 4, 14)
SKYLINE_DARK  = (12, 14, 26)
SKYLINE_MID   = (20, 24, 42)
STARK_BLUE    = (0, 210, 255)
WATER_BLUE    = (0, 90, 255, 185)
LAVA_ORANGE   = (255, 80, 10, 210)
WHITE         = (255, 255, 255)
HEALTH_RED    = (220, 40, 40)
NEON_GREEN    = (0, 255, 140)
CRUMBLE_ORANGE= (240, 100, 30)
GOLD          = (255, 215, 0)
PURPLE        = (160, 32, 240)
DARK_GREY     = (30, 30, 50)

HIGHSCORE_FILE = "avengers_highscore.json"
SETTINGS_FILE  = "avengers_settings.json"
DEFAULT_SETTINGS = {"volume": 0.6, "fullscreen": False,
                    "controls": {"left": "A/LEFT", "right": "D/RIGHT", "jump": "W/UP/SPACE"}}

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
            for k in DEFAULT_SETTINGS:
                if k not in s: s[k] = DEFAULT_SETTINGS[k]
            return s
    except: return dict(DEFAULT_SETTINGS)

def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w") as f: json.dump(s, f, indent=2)
    except: pass

settings = load_settings()
master_volume = settings.get("volume", 0.6)
pygame.mixer.music.set_volume(master_volume)

# ─── SOUNDS ───────────────────────────────────────────────────
def make_sound(freq, duration_ms, volume=0.4, wave="sine", fade_ms=30):
    import array as arr_mod
    sr = 44100; n = int(sr * duration_ms / 1000); buf = []
    for i in range(n):
        t = i / sr
        v = (math.sin(2 * math.pi * freq * t) if wave == "sine" else
             (1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0) if wave == "square" else
             random.uniform(-1, 1))
        fade = min(1.0, i / max(1, int(sr * fade_ms / 1000)),
                   (n - i) / max(1, int(sr * fade_ms / 1000)))
        buf.append(int(v * fade * volume * 32767))
    ch = pygame.mixer.get_init()[2]
    raw = arr_mod.array('h', buf * 2 if ch == 2 else buf)
    return pygame.sndarray.make_sound(raw)

snd_jump = snd_djump = snd_land = snd_dmg = snd_powerup = snd_crumble = snd_lava = snd_shoot = None
snd_crash = snd_unlock = None
SOUND_OK = False
try:
    snd_jump    = make_sound(380, 120, 0.3, "sine")
    snd_djump   = make_sound(520, 160, 0.35, "sine")
    snd_land    = make_sound(120, 80,  0.25, "square")
    snd_dmg     = make_sound(200, 200, 0.4,  "square")
    snd_powerup = make_sound(660, 300, 0.4,  "sine")
    snd_crumble = make_sound(90,  250, 0.3,  "noise")
    snd_lava    = make_sound(55,  400, 0.35, "noise")
    snd_shoot   = make_sound(440, 80,  0.25, "square")
    snd_crash   = make_sound(140, 220, 0.45, "noise")
    snd_unlock  = make_sound(740, 260, 0.4,  "sine")
    SOUND_OK = True
except: pass

def play(snd):
    if SOUND_OK and snd is not None:
        try: snd.set_volume(master_volume); snd.play()
        except: pass

# ─── HIGH SCORE ───────────────────────────────────────────────
def load_highscore():
    try:
        with open(HIGHSCORE_FILE) as f:
            d = json.load(f)
            return {DIFF_EASY: d.get("hs_easy", 0),
                    DIFF_MEDIUM: d.get("hs_medium", 0),
                    DIFF_HARD: d.get("hs_hard", 0)}
    except: return {DIFF_EASY: 0, DIFF_MEDIUM: 0, DIFF_HARD: 0}

def save_highscore(s):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump({"hs_easy": s[DIFF_EASY], "hs_medium": s[DIFF_MEDIUM], "hs_hard": s[DIFF_HARD]}, f)
    except: pass

high_scores = load_highscore()

# ─── FONTS ────────────────────────────────────────────────────
def load_fonts():
    global font_hud, font_title, font_sub, font_small, font_med, font_tiny
    try:
        font_hud   = pygame.font.SysFont("Courier New", 20, bold=True)
        font_title = pygame.font.SysFont("Impact", 72)
        font_sub   = pygame.font.SysFont("Courier New", 22, bold=True)
        font_small = pygame.font.SysFont("Courier New", 16)
        font_med   = pygame.font.SysFont("Courier New", 28, bold=True)
        font_tiny  = pygame.font.SysFont("Courier New", 13)
    except:
        font_hud = font_title = font_sub = font_small = font_med = font_tiny = pygame.font.Font(None, 24)

load_fonts()

def draw_text_shadow(surface, text, font, color, pos, shadow_col=(0, 0, 0), off=2):
    surface.blit(font.render(text, True, shadow_col), (pos[0] + off, pos[1] + off))
    surface.blit(font.render(text, True, color), pos)

# ─── BACKGROUND ───────────────────────────────────────────────
def gen_buildings():
    global bg_buildings_far, bg_buildings_mid, window_lights
    bg_buildings_far, bg_buildings_mid, window_lights = [], [], []
    for i in range(200):
        y = VIRTUAL_H - (i * 350) - random.randint(0, 120)
        bg_buildings_far.append({'rect': pygame.Rect(random.randint(-150, VIRTUAL_W + 50), y,
                                                     random.randint(100, 220), random.randint(500, 900)),
                                 'color': SKYLINE_DARK})
    for i in range(250):
        y = VIRTUAL_H - (i * 220) - random.randint(0, 90)
        bg_buildings_mid.append({'rect': pygame.Rect(random.randint(-100, VIRTUAL_W), y,
                                                     random.randint(140, 260), random.randint(400, 700)),
                                 'color': SKYLINE_MID})
    for b in bg_buildings_mid[:80]:
        for _ in range(random.randint(3, 10)):
            wx = b['rect'].x + random.randint(5, max(6, b['rect'].width - 15))
            wy = b['rect'].y + random.randint(5, max(6, b['rect'].height - 15))
            col = random.choice([(255, 255, 180), (255, 220, 120), (180, 220, 255)])
            window_lights.append((wx, wy, col, random.randint(0, 200)))

bg_buildings_far = bg_buildings_mid = window_lights = []
gen_buildings()

# ─── OBJECT POOL – PARTICLES ─────────────────────────
PARTICLE_POOL = [{'active': False, 'x': 0.0, 'y': 0.0, 'vx': 0.0, 'vy': 0.0,
                  'life': 0, 'color': (0, 0, 0), 'size': 2} for _ in range(300)]

def spawn_particles(x, y, color, count=8, speed=3):
    spawned = 0
    for p in PARTICLE_POOL:
        if spawned >= count: break
        if not p['active']:
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1, speed)
            p['active'] = True
            p['x'] = float(x); p['y'] = float(y)
            p['vx'] = math.cos(ang) * spd; p['vy'] = math.sin(ang) * spd
            p['life'] = random.randint(18, 35)
            p['color'] = color
            p['size'] = random.randint(2, 5)
            spawned += 1

def update_particles(surface, camera_y):
    for p in PARTICLE_POOL:
        if not p['active']: continue
        p['x'] += p['vx']; p['y'] += p['vy']
        p['vy'] += 0.12;   p['life'] -= 1
        if p['life'] <= 0: p['active'] = False; continue
        sx, sy = int(p['x']), int(p['y'] - camera_y)
        if 0 <= sx < VIRTUAL_W and 0 <= sy < VIRTUAL_H:
            pygame.draw.circle(surface, p['color'], (sx, sy), p['size'])

# ─── BULLET POOL ─────────────────────────────────────
BULLET_POOL = [{'active': False, 'x': 0.0, 'y': 0.0, 'vx': 0.0, 'vy': 0.0, 'life': 0}
               for _ in range(60)]

def spawn_bullet(x, y, target_x, target_y):
    for b in BULLET_POOL:
        if not b['active']:
            dx = target_x - x; dy = target_y - y
            dist = max(1, math.hypot(dx, dy)); speed = 7
            b['active'] = True
            b['x'] = float(x); b['y'] = float(y)
            b['vx'] = dx / dist * speed; b['vy'] = dy / dist * speed
            b['life'] = 90
            break

def update_bullets(surface, camera_y, player):
    for b in BULLET_POOL:
        if not b['active']: continue
        b['x'] += b['vx']; b['y'] += b['vy']; b['life'] -= 1
        sx, sy = int(b['x']), int(b['y'] - camera_y)
        if 0 <= sx < VIRTUAL_W and 0 <= sy < VIRTUAL_H:
            pygame.draw.circle(surface, (255, 180, 0), (sx, sy), 5)
            pygame.draw.circle(surface, (255, 80, 0),  (sx, sy), 3)
        br = pygame.Rect(b['x'] - 4, b['y'] - 4, 8, 8)
        if br.colliderect(player.rect):
            player.take_hit(); b['active'] = False
        elif b['life'] <= 0:
            b['active'] = False

# ─── POWER-UPS ────────────────────────────────────────────────
class PowerUp:
    TYPES  = ['shield', 'speed', 'heal', 'magnet']
    COLORS = {'shield': STARK_BLUE, 'speed': NEON_GREEN, 'heal': HEALTH_RED, 'magnet': PURPLE}
    LABELS = {'shield': 'SH', 'speed': 'SP', 'heal': 'HP', 'magnet': 'MG'}

    def __init__(self, x, y):
        self.type      = random.choice(self.TYPES)
        self.rect      = pygame.Rect(x, y - 24, 26, 26)
        self.collected = False
        self.bob       = random.uniform(0, math.pi * 2)

    def draw(self, surface, camera_y, frame_count):
        if self.collected: return
        bob_y = math.sin(frame_count * 0.07 + self.bob) * 5
        dr    = self.rect.move(0, int(-camera_y + bob_y))
        col   = self.COLORS[self.type]
        pygame.draw.rect(surface, col,   dr, border_radius=6)
        pygame.draw.rect(surface, WHITE, dr, 2, border_radius=6)
        lbl = font_small.render(self.LABELS[self.type], True, WHITE)
        surface.blit(lbl, (dr.x + 3, dr.y + 5))

# ─── ENEMIES ──────────────────────────────────────────────────
class DroneEnemy:
    def __init__(self, x, y):
        self.x    = float(x); self.y = float(y)
        self.rect = pygame.Rect(int(x), int(y), 36, 22)
        sp        = DIFF_CONFIG[difficulty]['enemy_speed']
        self.speed       = random.choice([-sp, sp])
        self.bob_offset  = random.uniform(0, math.pi * 2)
        self.alive       = True
        self.hit_flash   = 0
        self.shoot_timer = random.randint(60, 180)

    def update(self, frame_count, player):
        if not self.alive: return
        self.x += self.speed
        if self.x < 30 or self.x > VIRTUAL_W - 66: self.speed *= -1
        self.y_draw   = self.y + math.sin(frame_count * 0.06 + self.bob_offset) * 8
        self.rect.x   = int(self.x); self.rect.y = int(self.y_draw)
        if self.hit_flash > 0: self.hit_flash -= 1
        if DIFF_CONFIG[difficulty]['shoot']:
            self.shoot_timer -= 1
            if self.shoot_timer <= 0:
                spawn_bullet(self.rect.centerx, self.rect.centery,
                             player.rect.centerx, player.rect.centery)
                play(snd_shoot); self.shoot_timer = random.randint(90, 200)

    def draw(self, surface, camera_y, frame_count):
        if not self.alive: return
        dr  = self.rect.move(0, -camera_y)
        col = (255, 80, 80) if self.hit_flash > 0 else (180, 60, 60)
        pygame.draw.ellipse(surface, col,        dr)
        pygame.draw.ellipse(surface, HEALTH_RED, dr, 2)
        ex = dr.centerx + (5 if self.speed > 0 else -5)
        pygame.draw.circle(surface, (255, 200, 0), (ex, dr.centery - 2), 4)
        pygame.draw.circle(surface, (0, 0, 0),     (ex, dr.centery - 2), 2)
        for side in [-14, 14]:
            px = dr.centerx + side
            pygame.draw.line(surface, (200, 200, 255), (px, dr.top - 2), (px, dr.top - 10), 2)
            sw = int(abs(math.sin(frame_count * 0.4 + side)) * 10 + 4)
            pygame.draw.line(surface, WHITE, (px - sw, dr.top - 8), (px + sw, dr.top - 8), 2)
        if DIFF_CONFIG[difficulty]['shoot']:
            pygame.draw.circle(surface, (255, 0, 0), (dr.centerx, dr.bottom + 2), 3)

# ─── PLATFORMS ────────────────────────────────────────────────
class CityStairPlatform:
    def __init__(self, x, y, width, ptype='normal'):
        self.rect        = pygame.Rect(x, y, width, 18)
        self.ptype       = ptype
        self.move_speed  = random.choice([-2.5, 2.5]) if ptype == 'moving' else 0
        self.crumble_timer = 50 if not DIFF_CONFIG[difficulty]['insta_crumble'] else 12
        self.stepped_on  = False
        self.destroyed   = False
        self.phase_alpha = 255
        self.spring_bounce = 0
        self.powerup     = None
        self.enemy       = None

    def update(self, frame_count):
        if self.destroyed: return
        if self.ptype == 'moving':
            self.rect.x += self.move_speed
            if self.rect.left < 0 or self.rect.right > VIRTUAL_W: self.move_speed *= -1
        if self.stepped_on and self.ptype == 'unstable':
            self.crumble_timer -= 1
            if self.crumble_timer <= 0: self.destroyed = True; play(snd_crumble)
        if self.ptype == 'phase':
            self.phase_alpha = int(128 + 127 * math.sin(frame_count * 0.05))
        if self.spring_bounce > 0: self.spring_bounce -= 1

    def draw(self, surface, camera_y, frame_count, player):
        if self.destroyed: return
        dr = self.rect.move(0, -camera_y)
        pygame.draw.rect(surface, (35, 45, 70), dr, border_radius=4)
        if   self.ptype == 'normal':   edge = NEON_GREEN
        elif self.ptype == 'moving':   edge = STARK_BLUE
        elif self.ptype == 'unstable':
            frac = self.crumble_timer / 50
            edge = (int(CRUMBLE_ORANGE[0] + (HEALTH_RED[0] - CRUMBLE_ORANGE[0]) * (1 - frac)),
                    int(CRUMBLE_ORANGE[1] * frac), int(CRUMBLE_ORANGE[2] * frac))
        elif self.ptype == 'spring': edge = GOLD
        elif self.ptype == 'phase':
            s = pygame.Surface((dr.width, dr.height), pygame.SRCALPHA)
            s.fill((80, 100, 200, self.phase_alpha)); surface.blit(s, dr.topleft); edge = (80, 100, 255)
        else: edge = WHITE
        pygame.draw.rect(surface, edge, dr, 2, border_radius=4)
        if self.ptype == 'unstable' and self.stepped_on:
            for cx in range(dr.left + 4, dr.right - 4, 8):
                sh = random.randint(-1, 1)
                pygame.draw.line(surface, CRUMBLE_ORANGE, (cx + sh, dr.top), (cx + sh, dr.bottom), 1)
        if self.powerup: self.powerup.draw(surface, camera_y, frame_count)
        if self.enemy:   self.enemy.update(frame_count, player); self.enemy.draw(surface, camera_y, frame_count)

# ─── CHARACTERS ───────────────────────────────────────────────
# Ability keys: 'drone_crash' (AMOR), 'wind_runner' (BEBO), 'high_jump' (MASY),
#               'glider' (RONE), 'magnet_pull' (DOMA), 'heat_shield' (BLAZE)
CHARACTERS = [
    {'name': 'AMOR',  'desc': 'Big & tough — crashes drones, ignores wind', 'body': 'big',
     'skin': (200, 160, 120), 'hair': (50, 30, 10),  'outfit': (30, 60, 120),
     'pants': (80, 50, 20),   'accent': (0, 200, 255), 'cap': (20, 20, 50),
     'cap_logo': (0, 200, 255), 'shoe': (50, 35, 20), 'sole': (150, 100, 50),
     'chain': False, 'earring': False, 'icon_emoji': '💪',
     'ability': 'drone_crash', 'unlock_score': 0},
    {'name': 'BEBO',  'desc': 'Short & fast — quick, but wind hits harder', 'body': 'short',
     'skin': (240, 200, 170), 'hair': (60, 30, 10),  'outfit': (200, 50, 80),
     'pants': (255, 255, 255),'accent': (255, 100, 150), 'cap': None,
     'cap_logo': None, 'shoe': (255, 80, 80), 'sole': (255, 200, 0),
     'chain': False, 'earring': False, 'icon_emoji': '👟',
     'ability': 'wind_runner', 'unlock_score': 1},
    {'name': 'MASY',  'desc': 'Tall & springy — jumps higher than the rest', 'body': 'tall',
     'skin': (220, 185, 155), 'hair': (15, 10, 5),   'outfit': (20, 20, 28),
     'pants': (55, 70, 110),  'accent': (220, 60, 20), 'cap': (10, 10, 14),
     'cap_logo': (220, 60, 20), 'shoe': (30, 30, 30), 'sole': (200, 80, 20),
     'chain': True, 'earring': True, 'icon_emoji': '🧢',
     'ability': 'high_jump', 'unlock_score': 2},
    {'name': 'RONE',  'desc': 'Tall & stylish — outfit glides like a parachute', 'body': 'tall_f',
     'skin': (100, 65, 40),   'hair': (5, 5, 5),     'outfit': (80, 0, 120),
     'pants': (30, 30, 30),   'accent': (200, 100, 255), 'cap': None,
     'cap_logo': None, 'shoe': (100, 0, 150), 'sole': (200, 100, 255),
     'chain': True, 'earring': True, 'icon_emoji': '✨',
     'ability': 'glider', 'unlock_score': 3},
    {'name': 'DOMA',  'desc': 'Quick-handed — passively pulls in power-ups', 'body': 'short_m2',
     'skin': (255, 220, 190), 'hair': (40, 25, 10), 'outfit': (60, 120, 90),
     'pants': (50, 70, 40), 'accent': (255, 220, 0), 'cap': None,
     'cap_logo': None, 'shoe': (70, 60, 30), 'sole': (150, 130, 50),
     'chain': False, 'earring': False, 'icon_emoji': '🧲',
     'ability': 'magnet_pull', 'unlock_score': 4},
    {'name': 'BLAZE', 'desc': 'Balanced & cool — shrugs off heat and falls', 'body': 'medium',
     'skin': (160, 110, 70),  'hair': (20, 10, 5),   'outfit': (20, 80, 20),
     'pants': (20, 40, 80),   'accent': (0, 255, 100), 'cap': (0, 40, 0),
     'cap_logo': (0, 255, 100), 'shoe': (30, 60, 30), 'sole': (0, 200, 80),
     'chain': False, 'earring': False, 'icon_emoji': '⚡',
     'ability': 'heat_shield', 'unlock_score': 5},
]
selected_char = 0

# ─── UNLOCK SYSTEM ────────────────────────────────────────────
# A character at unlock tier N is unlocked once the player's best score on
# ANY difficulty crosses that difficulty's threshold for tier N.
# Tier thresholds scale down as difficulty increases (harder = less distance needed).
UNLOCK_THRESHOLDS = {
    DIFF_EASY:   1500,
    DIFF_MEDIUM: 1000,
    DIFF_HARD:   800,
}

def is_character_unlocked(idx):
    tier = CHARACTERS[idx]['unlock_score']
    if tier <= 0:
        return True
    needed_easy   = UNLOCK_THRESHOLDS[DIFF_EASY]   * tier
    needed_medium = UNLOCK_THRESHOLDS[DIFF_MEDIUM] * tier
    needed_hard   = UNLOCK_THRESHOLDS[DIFF_HARD]   * tier
    # high_scores values are stored in raw units (pixels of height climbed),
    # displayed as meters via //10, so compare against the same raw scale.
    return (high_scores[DIFF_EASY]   >= needed_easy * 10 or
            high_scores[DIFF_MEDIUM] >= needed_medium * 10 or
            high_scores[DIFF_HARD]   >= needed_hard * 10)

def unlock_progress_text(idx):
    tier = CHARACTERS[idx]['unlock_score']
    if tier <= 0: return "UNLOCKED"
    need_e = UNLOCK_THRESHOLDS[DIFF_EASY] * tier
    need_m = UNLOCK_THRESHOLDS[DIFF_MEDIUM] * tier
    need_h = UNLOCK_THRESHOLDS[DIFF_HARD] * tier
    return f"Reach {need_e}m EASY / {need_m}m MED / {need_h}m HARD"

BODY_SIZES = {
    'tall':     (38, 82, 12, 30, 32, 24, 1.0),
    'short':    (32, 62, 10, 26, 26, 18, 1.15),
    'big':      (50, 78, 15, 40, 34, 22, 0.85),
    'tall_f':   (36, 80, 11, 28, 30, 22, 1.05),
    'short_f':  (34, 60, 10, 26, 24, 18, 1.10),
    'short_m2': (34, 60, 10, 26, 24, 18, 1.10),
    'medium':   (38, 72, 11, 30, 28, 20, 1.0),
}

# ─── SPRITE CACHE ────────────────────────────────────
SPRITE_CACHE = {}

def bake_character_sprite(char_idx):
    ch = CHARACTERS[char_idx]
    bs = BODY_SIZES[ch['body']]
    bw, bh, hr, body_w, body_h, leg_h, _ = bs
    W = bw + 40; H = bh + 20
    surf = pygame.Surface((W, H), pygame.SRCALPHA)

    cx2 = W // 2
    by  = 4

    leg_offset = body_w // 2 - 8
    pygame.draw.rect(surf, ch['pants'], (cx2 - leg_offset, by + body_h + 26, 10, leg_h + 2), border_radius=3)
    pygame.draw.rect(surf, ch['pants'], (cx2 + leg_offset - 10, by + body_h + 26, 10, leg_h + 2), border_radius=3)
    for side in [-leg_offset, leg_offset - 10]:
        sx2 = cx2 + side; sy2 = by + body_h + 26 + leg_h + 2
        pygame.draw.rect(surf, ch['shoe'], (sx2 - 2, sy2, 14, 7), border_radius=2)
        pygame.draw.rect(surf, ch['sole'], (sx2 - 2, sy2 + 5, 14, 3), border_radius=1)

    body_top = by + 26
    bx2      = cx2 - body_w // 2
    pygame.draw.rect(surf, ch['outfit'], (bx2, body_top, body_w, body_h + 1), border_radius=5)
    pygame.draw.rect(surf, (max(0, ch['outfit'][0] - 15), max(0, ch['outfit'][1] - 15), max(0, ch['outfit'][2] - 15)),
                     (cx2 - 8, body_top + body_h // 2, 16, 10), border_radius=3)
    pygame.draw.rect(surf, ch['outfit'], (bx2 - 7, body_top + 2, 7, body_h - 6), border_radius=3)
    pygame.draw.rect(surf, ch['outfit'], (bx2 + body_w, body_top + 2, 7, body_h - 6), border_radius=3)
    pygame.draw.rect(surf, ch['skin'],   (bx2 - 7,      body_top + body_h - 8, 7, 5), border_radius=2)
    pygame.draw.rect(surf, ch['skin'],   (bx2 + body_w, body_top + body_h - 8, 7, 5), border_radius=2)

    if ch['body'] in ('short_f', 'tall_f'):
        skirt_top = body_top + body_h - 4
        skirt_pts  = [(cx2 - body_w // 2 - 4, skirt_top), (cx2 + body_w // 2 + 4, skirt_top),
                      (cx2 + body_w // 2 + 12, skirt_top + 18), (cx2 - body_w // 2 - 12, skirt_top + 18)]
        pygame.draw.polygon(surf, ch['accent'], skirt_pts)
        pygame.draw.polygon(surf, (max(0, ch['accent'][0] - 30), max(0, ch['accent'][1] - 30),
                                   max(0, ch['accent'][2] - 30)), skirt_pts, 2)

    neck_y = by + 20
    pygame.draw.rect(surf, ch['skin'], (cx2 - 5, neck_y, 10, 8))
    hcy = by + 14
    pygame.draw.circle(surf, ch['skin'], (cx2, hcy), hr)

    ear_x = cx2 + hr
    pygame.draw.ellipse(surf, ch['skin'], (ear_x - 3, hcy - 3, 6, 7))
    if ch['earring']:
        pygame.draw.circle(surf, GOLD, (ear_x, hcy + 2), 2)

    ex_e = cx2 + 4
    pygame.draw.rect(surf, (15, 15, 20), (ex_e, hcy - 3, 4, 3))
    pygame.draw.line(surf, ch['hair'], (ex_e - 1, hcy - 6), (ex_e + 5, hcy - 5), 2)

    hair_root_y  = hcy - hr + 2
    strand_xs    = [cx2 - hr + 2, cx2 - hr + 5, cx2 - hr + 9, cx2, cx2 + 4, cx2 + 7]
    for si, shx in enumerate(strand_xs):
        phase = si * 0.4
        rad   = math.radians(-8 + math.sin(phase) * 6)
        ex2   = shx + int(math.sin(rad) * 9)
        ey2   = hair_root_y - int(math.cos(rad) * 11) - 2
        pygame.draw.line(surf, ch['hair'], (shx, hair_root_y), (ex2, ey2), 2)

    if ch['cap']:
        cap_y = hcy - hr - 4
        pygame.draw.ellipse(surf, ch['cap'], (cx2 - hr - 2, cap_y, hr * 2 + 4, hr + 2))
        brim_x = cx2 + 4
        pygame.draw.rect(surf, ch['cap'], (brim_x, cap_y + hr - 2, 18, 5), border_radius=2)
        pygame.draw.circle(surf, (60, 60, 60), (cx2, cap_y), 2)
        if ch['cap_logo']:
            pygame.draw.circle(surf, ch['cap_logo'], (cx2 + 4, cap_y + 6), 3)
    else:
        bun_x = cx2 + 4
        pygame.draw.circle(surf, ch['hair'], (bun_x, hcy - hr - 3), 6)
        pygame.draw.ellipse(surf, ch['hair'], (cx2 - hr - 2, hcy - hr + 2, hr * 2 + 4, 8))

    if ch['chain']:
        for ci in range(6):
            cxp = cx2 - 5 + ci * 2; cyp = neck_y + 4 + int(math.sin(ci * 0.9) * 2)
            pygame.draw.circle(surf, GOLD, (cxp, cyp), 1)

    # RONE's glider cape — a small visual hint of the parachute fabric across the back
    if ch.get('ability') == 'glider':
        cape_pts = [(bx2 - 10, body_top + 2), (bx2 - 2, body_top + 2),
                    (bx2 - 14, body_top + body_h + 6), (bx2 - 20, body_top + body_h + 2)]
        pygame.draw.polygon(surf, ch['accent'], cape_pts)

    surf_left = pygame.transform.flip(surf, True, False)
    return surf, surf_left

def bake_all_sprites():
    global SPRITE_CACHE
    SPRITE_CACHE = {}
    for i in range(len(CHARACTERS)):
        r, l = bake_character_sprite(i)
        SPRITE_CACHE[(i, 1)]  = r
        SPRITE_CACHE[(i, -1)] = l

bake_all_sprites()

# ─── SCREENSHAKE ─────────────────────────────────────
shake_frames  = 0
shake_offset  = (0, 0)

def trigger_shake(frames=12):
    global shake_frames
    shake_frames = frames

def update_shake():
    global shake_frames, shake_offset
    if shake_frames > 0:
        shake_frames -= 1
        shake_offset = (random.randint(-5, 5), random.randint(-4, 4))
    else:
        shake_offset = (0, 0)

# ─── PLAYER ───────────────────────────────────────────────────
class PlayerAvatar:
    def __init__(self, x, y):
        ch = CHARACTERS[selected_char]
        bs = BODY_SIZES[ch['body']]
        self.rect = pygame.Rect(x, y, bs[0], bs[1])
        self.bw, self.bh, self.hr, self.body_w, self.body_h, self.leg_h, self.spd_mult = \
            bs[0], bs[1], bs[2], bs[3], bs[4], bs[5], bs[6]
        self.ability         = ch['ability']
        self.vel_y          = 0
        self.direction      = 1
        self.health         = 100
        self.score          = 0
        self.highest_y_in_air = y
        self.is_dead        = False
        self.is_jumping     = False
        self.can_double_jump= True
        self.is_flipping    = False
        self.flip_angle     = 0
        self.walk_cycle     = 0
        self.jump_debounce  = False
        self.shield_timer   = 0
        self.speed_timer    = 0
        self.magnet_timer   = 0
        self.invincible_flash = 0
        self.trail          = []
        self.hair_strands   = [0.0] * 6
        self.hair_vel       = [0.0] * 6
        self.wind_push      = 0.0
        self.scale_x        = 1.0
        self.scale_y        = 1.0
        # elastic-motion smoothing
        self.move_vel_x     = 0.0
        self.glide_timer    = 0

    @property
    def has_shield(self): return self.shield_timer > 0
    @property
    def has_speed(self):  return self.speed_timer > 0
    @property
    def has_magnet(self): return self.magnet_timer > 0 or self.ability == 'magnet_pull'

    def apply_powerup(self, ptype):
        play(snd_powerup)
        if   ptype == 'shield': self.shield_timer = 300
        elif ptype == 'speed':  self.speed_timer  = 300
        elif ptype == 'heal':
            self.health = min(100, self.health + 35)
            spawn_particles(self.rect.centerx, self.rect.centery, HEALTH_RED, 12)
        elif ptype == 'magnet': self.magnet_timer = 400

    def _update_hair(self, moving, jumping):
        wind = 0.18 if self.has_speed else 0.08
        target_angle = self.direction * (-25 if moving else -8)
        if jumping: target_angle += self.direction * -18
        for i in range(len(self.hair_strands)):
            phase   = i * 0.4
            natural = target_angle + math.sin(phase) * 6
            self.hair_vel[i]    += (natural - self.hair_strands[i]) * 0.12
            self.hair_vel[i]    *= 0.75
            self.hair_strands[i] += self.hair_vel[i] + math.sin(pygame.time.get_ticks() * 0.003 + phase) * wind * 4

    def _ease_scale(self):
        self.scale_x += (1.0 - self.scale_x) * 0.25
        self.scale_y += (1.0 - self.scale_y) * 0.25

    def move(self, keys, t_left=False, t_right=False, t_jump=False):
        if self.is_dead: return
        cfg        = DIFF_CONFIG[difficulty]
        is_wind_runner = (self.ability == 'wind_runner')
        BASE_SPEED = 8.5 * self.spd_mult * (1.55 if self.has_speed else 1.0)
        if is_wind_runner: BASE_SPEED *= 1.18
        GRAVITY    = 0.82
        JUMP_HEIGHT= -17.0
        if self.ability == 'high_jump': JUMP_HEIGHT = -19.5
        moving     = False

        # Elastic movement: build a target velocity, then ease toward it for a
        # smoother, slightly springy accel/turn feel instead of an instant snap.
        target_vx = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]  or t_left:
            target_vx -= BASE_SPEED; self.direction = -1; moving = True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT] or t_right:
            target_vx += BASE_SPEED; self.direction =  1; moving = True

        ease = 0.42
        self.move_vel_x += (target_vx - self.move_vel_x) * ease
        self.rect.x += int(round(self.move_vel_x))

        wind_strength = cfg['wind']
        if self.ability == 'drone_crash':
            wind_strength = 0  # AMOR is wind-immune
        elif is_wind_runner:
            wind_strength *= 1.8  # BEBO is hit harder by wind
        if wind_strength > 0:
            self.wind_push += wind_strength * math.sin(pygame.time.get_ticks() * 0.0008) * 0.06
            self.wind_push *= 0.95
            self.rect.x += int(self.wind_push)

        if moving and not self.is_jumping: self.walk_cycle += 0.22
        elif not moving: self.walk_cycle = 0

        if self.rect.right < 0:            self.rect.left  = VIRTUAL_W
        if self.rect.left  > VIRTUAL_W:    self.rect.right = 0

        jump_key = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE] or t_jump
        if jump_key:
            if not self.jump_debounce:
                if not self.is_jumping:
                    self.vel_y            = JUMP_HEIGHT
                    self.is_jumping       = True
                    self.can_double_jump  = True
                    self.highest_y_in_air = self.rect.bottom
                    self.scale_x, self.scale_y = 0.75, 1.3  # subtle stretch on launch
                    self.glide_timer       = 0
                    play(snd_jump)
                    spawn_particles(self.rect.centerx, self.rect.bottom, STARK_BLUE, 5, 2)
                elif self.can_double_jump and not self.is_flipping:
                    self.vel_y            = JUMP_HEIGHT * 0.95
                    self.is_flipping      = True
                    self.can_double_jump  = False
                    self.flip_angle       = 0
                    self.highest_y_in_air = self.rect.bottom
                    play(snd_djump)
                    spawn_particles(self.rect.centerx, self.rect.centery, STARK_BLUE, 10, 4)
                self.jump_debounce = True
        else:
            self.jump_debounce = False

        self._update_hair(moving, self.is_jumping)
        self._ease_scale()

        # RONE's glider: while falling, briefly slow descent for a fraction of
        # a second, like fabric catching air, then resume normal gravity.
        effective_gravity = GRAVITY
        if self.ability == 'glider' and self.is_jumping and self.vel_y > 0:
            if self.glide_timer < 14:  # short hang window, well under a second
                effective_gravity *= 0.35
                self.glide_timer += 1

        self.vel_y  += effective_gravity
        self.rect.y += int(self.vel_y)
        if self.is_jumping and self.rect.bottom < self.highest_y_in_air:
            self.highest_y_in_air = self.rect.bottom
        if self.is_flipping:
            self.flip_angle += 18 * self.direction
            if abs(self.flip_angle) >= 360: self.is_flipping = False; self.flip_angle = 0

        if self.shield_timer  > 0: self.shield_timer  -= 1
        if self.speed_timer   > 0: self.speed_timer   -= 1
        if self.magnet_timer  > 0: self.magnet_timer  -= 1
        if self.invincible_flash > 0: self.invincible_flash -= 1

        if self.has_speed:
            self.trail.append((self.rect.centerx, self.rect.centery))
            if len(self.trail) > 8: self.trail.pop(0)
        else:
            self.trail.clear()

    def landed(self, platform_top, spring=False):
        self.glide_timer = 0
        if spring:
            self.vel_y = -22.0; self.is_jumping = True
            self.highest_y_in_air = self.rect.bottom
            self.scale_x, self.scale_y = 1.3, 0.7
            spawn_particles(self.rect.centerx, self.rect.bottom, GOLD, 10, 4)
            play(snd_djump); return
        cfg       = DIFF_CONFIG[difficulty]
        fall_dist = platform_top - self.highest_y_in_air
        threshold = 320 if difficulty == DIFF_EASY else (300 if difficulty == DIFF_MEDIUM else 200)
        dmg_mult  = cfg['fall_dmg_mult']
        if self.ability == 'heat_shield': dmg_mult *= 0.55  # BLAZE takes less fall damage
        if fall_dist > threshold and not self.has_shield:
            dmg = int((fall_dist - threshold) * dmg_mult)
            self.health -= dmg; self.invincible_flash = 40
            self.scale_x, self.scale_y = 1.35, 0.65  # subtle squash on hard landing
            trigger_shake(10)
            play(snd_dmg)
            spawn_particles(self.rect.centerx, self.rect.bottom, HEALTH_RED, 12, 3)
            if self.health <= 0: self.health = 0; self.is_dead = True
        elif fall_dist > threshold and self.has_shield:
            self.shield_timer = 0
            spawn_particles(self.rect.centerx, self.rect.centery, STARK_BLUE, 20, 5)
        else:
            self.scale_x, self.scale_y = 1.12, 0.88  # gentle settle
        play(snd_land)
        self.rect.bottom       = platform_top
        self.vel_y             = 0
        self.is_jumping        = False
        self.can_double_jump   = True
        self.is_flipping       = False
        self.flip_angle        = 0
        self.highest_y_in_air  = self.rect.bottom

    def take_hit(self):
        if self.invincible_flash > 0:
            if self.has_shield:
                self.shield_timer = 0
                spawn_particles(self.rect.centerx, self.rect.centery, STARK_BLUE, 15, 5)
            return
        self.health -= 18; self.invincible_flash = 90
        trigger_shake(12)
        play(snd_dmg)
        spawn_particles(self.rect.centerx, self.rect.centery, HEALTH_RED, 15, 4)
        if self.health <= 0: self.health = 0; self.is_dead = True

    def draw(self, surface, camera_y, frame_count):
        dr = self.rect.move(0, -camera_y)

        for i, (tx, ty) in enumerate(self.trail):
            af = i / max(1, len(self.trail)); sy = int(ty - camera_y)
            if 0 <= sy < VIRTUAL_H:
                pygame.draw.circle(surface, NEON_GREEN, (tx, sy), int(4 * af + 1))

        visible = (self.invincible_flash // 5 % 2 == 0) if self.invincible_flash > 0 else True

        if self.is_flipping:
            fs  = pygame.Surface((self.bw + 20, self.bh + 10), pygame.SRCALPHA)
            cx2 = fs.get_width() // 2; cy2 = fs.get_height() // 2
            ch  = CHARACTERS[selected_char]
            pygame.draw.rect(fs, ch['outfit'],
                             (cx2 - self.body_w // 2, cy2 - 10, self.body_w, self.body_h), border_radius=4)
            pygame.draw.rect(fs, ch['pants'], (cx2 - 12, cy2 + self.body_h - 10, 10, self.leg_h))
            pygame.draw.rect(fs, ch['pants'], (cx2 + 2,  cy2 + self.body_h - 10, 10, self.leg_h))
            pygame.draw.circle(fs, ch['skin'], (cx2, cy2 - self.hr - 4), self.hr)
            if ch['cap']:
                pygame.draw.ellipse(fs, ch['cap'],
                                    (cx2 - self.hr - 2, cy2 - self.hr * 2 - 8, self.hr * 2 + 4, self.hr))
            rot = pygame.transform.rotate(fs, -self.flip_angle)
            nr  = rot.get_rect(center=dr.center)
            surface.blit(rot, nr.topleft)
            if frame_count % 2 == 0:
                pygame.draw.circle(surface, STARK_BLUE, (dr.centerx, dr.centery),
                                   random.randint(6, 15), 1)

        elif visible:
            base_surf = SPRITE_CACHE[(selected_char, self.direction)]
            sw, sh    = base_surf.get_size()

            draw_w = max(1, int(sw * self.scale_x))
            draw_h = max(1, int(sh * self.scale_y))
            if draw_w != sw or draw_h != sh:
                scaled_surf = pygame.transform.scale(base_surf, (draw_w, draw_h))
            else:
                scaled_surf = base_surf

            blit_x = dr.centerx - draw_w // 2
            blit_y = dr.bottom  - draw_h
            surface.blit(scaled_surf, (blit_x, blit_y))

            if not self.is_jumping and self.walk_cycle != 0:
                ch        = CHARACTERS[selected_char]
                cx2       = dr.centerx
                body_top  = blit_y + int(sh * 0.3)
                lleg_y    = body_top + self.body_h + 10
                llm       = math.sin(self.walk_cycle) * 13
                rlm       = -math.sin(self.walk_cycle) * 13
                leg_offset= self.body_w // 2 - 8
                for side, lm in [(-leg_offset, llm), (leg_offset - 10, rlm)]:
                    lx = cx2 + side
                    pygame.draw.rect(surface, ch['pants'],
                                     (lx, lleg_y + int(lm * 0.1), 10, self.leg_h + 2), border_radius=3)
                    sy2 = lleg_y + self.leg_h + 2 + int(lm * 0.1)
                    pygame.draw.rect(surface, ch['shoe'], (lx - 2, sy2, 14, 7), border_radius=2)
                    pygame.draw.rect(surface, ch['sole'], (lx - 2, sy2 + 5, 14, 3), border_radius=1)

            if frame_count // 15 % 10 == 0:
                ch  = CHARACTERS[selected_char]
                cx2 = dr.centerx
                hcy = blit_y + int(sh * 0.18)
                ex  = cx2 + (4 if self.direction == 1 else -7)
                pygame.draw.rect(surface, (15, 15, 20), (ex, hcy - 3, 4, 1))

        # RONE glider effect: faint billowing parachute trail while the hang window is active
        if self.ability == 'glider' and self.is_jumping and self.vel_y > 0 and self.glide_timer < 14:
            r = int(22 + 3 * math.sin(frame_count * 0.3))
            gs = pygame.Surface((r * 2 + 4, r + 10), pygame.SRCALPHA)
            pygame.draw.ellipse(gs, (*PURPLE, 90), (0, 0, r * 2 + 4, r + 10))
            surface.blit(gs, (dr.centerx - r - 2, dr.top - r // 2))

        if self.has_shield:
            r  = int(30 + 3 * math.sin(frame_count * 0.15))
            ss = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ss, (*STARK_BLUE, 60),  (r + 2, r + 2), r)
            pygame.draw.circle(ss, (*STARK_BLUE, 200), (r + 2, r + 2), r, 2)
            surface.blit(ss, (dr.centerx - r - 2, dr.centery - r - 2))

        if self.has_magnet and self.magnet_timer <= 0 and self.ability == 'magnet_pull':
            r = int(48 + 4 * math.sin(frame_count * 0.1))
            ms = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ms, (*PURPLE, 35), (r, r), r, 2)
            surface.blit(ms, (dr.centerx - r, dr.centery - r))

# ─── SCENE MANAGER ───────────────────────────────────
class SceneManager:
    def __init__(self):
        self._stack = []

    def push(self, scene):
        self._stack.append(scene)

    def pop(self):
        if self._stack: self._stack.pop()

    def replace(self, scene):
        if self._stack: self._stack[-1] = scene
        else: self._stack.append(scene)

    @property
    def current(self):
        return self._stack[-1] if self._stack else None

    @property
    def below(self):
        return self._stack[-2] if len(self._stack) >= 2 else None

manager = SceneManager()

# ─── GAME DATA ────────────────────────────────────────
platforms     = []
enemies_list  = []
powerups_list = []
player        = None
water_y       = VIRTUAL_H + 150
camera_y      = 0.0
frame_count   = 0
new_record    = False
last_platform_x        = VIRTUAL_W // 2
current_generation_y   = VIRTUAL_H - 150
wind_offset            = 0.0
lava_bubbles = [{'x': random.randint(0, VIRTUAL_W), 'phase': random.uniform(0, 6)} for _ in range(18)]

def build_fair_city_stairs(target_y, current_score):
    global current_generation_y, last_platform_x
    cfg = DIFF_CONFIG[difficulty]
    while current_generation_y > target_y:
        df        = min(current_score / 12000, 1.0)
        base_g, extra_g = cfg['platform_gap']
        width     = int(200 - (90 * df))
        gap_y     = int(base_g + (extra_g * df))
        roll      = random.random()
        if current_score < 500: ptype = 'normal'
        elif roll < 0.35:  ptype = 'normal'
        elif roll < 0.55:  ptype = 'moving'
        elif roll < 0.70:  ptype = 'unstable'
        elif roll < 0.80:  ptype = 'spring'
        else:              ptype = 'phase'
        # Scale max horizontal reach with difficulty so wider hard-mode gaps stay reachable
        max_reach = 230 + int(40 * (gap_y / max(1, base_g + extra_g)))
        min_x     = max(20, last_platform_x - max_reach)
        max_x     = min(VIRTUAL_W - width - 20, last_platform_x + max_reach)
        new_x     = random.randint(min_x, max_x) if min_x < max_x else random.randint(50, VIRTUAL_W - width - 50)
        p         = CityStairPlatform(new_x, current_generation_y, width, ptype)
        if random.random() < 0.15:
            pu = PowerUp(p.rect.centerx - 13, p.rect.y)
            p.powerup = pu; powerups_list.append(pu)
        if current_score > 700 and random.random() < cfg['enemy_chance']:
            e = DroneEnemy(new_x + width // 2, current_generation_y - 40)
            p.enemy = e; enemies_list.append(e)
        platforms.append(p)
        last_platform_x      = new_x
        current_generation_y -= gap_y

def cull_offscreen(camera_y):
    # Drop platforms/enemies/powerups well below the camera so lists don't grow forever.
    cutoff = camera_y + VIRTUAL_H + 600
    global platforms
    keep_platforms = [p for p in platforms if p.rect.y < cutoff]
    removed = [p for p in platforms if p.rect.y >= cutoff]
    for p in removed:
        if p.enemy and p.enemy in enemies_list: enemies_list.remove(p.enemy)
        if p.powerup and p.powerup in powerups_list: powerups_list.remove(p.powerup)
    platforms[:] = keep_platforms

unlocked_snapshot = set()

def take_unlock_snapshot():
    global unlocked_snapshot
    unlocked_snapshot = {i for i in range(len(CHARACTERS)) if is_character_unlocked(i)}

def reset_game():
    global player, water_y, camera_y, current_generation_y, last_platform_x
    global frame_count, wind_offset
    take_unlock_snapshot()
    player = PlayerAvatar(VIRTUAL_W // 2, VIRTUAL_H - 120)
    platforms.clear(); enemies_list.clear(); powerups_list.clear()
    for p in PARTICLE_POOL: p['active'] = False
    for b in BULLET_POOL:   b['active'] = False
    platforms.append(CityStairPlatform(-200, VIRTUAL_H - 40, VIRTUAL_W + 400, 'normal'))
    last_platform_x      = VIRTUAL_W // 2
    current_generation_y = VIRTUAL_H - 150
    water_y       = VIRTUAL_H + 150
    camera_y      = 0.0
    frame_count   = 0
    wind_offset   = 0.0
    gen_buildings()
    build_fair_city_stairs(player.rect.y - 1500, 0)

# ─── TOUCH STATE ──────────────────────────────────────────────
touch_fingers      = {}
touch_left         = False
touch_right        = False
touch_jump         = False
SWIPE_UP_THRESHOLD = 55
info_btn_rect      = pygame.Rect(VIRTUAL_W - 44, VIRTUAL_H - 44, 34, 34)

def process_touch_fingers():
    global touch_left, touch_right
    touch_left = touch_right = False
    for fid, data in touch_fingers.items():
        cx = data['cur'][0]
        if cx < VIRTUAL_W // 2: touch_left  = True
        else:                    touch_right = True

# ─── SHARED DRAW HELPERS ──────────────────────────────────────
def draw_info_btn(surface):
    pygame.draw.circle(surface, (30, 50, 80),
                       (info_btn_rect.centerx, info_btn_rect.centery), 17)
    pygame.draw.circle(surface, STARK_BLUE,
                       (info_btn_rect.centerx, info_btn_rect.centery), 17, 2)
    lbl = font_sub.render("i", True, STARK_BLUE)
    surface.blit(lbl, (info_btn_rect.centerx - lbl.get_width() // 2,
                        info_btn_rect.centery - lbl.get_height() // 2))

def draw_background(surface, cam_y):
    surface.fill(CITY_NIGHT)
    for b in bg_buildings_far:
        pygame.draw.rect(surface, b['color'], b['rect'].move(0, -int(cam_y * 0.15)))
    for b in bg_buildings_mid:
        pygame.draw.rect(surface, b['color'], b['rect'].move(0, -int(cam_y * 0.45)))
    for wx, wy, col, phase in window_lights:
        sy = wy - int(cam_y * 0.45)
        if 0 <= sy < VIRTUAL_H and math.sin(frame_count * 0.03 + phase * 0.1) > 0.2:
            pygame.draw.rect(surface, col, (wx, sy, 6, 5))

def draw_lava(surface, w_y, cam_y, fc):
    wsy = int(w_y - cam_y)
    if wsy >= VIRTUAL_H: return
    h   = VIRTUAL_H - max(0, wsy)
    ls  = pygame.Surface((VIRTUAL_W, h + 2), pygame.SRCALPHA)
    ls.fill((200, 50, 0, 220))
    for yi in range(min(18, h)):
        alpha = int(255 * (1 - yi / 18))
        rs    = pygame.Surface((VIRTUAL_W, 1), pygame.SRCALPHA)
        rs.fill((255, 160, 0, alpha)); ls.blit(rs, (0, yi))
    surface.blit(ls, (0, max(0, wsy)))
    for xi in range(0, VIRTUAL_W, 30):
        wave    = int(10 * math.sin((fc * 0.18) + xi * 0.07))
        crest_y = max(0, wsy + wave)
        if crest_y < VIRTUAL_H:
            pygame.draw.circle(surface, (255, 100, 0), (xi + 15, crest_y), 14)
    for b in lava_bubbles:
        by2 = wsy - int(20 * math.sin(fc * 0.05 + b['phase'])) - 10
        if 0 <= by2 < VIRTUAL_H:
            r = int(5 + 4 * math.sin(fc * 0.07 + b['phase']))
            pygame.draw.circle(surface, (255, 200, 0), (int(b['x']), by2), r, 2)
    if fc % 5 == 0 and wsy < VIRTUAL_H:
        spawn_particles(random.randint(0, VIRTUAL_W), wsy,
                        random.choice([(255, 100, 0), (255, 200, 0), (255, 60, 0)]), count=1, speed=2)

def draw_water(surface, w_y, cam_y, fc):
    wsy = int(w_y - cam_y)
    if wsy >= VIRTUAL_H: return
    h   = VIRTUAL_H - max(0, wsy)
    ws  = pygame.Surface((VIRTUAL_W, h), pygame.SRCALPHA)
    ws.fill(WATER_BLUE)
    for xi in range(0, VIRTUAL_W, 25):
        wave = int(8 * math.sin((fc * 0.15) + xi * 0.05))
        pygame.draw.circle(ws, STARK_BLUE, (xi + 12, max(0, wave)), 15)
    surface.blit(ws, (0, max(0, wsy)))

def draw_wind_lines(surface, fc):
    cfg = DIFF_CONFIG[difficulty]
    if cfg['wind'] == 0: return
    wind_dir = math.sin(pygame.time.get_ticks() * 0.0008)
    for i in range(12):
        y      = int((i * 70 + fc * 3 * wind_dir) % VIRTUAL_H)
        length = int(60 + 30 * abs(wind_dir))
        alpha  = int(80 * abs(wind_dir))
        if alpha > 10:
            xs  = random.randint(0, VIRTUAL_W - length) if wind_dir > 0 else random.randint(length, VIRTUAL_W)
            ls2 = pygame.Surface((length, 2), pygame.SRCALPHA)
            ls2.fill((200, 220, 255, alpha))
            surface.blit(ls2, (xs, y))

def draw_touch_hint(surface):
    if not touch_fingers:
        hint = font_small.render("TAP LEFT  ←  |  SWIPE UP to jump  |  →  TAP RIGHT", True, (70, 70, 110))
        surface.blit(hint, (VIRTUAL_W // 2 - hint.get_width() // 2, VIRTUAL_H - 28))
    else:
        for fid, data in touch_fingers.items():
            cx = data['cur'][0]
            if cx < VIRTUAL_W // 2:
                zs = pygame.Surface((VIRTUAL_W // 2, VIRTUAL_H), pygame.SRCALPHA)
                zs.fill((0, 210, 255, 20)); surface.blit(zs, (0, 0))
            else:
                zs = pygame.Surface((VIRTUAL_W // 2, VIRTUAL_H), pygame.SRCALPHA)
                zs.fill((0, 255, 140, 20)); surface.blit(zs, (VIRTUAL_W // 2, 0))

def draw_hud(surface, p, w_y, fc, hs):
    cfg = DIFF_CONFIG[difficulty]
    draw_text_shadow(surface, f"ALTITUDE: {p.score // 10} m", font_hud, WHITE, (40, 28))
    draw_text_shadow(surface, f"BEST: {hs[difficulty] // 10} m", font_hud, GOLD, (40, 52))
    badge = font_small.render(f"[ {cfg['label']} ]", True, cfg['color'])
    surface.blit(badge, (40, 76))
    ch = CHARACTERS[selected_char]
    cr = font_small.render(f"[ {ch['name']} ]", True, (160, 160, 200))
    surface.blit(cr, (40, 94))
    flood_gap = w_y - p.rect.bottom
    if flood_gap < 220:
        warn = "VOLCANO CRITICAL!" if cfg['hazard'] == 'lava' else "FLOOD CRITICAL!"
        col  = (255, 100, 0) if cfg['hazard'] == 'lava' else HEALTH_RED
        surface.blit(font_hud.render(warn, True, col), (40, 114))
    elif cfg['wind'] > 0:
        wdir = ">>> WIND >>>" if math.sin(pygame.time.get_ticks() * 0.0008) > 0 else "<<< WIND <<<"
        surface.blit(font_hud.render(wdir, True, (180, 210, 255)), (40, 114))
    elif p.is_flipping:
        surface.blit(font_hud.render("DOUBLE FLIP!", True, STARK_BLUE), (40, 114))
    else:
        surface.blit(font_hud.render("ASCENDING", True, NEON_GREEN), (40, 114))
    pu_x = VIRTUAL_W - 240
    if p.shield_timer > 0:
        pygame.draw.rect(surface, STARK_BLUE,
                         (pu_x, 26, int(180 * p.shield_timer / 300), 14), border_radius=3)
        surface.blit(font_small.render("SHIELD", True, STARK_BLUE), (pu_x + 4, 44)); pu_x -= 200
    if p.speed_timer > 0:
        pygame.draw.rect(surface, NEON_GREEN,
                         (pu_x, 26, int(180 * p.speed_timer / 300), 14), border_radius=3)
        surface.blit(font_small.render("SPEED", True, NEON_GREEN), (pu_x + 4, 44)); pu_x -= 200
    if p.magnet_timer > 0:
        pygame.draw.rect(surface, PURPLE,
                         (pu_x, 26, int(180 * p.magnet_timer / 400), 14), border_radius=3)
        surface.blit(font_small.render("MAGNET", True, PURPLE), (pu_x + 4, 44))
    surface.blit(font_hud.render("HEALTH", True, WHITE), (VIRTUAL_W - 240, VIRTUAL_H - 60))
    pygame.draw.rect(surface, (70, 20, 20),
                     (VIRTUAL_W - 240, VIRTUAL_H - 38, 200, 14), border_radius=3)
    if p.health > 0:
        hcol = NEON_GREEN if p.health > 60 else GOLD if p.health > 30 else HEALTH_RED
        pygame.draw.rect(surface, hcol,
                         (VIRTUAL_W - 240, VIRTUAL_H - 38, int(p.health * 2), 14), border_radius=3)
    pygame.draw.rect(surface, WHITE,
                     (VIRTUAL_W - 240, VIRTUAL_H - 38, 200, 14), 1, border_radius=3)
    surface.blit(font_small.render("ESC Pause | F11 Fullscreen", True, (80, 80, 120)),
                 (VIRTUAL_W - 280, VIRTUAL_H - 22))
    draw_touch_hint(surface)
    draw_info_btn(surface)

# ─── SCENES ───────────────────────────────────────────────────

class SplashScene:
    def __init__(self): self.timer = 0

    def handle_event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.FINGERDOWN):
            manager.replace(MenuScene())

    def update(self):
        self.timer += 1
        if self.timer >= 180: manager.replace(MenuScene())

    def draw(self, surface):
        surface.fill(CITY_NIGHT)
        cx, cy   = VIRTUAL_W // 2, VIRTUAL_H // 2
        ring_r   = int(90 * min(1.0, self.timer / 40))
        if ring_r > 0:
            pygame.draw.circle(surface, STARK_BLUE, (cx, cy), ring_r, 3)
        if self.timer > 30:
            ic = pygame.transform.scale(icon_surf, (100, 100))
            ic.set_alpha(min(255, (self.timer - 30) * 8))
            surface.blit(ic, (cx - 50, cy - 50))
        if self.timer > 70:
            l1 = font_sub.render("CITY SURGE STUDIOS", True, STARK_BLUE)
            l1.set_alpha(min(255, (self.timer - 70) * 6))
            surface.blit(l1, (cx - l1.get_width() // 2, cy + 70))
        if self.timer > 100:
            l2 = font_small.render("presents", True, WHITE)
            l2.set_alpha(min(255, (self.timer - 100) * 5))
            surface.blit(l2, (cx - l2.get_width() // 2, cy + 100))
        bar_w = int((VIRTUAL_W - 200) * min(1.0, self.timer / 180))
        pygame.draw.rect(surface, DARK_GREY,  (100, VIRTUAL_H - 50, VIRTUAL_W - 200, 10), border_radius=5)
        pygame.draw.rect(surface, STARK_BLUE, (100, VIRTUAL_H - 50, bar_w, 10),           border_radius=5)
        surface.blit(font_small.render("Loading...", True, (100, 100, 140)), (100, VIRTUAL_H - 30))


class MenuScene:
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                manager.push(InfoScene(self))
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                manager.replace(DiffSelectScene())
            elif event.key == pygame.K_s:
                manager.push(SettingsScene())
            elif event.key == pygame.K_q:
                save_highscore(high_scores); save_settings(settings); pygame.quit(); sys.exit()
        if event.type == pygame.FINGERDOWN:
            manager.replace(DiffSelectScene())
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos):
                manager.push(InfoScene(self))

    def update(self): pass

    def draw(self, surface):
        surface.fill(CITY_NIGHT)
        for b in bg_buildings_far: pygame.draw.rect(surface, b['color'], b['rect'])
        for b in bg_buildings_mid: pygame.draw.rect(surface, b['color'], b['rect'])
        for wx, wy, col, phase in window_lights:
            if math.sin(frame_count * 0.03 + phase * 0.1) > 0.2:
                pygame.draw.rect(surface, col, (wx, wy, 6, 5))
        title_col = (int(100 + 155 * abs(math.sin(frame_count * 0.03))), 210, 255)
        tx1 = VIRTUAL_W // 2 - font_title.size("AVENGERS ASCENT")[0] // 2
        tx2 = VIRTUAL_W // 2 - font_title.size("CITY SURGE")[0] // 2
        draw_text_shadow(surface, "AVENGERS ASCENT", font_title, title_col, (tx1, 145))
        draw_text_shadow(surface, "CITY SURGE",      font_title, STARK_BLUE, (tx2, 225))
        pulse = int(3 * math.sin(frame_count * 0.1))
        btn   = pygame.Rect(VIRTUAL_W // 2 - 130, 335 - pulse, 260, 52)
        pygame.draw.rect(surface, STARK_BLUE, btn, border_radius=10)
        pygame.draw.rect(surface, WHITE,      btn, 2, border_radius=10)
        draw_text_shadow(surface, "ENTER  —  PLAY", font_sub, WHITE, (btn.x + 30, btn.y + 13))
        btn2 = pygame.Rect(VIRTUAL_W // 2 - 130, 403, 260, 46)
        pygame.draw.rect(surface, DARK_GREY,  btn2, border_radius=10)
        pygame.draw.rect(surface, STARK_BLUE, btn2, 2, border_radius=10)
        draw_text_shadow(surface, "S  —  SETTINGS", font_sub, WHITE, (btn2.x + 30, btn2.y + 11))
        btn3 = pygame.Rect(VIRTUAL_W // 2 - 130, 465, 260, 46)
        pygame.draw.rect(surface, DARK_GREY,     btn3, border_radius=10)
        pygame.draw.rect(surface, (120, 40, 40), btn3, 2, border_radius=10)
        draw_text_shadow(surface, "Q  —  QUIT", font_sub, (200, 100, 100), (btn3.x + 50, btn3.y + 11))
        best_y = 530
        for di, diff in enumerate([DIFF_EASY, DIFF_MEDIUM, DIFF_HARD]):
            cfg = DIFF_CONFIG[diff]; hs = high_scores[diff]
            if hs > 0:
                t = font_small.render(f"{cfg['label']}: {hs // 10}m", True, cfg['color'])
                surface.blit(t, (VIRTUAL_W // 2 - 180 + di * 130, best_y))
        legend = [("■ NORMAL", NEON_GREEN), ("■ MOVING", STARK_BLUE),
                  ("■ UNSTABLE", CRUMBLE_ORANGE), ("■ SPRING", GOLD), ("■ PHASE", (80, 100, 255))]
        for i, (txt, col) in enumerate(legend):
            surface.blit(font_small.render(txt, True, col), (60 + i * 198, VIRTUAL_H - 48))
        surface.blit(font_small.render("F11 — Toggle Fullscreen", True, (80, 80, 120)),
                     (VIRTUAL_W - 250, VIRTUAL_H - 24))
        draw_info_btn(surface)


class DiffSelectScene:
    def __init__(self): self.cursor = 1

    def handle_event(self, event):
        global difficulty
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                manager.push(InfoScene(self))
            elif event.key == pygame.K_ESCAPE:
                manager.replace(MenuScene())
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.cursor = (self.cursor - 1) % 3
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.cursor = (self.cursor + 1) % 3
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                difficulty = [DIFF_EASY, DIFF_MEDIUM, DIFF_HARD][self.cursor]
                manager.replace(CharSelectScene())
        if event.type == pygame.FINGERDOWN:
            manager.replace(CharSelectScene())
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos): manager.push(InfoScene(self))

    def update(self): pass

    def draw(self, surface):
        surface.fill(CITY_NIGHT)
        for b in bg_buildings_far: pygame.draw.rect(surface, b['color'], b['rect'])
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140)); surface.blit(overlay, (0, 0))
        draw_text_shadow(surface, "SELECT DIFFICULTY", font_title, STARK_BLUE,
                         (VIRTUAL_W // 2 - font_title.size("SELECT DIFFICULTY")[0] // 2, 70))
        diffs = [DIFF_EASY, DIFF_MEDIUM, DIFF_HARD]
        descs = {
            DIFF_EASY:   ["Platforms closer", "Slow flood",      "Less fall damage", "Few drones"],
            DIFF_MEDIUM: ["Balanced layout",  "Normal flood",    "Standard damage",  "Regular drones"],
            DIFF_HARD:   ["Wide gaps",         "VOLCANO x3 speed","HIGH damage",      "Drones SHOOT  +  WIND"],
        }
        for i, diff in enumerate(diffs):
            cfg = DIFF_CONFIG[diff]; sel = (i == self.cursor)
            bx = VIRTUAL_W // 2 - 460 + i * 320; by = 200; bw, bh = 280, 260
            box = pygame.Rect(bx, by, bw, bh)
            pygame.draw.rect(surface, (25, 45, 70) if sel else (12, 18, 30), box, border_radius=12)
            pygame.draw.rect(surface, cfg['color'] if sel else (40, 50, 70), box, 3 if sel else 1, border_radius=12)
            if sel:
                pulse = int(2 * math.sin(frame_count * 0.1))
                glow  = pygame.Rect(bx - pulse, by - pulse, bw + pulse * 2, bh + pulse * 2)
                gs    = pygame.Surface((glow.width, glow.height), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*cfg['color'], 40), (0, 0, glow.width, glow.height), border_radius=14)
                surface.blit(gs, (glow.x, glow.y))
            lbl = font_med.render(cfg['label'], True, cfg['color'])
            surface.blit(lbl, (bx + bw // 2 - lbl.get_width() // 2, by + 18))
            haz = font_small.render(f"Hazard: {cfg['hazard'].upper()}", True,
                                     WHITE if diff != DIFF_HARD else (255, 120, 0))
            surface.blit(haz, (bx + bw // 2 - haz.get_width() // 2, by + 54))
            for j, line in enumerate(descs[diff]):
                col = WHITE if sel else (130, 130, 150)
                dl  = font_small.render("• " + line, True, col); surface.blit(dl, (bx + 16, by + 90 + j * 34))
            hs     = high_scores[diff]
            hs_txt = font_small.render(f"BEST: {hs // 10}m", True, GOLD if hs > 0 else (60, 60, 80))
            surface.blit(hs_txt, (bx + bw // 2 - hs_txt.get_width() // 2, by + bh - 34))
        draw_text_shadow(surface, "← → or A/D to select    ENTER to play    ESC back",
                         font_small, (100, 100, 140), (VIRTUAL_W // 2 - 280, VIRTUAL_H - 52))
        draw_info_btn(surface)


class CharSelectScene:
    def __init__(self):
        self.cursor = 0
        if not is_character_unlocked(self.cursor):
            for i in range(len(CHARACTERS)):
                if is_character_unlocked(i):
                    self.cursor = i; break

    def _move_cursor(self, delta):
        n = len(CHARACTERS)
        self.cursor = (self.cursor + delta) % n

    def handle_event(self, event):
        global selected_char
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                manager.push(InfoScene(self))
            elif event.key == pygame.K_ESCAPE:
                manager.replace(DiffSelectScene())
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._move_cursor(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._move_cursor(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if is_character_unlocked(self.cursor):
                    selected_char = self.cursor
                    reset_game()
                    manager.replace(GameplayScene())
                else:
                    play(snd_dmg)
        if event.type == pygame.FINGERDOWN:
            if is_character_unlocked(self.cursor):
                selected_char = self.cursor; reset_game(); manager.replace(GameplayScene())
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos): manager.push(InfoScene(self))

    def update(self): pass

    def draw(self, surface):
        surface.fill(CITY_NIGHT)
        for b in bg_buildings_far: pygame.draw.rect(surface, b['color'], b['rect'])
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150)); surface.blit(overlay, (0, 0))
        draw_text_shadow(surface, "CHOOSE YOUR RUNNER", font_title, STARK_BLUE,
                         (VIRTUAL_W // 2 - font_title.size("CHOOSE YOUR RUNNER")[0] // 2, 40))
        card_w, card_h = 160, 270; cols = 6
        total_w = cols * card_w + (cols - 1) * 14
        start_x = VIRTUAL_W // 2 - total_w // 2
        for i, ch in enumerate(CHARACTERS):
            sel     = (i == self.cursor)
            unlocked = is_character_unlocked(i)
            bx = start_x + i * (card_w + 14); by = 145
            box = pygame.Rect(bx, by, card_w, card_h)
            pygame.draw.rect(surface, (25, 45, 70) if sel else (10, 16, 28), box, border_radius=10)
            pygame.draw.rect(surface, STARK_BLUE if sel else (40, 50, 70), box, 3 if sel else 1, border_radius=10)
            preview = pygame.Surface((card_w - 16, 140), pygame.SRCALPHA)
            pw, ph  = preview.get_size(); pcx = pw // 2; pcy = ph // 2 + 10
            bs      = BODY_SIZES[ch['body']]
            bw2, hr2, bh2 = bs[2] * 2, bs[2], bs[4]
            pygame.draw.rect(preview, ch['outfit'],  (pcx - bw2 // 2, pcy - 10, bw2, bh2), border_radius=4)
            pygame.draw.rect(preview, ch['pants'],   (pcx - bw2 // 2 + 2, pcy + bh2 - 10, bw2 // 2 - 3, 18), border_radius=2)
            pygame.draw.rect(preview, ch['pants'],   (pcx + 3, pcy + bh2 - 10, bw2 // 2 - 3, 18), border_radius=2)
            pygame.draw.rect(preview, ch['shoe'],    (pcx - bw2 // 2, pcy + bh2 + 7, bw2 // 2 - 1, 5), border_radius=1)
            pygame.draw.rect(preview, ch['shoe'],    (pcx + 2, pcy + bh2 + 7, bw2 // 2 - 1, 5), border_radius=1)
            pygame.draw.circle(preview, ch['skin'],  (pcx, pcy - hr2 - 6), hr2)
            if ch['cap']:
                pygame.draw.ellipse(preview, ch['cap'], (pcx - hr2 - 2, pcy - hr2 * 2 - 10, hr2 * 2 + 4, hr2 + 2))
                pygame.draw.rect(preview, ch['cap'], (pcx + 3, pcy - hr2 - 4, 14, 4), border_radius=1)
            else:
                pygame.draw.ellipse(preview, ch['hair'], (pcx - hr2 - 2, pcy - hr2 * 2 - 4, hr2 * 2 + 4, 8))
                pygame.draw.circle(preview, ch['hair'], (pcx + 3, pcy - hr2 - 8), 5)
            if ch['body'] in ('short_f', 'tall_f'):
                pts = [(pcx - bw2 // 2 - 3, pcy + bh2 - 12), (pcx + bw2 // 2 + 3, pcy + bh2 - 12),
                       (pcx + bw2 // 2 + 8, pcy + bh2 + 8),  (pcx - bw2 // 2 - 8, pcy + bh2 + 8)]
                pygame.draw.polygon(preview, ch['accent'], pts)
            if not unlocked:
                lockoverlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
                lockoverlay.fill((0, 0, 0, 170)); preview.blit(lockoverlay, (0, 0))
            surface.blit(preview, (bx + 8, by + 8))
            nl = font_small.render(ch['name'], True, STARK_BLUE if sel else (WHITE if unlocked else (110, 110, 130)))
            surface.blit(nl, (bx + card_w // 2 - nl.get_width() // 2, by + card_h - 96))
            if unlocked:
                dl = font_tiny.render(ch['desc'][:26], True, (160, 160, 200) if sel else (80, 80, 110))
                surface.blit(dl, (bx + card_w // 2 - dl.get_width() // 2, by + card_h - 78))
                em = font_small.render(ch['icon_emoji'], True, WHITE)
                surface.blit(em, (bx + card_w // 2 - em.get_width() // 2, by + card_h - 58))
            else:
                lock_lbl = font_small.render("🔒 LOCKED", True, (255, 120, 60))
                surface.blit(lock_lbl, (bx + card_w // 2 - lock_lbl.get_width() // 2, by + card_h - 78))
                prog_lines = unlock_progress_text(i)
                # wrap onto two short lines for the narrow card
                words = prog_lines.split(' / ')
                for li, line in enumerate(words[:2]):
                    pl = font_tiny.render(line.strip(), True, (180, 140, 100))
                    surface.blit(pl, (bx + card_w // 2 - pl.get_width() // 2, by + card_h - 58 + li * 14))
            if sel:
                pulse2 = int(3 * math.sin(frame_count * 0.12))
                pygame.draw.rect(surface, (*STARK_BLUE, 80),
                                 pygame.Rect(bx - pulse2, by - pulse2, card_w + pulse2 * 2, card_h + pulse2 * 2),
                                 border_radius=12)
        if not is_character_unlocked(self.cursor):
            warn = font_sub.render("This runner is still locked!", True, (255, 120, 60))
            surface.blit(warn, (VIRTUAL_W // 2 - warn.get_width() // 2, by + card_h + 28))
        draw_text_shadow(surface, "← → or A/D to select    ENTER to confirm    ESC back",
                         font_small, (100, 100, 140), (VIRTUAL_W // 2 - 290, VIRTUAL_H - 40))
        draw_info_btn(surface)


class SettingsScene:
    def __init__(self): self.cursor = 0

    def handle_event(self, event):
        global master_volume
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                manager.push(InfoScene(self))
            elif event.key == pygame.K_ESCAPE:
                save_settings(settings); manager.pop()
            elif event.key == pygame.K_UP:   self.cursor = (self.cursor - 1) % 3
            elif event.key == pygame.K_DOWN: self.cursor = (self.cursor + 1) % 3
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.cursor == 1:
                    settings["fullscreen"] = not settings.get("fullscreen", False)
                    set_display(settings["fullscreen"]); gen_buildings(); load_fonts(); save_settings(settings)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.cursor == 0:
                    settings["volume"] = max(0.0, round(settings.get("volume", 0.6) - 0.05, 2))
                    master_volume = settings["volume"]
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.cursor == 0:
                    settings["volume"] = min(1.0, round(settings.get("volume", 0.6) + 0.05, 2))
                    master_volume = settings["volume"]
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos): manager.push(InfoScene(self))

    def update(self): pass

    def draw(self, surface):
        surface.fill(CITY_NIGHT)
        for b in bg_buildings_far: pygame.draw.rect(surface, b['color'], b['rect'])
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160)); surface.blit(overlay, (0, 0))
        draw_text_shadow(surface, "SETTINGS", font_title, STARK_BLUE, (VIRTUAL_W // 2 - 140, 60))
        vol = settings.get("volume", 0.6); fs = settings.get("fullscreen", False)
        rows = [("Master Volume", f"{int(vol * 100)}%", "← → to adjust"),
                ("Fullscreen",    "ON" if fs else "OFF", "ENTER to toggle"),
                ("Controls",      "WASD / Arrow Keys",   "fixed layout")]
        for i, (label, val, hint) in enumerate(rows):
            y   = 200 + i * 110; selected = (i == self.cursor)
            box = pygame.Rect(VIRTUAL_W // 2 - 320, y, 640, 80)
            pygame.draw.rect(surface, (30, 50, 80) if selected else (15, 20, 35), box, border_radius=8)
            pygame.draw.rect(surface, STARK_BLUE if selected else (40, 50, 70), box, 2, border_radius=8)
            draw_text_shadow(surface, label, font_sub, WHITE, (box.x + 24, box.y + 10))
            draw_text_shadow(surface, val, font_med, GOLD if selected else NEON_GREEN, (box.x + 24, box.y + 42))
            surface.blit(font_small.render(hint, True, (100, 100, 140)), (box.right - len(hint) * 8 - 20, box.y + 56))
            if i == 0:
                bx2 = box.x + 340; bw2 = 260; by2 = box.y + 48
                pygame.draw.rect(surface, (40, 40, 60), (bx2, by2, bw2, 10),          border_radius=5)
                pygame.draw.rect(surface, STARK_BLUE,   (bx2, by2, int(bw2 * vol), 10), border_radius=5)
        draw_text_shadow(surface, "↑ ↓ Navigate    ENTER Toggle    ESC Back",
                         font_small, (100, 100, 140), (VIRTUAL_W // 2 - 220, VIRTUAL_H - 55))
        draw_info_btn(surface)


class GameplayScene:
    def __init__(self):
        self.touch_jump = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                manager.push(PauseScene())
            elif event.key == pygame.K_i:
                manager.push(InfoScene(self))
        if event.type == pygame.FINGERDOWN:
            fx = int(event.x * VIRTUAL_W); fy = int(event.y * VIRTUAL_H)
            touch_fingers[event.finger_id] = {'start': (fx, fy), 'cur': (fx, fy)}
        elif event.type == pygame.FINGERMOTION:
            fx = int(event.x * VIRTUAL_W); fy = int(event.y * VIRTUAL_H)
            if event.finger_id in touch_fingers:
                data = touch_fingers[event.finger_id]; data['cur'] = (fx, fy)
                dy = data['cur'][1] - data['start'][1]
                if dy < -SWIPE_UP_THRESHOLD:
                    self.touch_jump = True
                    data['start'] = data['cur']
        elif event.type == pygame.FINGERUP:
            touch_fingers.pop(event.finger_id, None)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos): manager.push(InfoScene(self))

    def update(self):
        global water_y, camera_y, new_record
        if player.is_dead:
            save_highscore(high_scores)
            new_record = (player.score >= high_scores[difficulty] and player.score > 0)
            manager.replace(GameOverScene())
            return

        keys = pygame.key.get_pressed()
        process_touch_fingers()
        cfg  = DIFF_CONFIG[difficulty]

        player.move(keys, touch_left, touch_right, self.touch_jump)
        self.touch_jump = False

        player.score = max(player.score, int((VIRTUAL_H - 120) - player.rect.y))
        if player.score > high_scores[difficulty]: high_scores[difficulty] = player.score
        water_y -= cfg['water_speed'] + (player.score / cfg['water_speed_k'])

        if cfg['hazard'] == 'lava':
            heat_dist = water_y - player.rect.bottom
            heat_immune = (player.ability == 'heat_shield')
            if 0 < heat_dist < 80 and frame_count % 30 == 0:
                dmg = 2 if heat_immune else 5
                player.health -= dmg
                if player.health <= 0: player.health = 0; player.is_dead = True

        if player.has_magnet:
            pull_radius = 220 if player.ability == 'magnet_pull' else 200
            for pu in powerups_list:
                if not pu.collected:
                    dx   = player.rect.centerx - pu.rect.centerx
                    dy   = player.rect.centery - pu.rect.centery
                    dist = math.hypot(dx, dy)
                    if dist < pull_radius:
                        pull_rate = 0.1 if player.ability == 'magnet_pull' else 0.08
                        pu.rect.x += int(dx * pull_rate); pu.rect.y += int(dy * pull_rate)

        for plat in platforms:
            if plat.destroyed: continue
            if plat.ptype == 'phase' and plat.phase_alpha < 80: continue
            if player.rect.colliderect(plat.rect):
                if player.vel_y > 0 and player.rect.bottom <= plat.rect.top + 16:
                    is_spring = (plat.ptype == 'spring')
                    player.landed(plat.rect.top, spring=is_spring)
                    if is_spring: plat.spring_bounce = 12
                    else:         plat.stepped_on   = True
                    if plat.powerup and not plat.powerup.collected:
                        player.apply_powerup(plat.powerup.type)
                        plat.powerup.collected = True
                        spawn_particles(plat.powerup.rect.centerx, plat.powerup.rect.centery, GOLD, 15, 5)

        for pu in powerups_list:
            if not pu.collected and player.rect.colliderect(pu.rect):
                player.apply_powerup(pu.type); pu.collected = True
                spawn_particles(pu.rect.centerx, pu.rect.centery, GOLD, 15, 5)

        for e in enemies_list:
            if e.alive and player.rect.colliderect(e.rect):
                if player.ability == 'drone_crash':
                    e.alive = False
                    play(snd_crash)
                    spawn_particles(e.rect.centerx, e.rect.centery, (255, 150, 0), 16, 5)
                    trigger_shake(6)
                else:
                    player.take_hit()
                    spawn_particles(e.rect.centerx, e.rect.centery, HEALTH_RED, 8, 3)

        if player.rect.bottom >= water_y:
            if not player.has_shield:
                dmg = 3.5 if cfg['hazard'] == 'lava' else 2.2
                if player.ability == 'heat_shield' and cfg['hazard'] == 'lava': dmg *= 0.5
                player.health -= dmg
                if player.health <= 0: player.health = 0; player.is_dead = True
                if cfg['hazard'] == 'lava' and frame_count % 20 == 0: play(snd_lava)
            else:
                player.shield_timer = 0

        player_screen_y = player.rect.y - camera_y
        UPPER = int(VIRTUAL_H * 0.35)
        if player_screen_y < UPPER: camera_y += (player_screen_y - UPPER)

        build_fair_city_stairs(player.rect.y - 1500, player.score)
        cull_offscreen(camera_y)
        for plat in platforms: plat.update(frame_count)
        update_shake()

    def draw(self, surface):
        cfg = DIFF_CONFIG[difficulty]

        draw_background(surface, camera_y)

        if difficulty == DIFF_HARD:
            lava_screen_y = int(water_y - camera_y)
            if lava_screen_y < VIRTUAL_H:
                glow_h    = min(VIRTUAL_H, VIRTUAL_H - lava_screen_y + 150)
                glow_surf = pygame.Surface((VIRTUAL_W, glow_h), pygame.SRCALPHA)
                for gi in range(glow_h):
                    alpha = int(70 * (1 - gi / glow_h))
                    row   = pygame.Surface((VIRTUAL_W, 1), pygame.SRCALPHA)
                    row.fill((255, 80, 0, alpha)); glow_surf.blit(row, (0, gi))
                surface.blit(glow_surf, (0, max(0, lava_screen_y - 150)))

        draw_wind_lines(surface, frame_count)
        for plat in platforms: plat.draw(surface, camera_y, frame_count, player)
        update_particles(surface, camera_y)
        update_bullets(surface, camera_y, player)
        player.draw(surface, camera_y, frame_count)

        if cfg['hazard'] == 'lava': draw_lava(surface, water_y, camera_y, frame_count)
        else:                        draw_water(surface, water_y, camera_y, frame_count)

        draw_hud(surface, player, water_y, frame_count, high_scores)


class PauseScene:
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  manager.pop()
            elif event.key == pygame.K_m:     reset_game(); manager.replace(MenuScene())
            elif event.key == pygame.K_i:     manager.push(InfoScene(self))
            elif event.key == pygame.K_q:
                save_highscore(high_scores); save_settings(settings); pygame.quit(); sys.exit()
        if event.type == pygame.FINGERDOWN: manager.pop()

    def update(self): pass

    def draw(self, surface):
        below = manager.below
        if below: below.draw(surface)
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((6, 4, 14, 180)); surface.blit(overlay, (0, 0))
        draw_text_shadow(surface, "PAUSED", font_title, STARK_BLUE, (VIRTUAL_W // 2 - 130, VIRTUAL_H // 2 - 110))
        lines = ["ESC — Resume", "M — Main Menu", "Q — Quit Game", "F11 — Toggle Fullscreen"]
        for i, ln in enumerate(lines):
            surface.blit(font_sub.render(ln, True, WHITE), (VIRTUAL_W // 2 - 130, VIRTUAL_H // 2 + i * 38))


class GameOverScene:
    def __init__(self):
        self.newly_unlocked = []
        for i, ch in enumerate(CHARACTERS):
            if i not in unlocked_snapshot and is_character_unlocked(i):
                self.newly_unlocked.append(ch['name'])
        if self.newly_unlocked:
            play(snd_unlock)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                reset_game(); manager.replace(GameplayScene())
            elif event.key == pygame.K_m:
                reset_game(); manager.replace(MenuScene())
            elif event.key == pygame.K_i:
                manager.push(InfoScene(self))
        if event.type == pygame.FINGERDOWN:
            reset_game(); manager.replace(GameplayScene())
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos): manager.push(InfoScene(self))

    def update(self): update_shake()

    def draw(self, surface):
        draw_background(surface, camera_y)
        for plat in platforms: plat.draw(surface, camera_y, frame_count, player)
        player.draw(surface, camera_y, frame_count)
        cfg     = DIFF_CONFIG[difficulty]; is_lava = cfg['hazard'] == 'lava'
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((6, 4, 14, 210)); surface.blit(overlay, (0, 0))
        if player.rect.bottom >= water_y:
            reason = "CONSUMED BY THE VOLCANO" if is_lava else "SUBMERGED IN QUANTUM SURGE"
        else:
            reason = "TERMINATED BY KINETIC IMPACT"
        rw = font_title.size(reason)[0]
        draw_text_shadow(surface, reason, font_title,
                         (255, 80, 0) if is_lava else HEALTH_RED,
                         (VIRTUAL_W // 2 - rw // 2, VIRTUAL_H // 2 - 170))
        draw_text_shadow(surface, f"HEIGHT REACHED: {player.score // 10} m",
                         font_med, WHITE, (VIRTUAL_W // 2 - 190, VIRTUAL_H // 2 - 60))
        hs     = high_scores[difficulty]
        hs_txt = (f"  NEW RECORD ({cfg['label']}): {hs // 10} m  " if new_record
                  else f"BEST ({cfg['label']}): {hs // 10} m")
        draw_text_shadow(surface, hs_txt, font_med,
                         GOLD if new_record else WHITE,
                         (VIRTUAL_W // 2 - font_med.size(hs_txt)[0] // 2, VIRTUAL_H // 2 - 10))
        if self.newly_unlocked:
            unlock_txt = "NEW RUNNER UNLOCKED: " + ", ".join(self.newly_unlocked)
            draw_text_shadow(surface, unlock_txt, font_sub, GOLD,
                             (VIRTUAL_W // 2 - font_sub.size(unlock_txt)[0] // 2, VIRTUAL_H // 2 + 28))
        pulse = int(3 * math.sin(frame_count * 0.12))
        btn   = pygame.Rect(VIRTUAL_W // 2 - 130, VIRTUAL_H // 2 + 70 - pulse, 260, 52)
        pygame.draw.rect(surface, NEON_GREEN, btn, border_radius=10)
        pygame.draw.rect(surface, WHITE,      btn, 2, border_radius=10)
        draw_text_shadow(surface, "R — RESTART", font_sub, DARK_GREY, (btn.x + 48, btn.y + 13))
        btn2 = pygame.Rect(VIRTUAL_W // 2 - 130, VIRTUAL_H // 2 + 142, 260, 46)
        pygame.draw.rect(surface, DARK_GREY,  btn2, border_radius=10)
        pygame.draw.rect(surface, STARK_BLUE, btn2, 2, border_radius=10)
        draw_text_shadow(surface, "M — MENU", font_sub, WHITE, (btn2.x + 60, btn2.y + 11))


class InfoScene:
    def __init__(self, return_scene): self._return = return_scene

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i): manager.pop()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if info_btn_rect.collidepoint(event.pos): manager.pop()
        if event.type == pygame.FINGERDOWN: manager.pop()

    def update(self): pass

    def draw(self, surface):
        surface.fill(CITY_NIGHT)
        for b in bg_buildings_far: pygame.draw.rect(surface, b['color'], b['rect'])
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 5, 210)); surface.blit(overlay, (0, 0))
        card_w, card_h = 640, 480
        card = pygame.Rect(VIRTUAL_W // 2 - card_w // 2, VIRTUAL_H // 2 - card_h // 2, card_w, card_h)
        pygame.draw.rect(surface, (10, 16, 30), card, border_radius=16)
        pygame.draw.rect(surface, STARK_BLUE,   card, 2, border_radius=16)
        for si in range(20):
            sx    = card.x + 15 + int((si * 31) % card_w - 10)
            sy    = card.y + 15 + int((si * 19) % card_h - 10)
            alpha = int(100 + 80 * math.sin(frame_count * 0.04 + si))
            pygame.draw.circle(surface, (180, 200, 255), (sx, sy), 1)
        title = font_med.render("⚡ AVENGERS ASCENT: CITY SURGE ⚡", True, STARK_BLUE)
        surface.blit(title, (card.x + card_w // 2 - title.get_width() // 2, card.y + 22))
        pygame.draw.line(surface, STARK_BLUE, (card.x + 30, card.y + 62), (card.right - 30, card.y + 62), 1)
        eng_label = font_small.render("ENGINEER", True, (120, 120, 160))
        surface.blit(eng_label, (card.x + 40, card.y + 78))
        pulse_col = (int(180 + 75 * abs(math.sin(frame_count * 0.05))),
                     int(200 + 55 * abs(math.sin(frame_count * 0.06))), 255)
        name_txt = font_med.render("Mansy", True, pulse_col)
        surface.blit(name_txt, (card.x + 40, card.y + 96))
        badge_x = card.x + 40 + name_txt.get_width() + 16; badge_y = card.y + 100
        blink    = (frame_count // 20 % 2 == 0)
        badge_col= (0, 255, 140) if blink else (0, 180, 100)
        pygame.draw.rect(surface, badge_col, (badge_x, badge_y, 76, 20), border_radius=4)
        bl = font_tiny.render("ENGINEER", True, (0, 0, 0))
        surface.blit(bl, (badge_x + 4, badge_y + 4))
        tagline = font_tiny.render("Crafting worlds one line of code at a time  🎮", True, (140, 160, 200))
        surface.blit(tagline, (card.x + 40, card.y + 128))
        pygame.draw.line(surface, (40, 50, 70), (card.x + 30, card.y + 152), (card.right - 30, card.y + 152), 1)
        info_lines = [
            ("GAME",     "Avengers Ascent: City Surge"),
            ("VERSION",  "v5.0  —  Production Ready"),
            ("MODES",    "Easy  /  Medium  /  HARD (Volcano)"),
            ("CHARS",    "6 Playable Characters — unlock by altitude"),
            ("CONTROLS", "WASD / Arrow Keys / Touch"),
            ("POWERUPS", "Shield · Speed · Heal · Magnet"),
        ]
        for i, (lbl, val) in enumerate(info_lines):
            iy = card.y + 168 + i * 38
            pygame.draw.rect(surface, (16, 24, 40), (card.x + 30, iy, card_w - 60, 32), border_radius=5)
            lbl_s = font_tiny.render(lbl, True, (100, 120, 160))
            val_s = font_small.render(val, True, WHITE)
            surface.blit(lbl_s, (card.x + 42, iy + 4))
            surface.blit(val_s, (card.x + 130, iy + 7))
        hint = font_small.render("Press  I  or  ESC  to close", True, (80, 80, 120))
        surface.blit(hint, (card.x + card_w // 2 - hint.get_width() // 2, card.bottom - 36))
        sig = font_tiny.render("made with ♥  by  Mansy", True, (100, 100, 160))
        surface.blit(sig, (card.x + card_w // 2 - sig.get_width() // 2, card.bottom - 18))

# ─── BOOTSTRAP ────────────────────────────────────────────────
reset_game()
manager.push(SplashScene())

# ─── MAIN LOOP ────────────────────────────────────────────────
while True:
    clock.tick(FPS)
    frame_count += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_highscore(high_scores); save_settings(settings); pygame.quit(); sys.exit()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            settings["fullscreen"] = not settings.get("fullscreen", False)
            set_display(settings["fullscreen"])
            gen_buildings(); load_fonts(); save_settings(settings)

        if manager.current:
            manager.current.handle_event(event)

    if manager.current:
        manager.current.update()

    if manager.current:
        virtual_surface.fill((0, 0, 0))
        manager.current.draw(virtual_surface)

    rw, rh     = screen.get_size()
    scale      = min(rw / VIRTUAL_W, rh / VIRTUAL_H)
    new_w      = int(VIRTUAL_W * scale); new_h = int(VIRTUAL_H * scale)
    scaled     = pygame.transform.smoothscale(virtual_surface, (new_w, new_h))
    screen.fill((0, 0, 0))
    ox         = (rw - new_w) // 2 + shake_offset[0]
    oy         = (rh - new_h) // 2 + shake_offset[1]
    screen.blit(scaled, (ox, oy))

    pygame.display.flip()