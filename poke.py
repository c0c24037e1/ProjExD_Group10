# game_full.py
import pygame
import sys
import os
import time
import random
import math
from typing import Tuple, List

"""
必要画像（同フォルダ想定）
- 背景: background.png
- プレイヤー: player_down.png, player_side_left.png
- タマゴ: egg.png
- 相棒: 3.png
- ペットモード用: こうかとん/1.png, 7.png, 8.png, 9.png
- ボス: boss_yellow.png, boss_red.png, boss_white.png
- バトル背景: battle_bg.png
- バトル用プレイヤー/敵シルエット: player_poke.png, enemy_poke.png（無ければ 9.png を代替使用）
- 勝敗演出: win.png, lose.png
"""

# 実行フォルダをスクリプトの場所に固定
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ====== 定数設定 ======

MODE_TITLE  = 0
MODE_SELECT = 1
MODE_PLAY   = 2
MODE_CLEAR  = 3
# 上限（上方向の到達位置）設定
USE_MANUAL_TOP_LIMIT = False  # True: MANUAL_TOP_Y を使う / False: 背景から自動検出
MANUAL_TOP_Y = 150  # 手動で決める最小 top 座標（小さいほど上へ行ける）
TOP_LIMIT_OFFSET = -300  # 自動検出値に加えるオフセット（負でさらに上へ行ける）

WINDOW_W, WINDOW_H = 800, 600


# ====== ユーティリティ ======
def get_jp_font(size: int) -> pygame.font.Font:
    # Windowsのメジャー日本語フォントを順に当てる。なければデフォルト。
    font_paths = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/yugothb.ttf",
        "C:/Windows/Fonts/yugothm.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                pass
    return pygame.font.Font(None, size)

def draw_text(surface, text, x, y, size=28, color=(0, 0, 0)):
    font = get_jp_font(size)
    surf = font.render(text, True, color)
    surface.blit(surf, (x, y))

def scale_img(img: pygame.Surface, s: float) -> pygame.Surface:
    w, h = img.get_size()
    return pygame.transform.scale(img, (int(w * s), int(h * s)))

def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """背景から歩行可能上限を自動検出（中央帯の同色行を走査）"""
    cx = bg_surf.get_rect().centerx
    w, h = bg_surf.get_width(), bg_surf.get_height()
    sample_y = int(h * 0.65)
    floor_color = bg_surf.get_at((min(max(cx, 0), w - 1), min(max(sample_y, 0), h - 1)))
    band = range(max(0, cx - 6), min(w, cx + 7))
    for y in range(0, sample_y + 1):
        if any(bg_surf.get_at((x, y)) == floor_color for x in band):
            return y + 2

    # 見つからなければ 0 付近を返す（安全側）
    return 2

def _lerp(a, b, t):
    return a + (b - a) * t

def _dir(a, b):
    ax, ay = a; bx, by = b
    dx, dy = (bx - ax, by - ay)
    d = max(1.0, math.hypot(dx, dy))
    return (dx / d, dy / d), d


# ====== ダメージ浮遊テキスト ======
class FloatingNumber:
    def __init__(self, text: str, pos: Tuple[int, int], vy: float = -1.0, ttl: int = 60):
        self.text = text
        self.x, self.y = pos
        self.vy = vy
        self.ttl = ttl
        self.alpha = 255

    def update(self) -> bool:
        self.y += self.vy
        self.ttl -= 1
        if self.ttl < 20:
            self.alpha = int(255 * (self.ttl / 20))
        return self.ttl > 0

    def draw(self, screen):
        font = get_jp_font(36)
        surf = font.render(self.text, True, (255, 255, 0))
        surf.set_alpha(self.alpha)
        screen.blit(surf, (self.x, self.y))


# ====== プレイヤー ======
class Player:
    def __init__(self, bg_rect: pygame.Rect):
        self.down_img = pygame.image.load("player_down.png").convert_alpha()
        self.left_img = pygame.image.load("player_side_left.png").convert_alpha()
        self.right_img = pygame.transform.flip(self.left_img, True, False)

        player_scale = 0.1
        pw, ph = self.down_img.get_size()
        new_size = (int(pw * player_scale), int(ph * player_scale))
        self.down_img  = pygame.transform.scale(self.down_img, new_size)
        self.left_img  = pygame.transform.scale(self.left_img, new_size)
        self.right_img = pygame.transform.scale(self.right_img, new_size)

        self.image = self.down_img
        self.rect = self.image.get_rect(topleft=(465, 600))
        self.bg_rect = bg_rect

    def update(self, keys, top_limit: int):
        dx = dy = 0
        speed = 4
        if keys[pygame.K_LEFT]:
            dx = -speed
            self.image = self.left_img
        elif keys[pygame.K_RIGHT]:
            dx = speed
            self.image = self.right_img
        elif keys[pygame.K_UP]:
            dy = -speed
            self.image = self.down_img
        elif keys[pygame.K_DOWN]:
            dy = speed
            self.image = self.down_img

        self.rect.x += dx
        self.rect.y += dy
        self.rect.clamp_ip(self.bg_rect)
        if self.rect.top < top_limit:
            self.rect.top = top_limit

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, self.rect)


# ====== タマゴ ======
class Egg:
    def __init__(self, bg_rect: pygame.Rect):
        egg_img = pygame.image.load("egg.png").convert_alpha()
        egg_scale = 0.35
        ew, eh = egg_img.get_size()
        egg_img = pygame.transform.scale(egg_img, (int(ew * egg_scale), int(eh * egg_scale)))
        self.image = egg_img
        self.rect = self.image.get_rect(center=bg_rect.center)

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, self.rect)


# ====== 相棒（セレクト/クリア演出用） ======
class Partner:
    def __init__(self, name: str):
        img = pygame.image.load("3.png").convert_alpha()
        img = scale_img(img, 5)
        self.image = img
        self.name = name

    def draw_center(self, screen: pygame.Surface, center_pos):
        rect = self.image.get_rect(center=center_pos)
        screen.blit(self.image, rect)

    def draw_midbottom(self, screen: pygame.Surface, midbottom_pos):
        rect = self.image.get_rect()
        rect.midbottom = midbottom_pos
        screen.blit(self.image, rect)


# ====== ボス ======
class Boss:
    def __init__(self, name: str, img_path: str, type_: str, scale: float, x: int, y: int):
        self.name = name
        self.type = type_
        img = pygame.image.load(img_path).convert_alpha()
        self.image = scale_img(img, scale)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.alive = True

    def draw(self, screen: pygame.Surface):
        if self.alive:
            screen.blit(self.image, self.rect)

class BossGroup:
    def __init__(self):
        self.bosses: List[Boss] = [
            Boss("イエローボス", "boss_yellow.png", "でんき", 0.2, 200, 200),
            Boss("レッドボス",   "boss_red.png",    "ほのお", 0.2, 400, 200),
            Boss("ブルーボス",   "boss_white.png",  "みず",   0.18, 600, 180),
        ]

    def draw(self, screen: pygame.Surface):
        for b in self.bosses:
            b.draw(screen)

    def alive_collision_with(self, rect: pygame.Rect):
        for b in self.bosses:
            if b.alive and rect.colliderect(b.rect):
                return b
        return None

    def any_alive(self) -> bool:
        return any(b.alive for b in self.bosses)


# ====== ペット（ふれあい）シーン ======
class PetScene:
    def __init__(self, folder: str, screen: pygame.Surface):
        self.screen = screen
        self.folder = folder
        self.state = "normal"
        self.last_q_press_time = 0
        self.action_start_time = 0
        self.font = get_jp_font(28)
        self.images = {
            "normal": pygame.image.load(os.path.join(folder, "1.png")).convert_alpha(),
            "pet": pygame.image.load(os.path.join(folder, "9.png")).convert_alpha(),
            "hit": pygame.image.load(os.path.join(folder, "7.png")).convert_alpha(),
            "hit_strong": pygame.image.load(os.path.join(folder, "8.png")).convert_alpha(),
        }

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                self.state = "pet"
                self.action_start_time = time.time()
            elif event.key == pygame.K_q:
                now = time.time()
                if now - self.last_q_press_time < 0.4:
                    self.state = "hit_strong"
                else:
                    self.state = "hit"
                self.last_q_press_time = now
                self.action_start_time = now

    def update(self):
        if self.state != "normal" and time.time() - self.action_start_time > 3:
            self.state = "normal"

    def draw(self):
        screen = self.screen
        screen.fill((255, 200, 220))
        sw, sh = screen.get_size()
        pet_img = self.images[self.state]
        ih, iw = pet_img.get_height(), pet_img.get_width()
        scale_factor = (sh * 0.6) / ih
        scaled = pygame.transform.scale(pet_img, (int(iw * scale_factor), int(ih * scale_factor)))
        rect = scaled.get_rect(center=(sw // 2, sh // 2))
        screen.blit(scaled, rect)
        msg1 = self.font.render("A：なでる", True, (100, 0, 50))
        msg2 = self.font.render("Q：なぐる（連打で強）", True, (100, 0, 50))
        msg3 = self.font.render("F：もどる", True, (100, 0, 50))
        screen.blit(msg1, (sw - msg1.get_width() - 20, 20))
        screen.blit(msg2, (sw - msg2.get_width() - 20, 60))
        screen.blit(msg3, (sw - msg3.get_width() - 20, 100))


# ====== バトル相性 ======
def get_type_multiplier(move_type: str, target_type: str) -> float:
    advantage = {
        "ほのお": {"みず": 0.5, "くさ": 2.0, "でんき": 1.0},
        "みず": {"ほのお": 2.0, "でんき": 0.5, "くさ": 0.5},
        "でんき": {"みず": 2.0, "ほのお": 1.0, "くさ": 1.0},
        "くさ": {"みず": 2.0, "ほのお": 0.5, "でんき": 1.0},
        "ノーマル": {},
    }
    if move_type in advantage and target_type in advantage[move_type]:
        return advantage[move_type][target_type]
    return 1.0


# ====== バトルエフェクト（下コードを統合） ======
class EffectBase:
    def __init__(self):
        self.alive = True
    def update(self) -> bool:
        return self.alive
    def draw(self, surf):
        pass

class TackleEffect(EffectBase):
    """たいあたり：攻撃側Rectを突進→戻す"""
    def __init__(self, attacker_rect, src_pos, dst_center, frames=10):
        super().__init__()
        self.attacker_rect = attacker_rect
        self.start_pos = src_pos
        self.target_pos = (dst_center[0] - attacker_rect.width / 2,
                           dst_center[1] - attacker_rect.height / 2)
        self.f = 0
        self.frames_one_way = max(1, frames)
        self.frames_total = self.frames_one_way * 2
    def update(self):
        self.f += 1
        if self.f <= self.frames_one_way:
            t = math.sin((self.f / self.frames_one_way) * (math.pi / 2))
            x = _lerp(self.start_pos[0], self.target_pos[0], t)
            y = _lerp(self.start_pos[1], self.target_pos[1], t)
            self.attacker_rect.topleft = (int(x), int(y))
        elif self.f <= self.frames_total:
            t = (self.f - self.frames_one_way) / self.frames_one_way
            x = _lerp(self.target_pos[0], self.start_pos[0], t)
            y = _lerp(self.target_pos[1], self.start_pos[1], t)
            self.attacker_rect.topleft = (int(x), int(y))
        else:
            self.attacker_rect.topleft = self.start_pos
            self.alive = False
        return self.alive

class QuickAttackEffect(EffectBase):
    """でんこうせっか：ジグザグ線を複数本"""
    def __init__(self, src, dst, frames=20):
        super().__init__()
        self.src, self.dst = src, dst
        self.f, self.frames = 0, frames
        self.paths = []
    def update(self):
        self.f += 1
        if self.f > self.frames:
            self.alive = False
        else:
            self.paths = []
            for _ in range(3):
                pts = []
                for i in range(6):
                    t = i / 5
                    x = _lerp(self.src[0], self.dst[0], t)
                    y = _lerp(self.src[1], self.dst[1], t) + random.randint(-10, 10)
                    pts.append((x, y))
                self.paths.append(pts)
        return self.alive
    def draw(self, surf):
        for pts in self.paths:
            pygame.draw.lines(surf, (255, 255, 100), False, pts, 4)
            pygame.draw.lines(surf, (255, 255, 255), False, pts, 2)

class FlamethrowerEffect(EffectBase):
    """かえんほうしゃ：炎→煙のパーティクル"""
    def __init__(self, src, dst, frames=40):
        super().__init__()
        self.src, self.dst = src, dst
        self.f, self.frames = 0, frames
        self.flames = []
        self.smoke = []
        self._spawn(25)
    def _spawn(self, n):
        (ux, uy), _ = _dir(self.src, self.dst)
        base = math.atan2(uy, ux)
        for _ in range(n):
            ang = base + random.uniform(-0.4, 0.4)
            spd = random.uniform(4, 8)
            vx, vy = math.cos(ang) * spd, math.sin(ang) * spd
            life = random.randint(20, 35)
            self.flames.append([self.src[0], self.src[1], vx, vy, life])
    def update(self):
        self.f += 1
        if self.f <= self.frames and self.f % 2 == 0:
            self._spawn(5)
        new_flames, new_smoke = [], []
        for p in self.flames:
            p[0] += p[2]; p[1] += p[3]
            p[3] += 0.05
            p[4] -= 1
            if p[4] > 0:
                new_flames.append(p)
            else:
                new_smoke.append([p[0], p[1], random.uniform(-0.5, 0.5), -1.0, 40])
        self.flames = new_flames
        self.smoke = self.smoke + new_smoke
        self.smoke = [s for s in self.smoke if s[4] > 0]
        for s in self.smoke:
            s[0] += s[2]; s[1] += s[3]
            s[4] -= 1
        if self.f > self.frames and not self.flames and not self.smoke:
            self.alive = False
        return self.alive
    def draw(self, surf):
        for x, y, _, _, life in self.flames:
            col = (255, random.randint(100, 200), random.randint(30, 60))
            r = max(2, int(6 * (life / 35)))
            pygame.draw.circle(surf, col, (int(x), int(y)), r)
        for x, y, _, _, life in self.smoke:
            alpha = int(180 * (life / 40))
            r = int(8 * (life / 40))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (80, 80, 80, alpha), (r, r), r)
            surf.blit(s, (x - r, y - r))

class WaterGunEffect(EffectBase):
    """みずでっぽう：水流の線＋水しぶき"""
    def __init__(self, src, dst, frames=45):
        super().__init__()
        self.src, self.dst, self.f, self.frames = src, dst, 0, frames
        self.drops = []
    def update(self):
        self.f += 1
        (ux, uy), dist = _dir(self.src, self.dst)
        if self.f <= self.frames:
            for _ in range(8):
                rand_dist = random.uniform(0, dist)
                px = self.src[0] + ux * rand_dist
                py = self.src[1] + uy * rand_dist
                vx = ux * random.uniform(3, 5) + random.uniform(-0.8, 0.8)
                vy = uy * random.uniform(3, 5) + random.uniform(-0.8, 0.8)
                life = random.randint(10, 25)
                self.drops.append([px, py, vx, vy, life])
        self.drops = [[x + vx, y + vy, vx, vy, life - 1]
                      for x, y, vx, vy, life in self.drops if life > 1]
        if self.f > self.frames and not self.drops:
            self.alive = False
        return self.alive
    def draw(self, surf):
        pygame.draw.line(surf, (100, 200, 255), self.src, self.dst, 10)
        pygame.draw.line(surf, (220, 245, 255), self.src, self.dst, 4)
        for x, y, _, _, life in self.drops:
            r = max(1, int(3 * (life / 20)))
            pygame.draw.circle(surf, (170, 220, 255), (int(x), int(y)), r)


# ====== 統合版バトルシーン ======
def _load_battle_images():
    # battle_bg
    try:
        bg = pygame.image.load("battle_bg.png").convert()
    except:
        bg = pygame.Surface((WINDOW_W, WINDOW_H)).convert()
        bg.fill((200, 220, 240))

    # player_poke / enemy_poke
    def _try_load(*candidates):
        for path in candidates:
            if os.path.exists(path):
                try:
                    return pygame.image.load(path).convert_alpha()
                except:
                    pass
        # フォールバック：適当な円
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.circle(surf, (80, 80, 80, 200), (100, 100), 100)
        return surf

    player_poke = _try_load("player_poke.png", "9.png")
    enemy_poke  = _try_load("enemy.png",  "9.png")
    return bg, player_poke, enemy_poke

def battle_scene(screen, enemy_name: str, enemy_type: str) -> str:
    """タイプ相性＋高品質エフェクト統合版のバトル"""
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # --- アセット読み込み ---
    raw_bg, raw_player, raw_enemy = _load_battle_images()
    bg = pygame.transform.scale(raw_bg, (W, H))
    player_img = pygame.transform.scale(raw_player, (200, 200))
    enemy_img = pygame.transform.scale(raw_enemy, (200, 200))

    player_rect = player_img.get_rect(bottomleft=(200, H - 50))
    enemy_rect = enemy_img.get_rect(topleft=(W - 300, 120))

    effects: List[EffectBase] = []
    floating: List[FloatingNumber] = []

    player_hp, enemy_hp = 100, 100

    # 技：名前, 基本威力, タイプ, エフェクト種別
    # エフェクト種別: "tackle", "quick", "flame", "water"
    commands = [
        ("たいあたり",   10, "ノーマル", "tackle"),
        ("かえんほうしゃ", 25, "ほのお",   "flame"),
        ("でんこうせっか", 18, "でんき",   "quick"),
        ("みずでっぽう",   20, "みず",     "water"),
    ]
    selected = 0
    turn = "player"
    message = f"{enemy_name}（{enemy_type}） が あらわれた！"
    effect_text = None
    effect_timer = 0

    while True:
        # --- イベント ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and turn == "player":
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(commands)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(commands)
                elif event.key == pygame.K_RETURN:
                    move, base, mtype, kind = commands[selected]
                    mult = get_type_multiplier(mtype, enemy_type)
                    dmg = int(base * mult)

                    # エフェクト生成
                    if kind == "tackle":
                        effects.append(TackleEffect(player_rect, player_rect.topleft, enemy_rect.center, frames=10))
                    else:
                        src = (player_rect.right - 20, player_rect.top + 40)
                        dst = (enemy_rect.left + 20, enemy_rect.top + 40)
                        if kind == "quick":
                            effects.append(QuickAttackEffect(src, dst))
                        elif kind == "flame":
                            effects.append(FlamethrowerEffect(src, dst))
                        elif kind == "water":
                            effects.append(WaterGunEffect(src, dst))

                    # ダメージ＆演出
                    enemy_hp -= dmg
                    floating.append(FloatingNumber(str(dmg), enemy_rect.midtop))
                    if mult > 1:
                        effect_text = "こうかは ばつぐんだ！"
                        effect_timer = 60
                    elif mult < 1:
                        effect_text = "こうかは いまひとつだ…"
                        effect_timer = 60
                    else:
                        effect_text = None
                    message = f"{move}（{mtype}）！ {dmg}ダメージ！"

                    if enemy_hp <= 0:
                        return "win"
                    turn = "enemy"

        # --- 敵ターン ---
        if turn == "enemy":
            pygame.time.delay(600)
            dmg = random.randint(8, 22)
            player_hp -= dmg
            message = f"{enemy_name} の こうげき！ {dmg}ダメージ！"
            floating.append(FloatingNumber(str(dmg), player_rect.midtop))
            if player_hp <= 0:
                return "lose"
            turn = "player"

        # --- 更新 ---
        floating = [f for f in floating if f.update()]
        effects = [e for e in effects if e.update()]
        if effect_text:
            effect_timer -= 1
            if effect_timer <= 0:
                effect_text = None

        # --- 描画 ---
        temp = pygame.Surface((W, H), pygame.SRCALPHA)
        temp.blit(bg, (0, 0))

        # キャラ
        temp.blit(player_img, player_rect)
        temp.blit(enemy_img, enemy_rect)

        # HPバー
        pygame.draw.rect(temp, (255, 0, 0), (80,  H - 260, max(0, player_hp * 2), 20))
        pygame.draw.rect(temp, (255, 0, 0), (W - 300, 80,   max(0, enemy_hp * 2), 20))

        # メッセージ
        draw_text(temp, message, 80, H - 180, 26)

        # コマンド
        if turn == "player":
            for i, (cmd, _, t, _) in enumerate(commands):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                draw_text(temp, f"{cmd}（{t}）", 100, H - 150 + i * 28, 24, color)

        # 浮遊ダメージ・エフェクト
        for f in floating: f.draw(temp)
        for ef in effects: ef.draw(temp)

        # 効果テキスト
        if effect_text:
            draw_text(temp, effect_text, W // 2 - 140, 140, 40, (255, 255, 0))

        screen.blit(temp, (0, 0))
        pygame.display.flip()
        clock.tick(60)


# ====== 勝敗演出（上コードの画像版を採用） ======
def show_result(screen, result: str):
    W, H = screen.get_size()
    path = "win.png" if result == "win" else "lose.png"
    if os.path.exists(path):
        img = pygame.transform.scale(pygame.image.load(path), (W, H))
    else:
        # フォールバック：色背景
        img = pygame.Surface((W, H))
        img.fill((30, 160, 80) if result == "win" else (160, 40, 40))

    clock = pygame.time.Clock()

    if result == "win":
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < 2000:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
            screen.blit(img, (0, 0))
            draw_text(screen, "WIN!", W//2 - 60, H - 100, 40, (255, 255, 255))
            pygame.display.flip()
            clock.tick(30)
        return

    # lose時はEnterで戻る
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return
        screen.blit(img, (0, 0))
        draw_text(screen, "Enterで戻る", W//2 - 100, H - 100, 30, (255, 255, 255))
        pygame.display.flip()
        clock.tick(30)

# ===========================
# モンスタークラス（仮実装）
# ===========================

class Monster:
    def __init__(self, name, max_hp):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.status = None  # None, "Poison", "Paralysis", など

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.max_hp)

    def status_heal(self):
        self.status = None


# ===========================
# インベントリークラス
# ===========================
class Inventory:
    """
    Bキーを押すとインベントリ画面が開き、バッグ、キーアイテム、モンスターの3つのタブが出てくる。
    ポーションを選択すると回復、解毒、異常状態回復の3つが選べ、使う事でその効果をモンスターに与える事ができる。
    モンスタータブではモンスターのHPや状態を確認する事ができる。
    """

    def __init__(self, screen: pygame.Surface, monster: Monster) -> None:
        self.screen = screen
        self.monster = monster

        self.bg_img = pygame.image.load("インベントリ背景画像.png").convert()
        self.bg_img = pygame.transform.scale(self.bg_img, (800, 600))
        self.bg_rect = self.bg_img.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

        self.font_tab = pygame.font.Font(None, 50)
        self.font_item = pygame.font.Font(None, 40)

        self.tabs = ["Bag", "Key Items", "Monster"]
        self.items = {
            "Bag": ["Potion", "Items"],
            "Key Items": ["Bicycle", "Map", "Coin"]
        }

        self.current_tab = 0
        self.cursor = 0

    # ==== 共通：メッセージ表示関数 ====
    def show_message(self, text: str, delay=800):
        """中央下に小さめの黒背景＋白文字でメッセージを表示"""
        # 背景サイズ（画面幅の7割、縦100px程度）
        msg_width = int(self.screen.get_width() * 0.7)
        msg_height = 100

        # 背景の位置（画面中央）
        msg_x = (self.screen.get_width() - msg_width) // 2
        msg_y = (self.screen.get_height() - msg_height) // 2

        # 半透明黒背景を作成（より黒く、透明度220/255）
        overlay = pygame.Surface((msg_width, msg_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))  # ← 透明度を上げることでより黒く

        # テキストを白で描画
        font = pygame.font.Font(None, 36)
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(msg_width // 2, msg_height // 2))

        # 背景を描画
        self.screen.blit(overlay, (msg_x, msg_y))
        self.screen.blit(text_surface, (msg_x + text_rect.x, msg_y + text_rect.y))

        pygame.display.flip()
        pygame.time.delay(delay)


    def open(self) -> None:
        """インベントリ画面を開く"""
        pygame.mixer.music.play(loops = -1)
        while True:
            self.draw()
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_b, pygame.K_ESCAPE]:
                        pygame.mixer.music.stop()
                        return
                    elif event.key == pygame.K_RIGHT:
                        self.current_tab = (self.current_tab + 1) % len(self.tabs)
                        self.cursor = 0
                    elif event.key == pygame.K_LEFT:
                        self.current_tab = (self.current_tab - 1) % len(self.tabs)
                        self.cursor = 0
                    elif event.key == pygame.K_DOWN:
                        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
                            current_items = self.items[self.tabs[self.current_tab]]
                            if len(current_items) > 1:
                                self.cursor = (self.cursor + 1) % len(current_items)
                    elif event.key == pygame.K_UP:
                        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
                            current_items = self.items[self.tabs[self.current_tab]]
                            if len(current_items) > 1:
                                self.cursor = (self.cursor - 1) % len(current_items)
                    elif event.key == pygame.K_RETURN:
                        self.select_item()

    def draw(self) -> None:
        """インベントリの描画"""
        self.screen.blit(self.bg_img, self.bg_rect.topleft)

        # タブ描画
        for i, tab in enumerate(self.tabs):
            color = (255, 255, 0) if i == self.current_tab else (200, 200, 200)
            tab_text = self.font_tab.render(tab, True, color)
            tab_x = self.bg_rect.left + 50 + i * 200
            tab_y = self.bg_rect.top + 20
            self.screen.blit(tab_text, (tab_x, tab_y))

        # アイテム描画
        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
            current_items = self.items[self.tabs[self.current_tab]]
            for i, item in enumerate(current_items):
                color = (255, 255, 255) if i == self.cursor else (150, 150, 150)
                item_text = self.font_item.render(item, True, color)
                self.screen.blit(item_text, (self.bg_rect.left + 100, self.bg_rect.top + 100 + i * 50))

        elif self.tabs[self.current_tab] == "Monster":
            m = self.monster
            color = (255, 255, 255)
            self.screen.blit(self.font_item.render(f"HP: {m.hp}/{m.max_hp}", True, color),
                             (self.bg_rect.left + 50, self.bg_rect.top + 130))
            self.screen.blit(self.font_item.render(f"Status: {m.status if m.status else 'Normal'}", True, color),
                             (self.bg_rect.left + 50, self.bg_rect.top + 160))

    def select_item(self) -> None:
        """選択中のアイテムを使用"""
        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
            current_items = self.items[self.tabs[self.current_tab]]
            selected_item = current_items[self.cursor]
            if selected_item == "Potion":
                self.potion_select()
            else:
                self.draw()
                self.show_message(f"{selected_item} is not implemented yet!", delay=800)

    def potion_select(self) -> None:
        """ポーション選択と使用（ESC/Bで一段階戻る）"""
        potions = ["Heal Potion", "Antidote", "Status Heal"]
        cursor = 0
        font = pygame.font.Font(None, 40)

        while True:
            self.screen.blit(self.bg_img, self.bg_rect.topleft)
            self.draw()

            for i, potion in enumerate(potions):
                color = (255, 255, 255) if i == cursor else (150, 150, 150)
                self.screen.blit(font.render(potion, True, color),
                                 (self.bg_rect.left + 300, self.bg_rect.top + 100 + i * 50))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_b]:
                        return
                    elif event.key == pygame.K_RETURN:
                        potion_name = potions[cursor]
                        if potion_name == "Heal Potion":
                            self.monster.heal(50)
                        elif potion_name == "Antidote":
                            if self.monster.status == "Poison":
                                self.monster.status_heal()
                        elif potion_name == "Status Heal":
                            self.monster.status_heal()
                        self.draw()
                        self.show_message(f"Used {potion_name}", delay=800)
                        return
                    elif event.key == pygame.K_UP:
                        cursor = (cursor - 1) % len(potions)
                    elif event.key == pygame.K_DOWN:
                        cursor = (cursor + 1) % len(potions)


# ====== ゲーム全体（上コードをベースに統合） ======
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("ポケットコウカトン")
        self.clock = pygame.time.Clock()

        self.monster = Monster("こうかとん", 100)
        self.monster.status = "Poison"
        self.inventory = Inventory(self.screen, self.monster)
        pygame.mixer.music.load("poke_center.wav")  # BGMファイル読み込み

        # 状態
        self.mode = MODE_TITLE
        self.egg_phase = 0
        self.pink_mode = False

        # 背景
        self.bg_img = pygame.image.load("background.png").convert()
        self.bg_rect = self.bg_img.get_rect()

        # 各キャラ/シーン
        self.player = Player(self.bg_rect)
        self.egg = Egg(self.bg_rect)
        self.partner = Partner("Koukaton")
        self.bosses = BossGroup()
        self.pet_scene = PetScene("こうかとん", self.screen)

        # 上限判定
        if USE_MANUAL_TOP_LIMIT:
            self.top_limit = MANUAL_TOP_Y
        else:
            auto_top = detect_top_walkable_y(self.bg_img)
            self.top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

    def run(self):
        while True:# 以下追加コード
            self.handle_events()
            if self.pink_mode:
                self.pet_scene.update()
                self.pet_scene.draw()
            else:
                self.update()
                self.draw()
            pygame.display.flip()
            self.clock.tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                # ペットモード切替（どのモードからでも）
                if event.key == pygame.K_f:
                    self.pink_mode = not self.pink_mode
                    continue

                # Bキーでインベントリを開く
                if event.type == pygame.KEYDOWN and event.key == pygame.K_b:
                    self.inventory.open()

                # ペットモード中の操作
                if self.pink_mode:
                    self.pet_scene.handle_event(event)
                    continue

                # 各モードのハンドリング
                if self.mode == MODE_TITLE:
                    if event.key == pygame.K_RETURN:
                        self.mode = MODE_SELECT

                elif self.mode == MODE_SELECT:
                    if event.key == pygame.K_RETURN:
                        if self.egg_phase == 0:
                            self.egg_phase = 1  # 孵化
                        else:
                            self.mode = MODE_PLAY

                elif self.mode == MODE_CLEAR:
                    if event.key == pygame.K_RETURN:
                        pygame.quit(); sys.exit()

    def update(self):
        if self.mode == MODE_PLAY:
            keys = pygame.key.get_pressed()
            self.player.update(keys, self.top_limit)

            # ボス衝突でバトル開始（→統合版battle_scene使用）
            collided = self.bosses.alive_collision_with(self.player.rect)
            if collided:
                result = battle_scene(self.screen, collided.name, collided.type)
                show_result(self.screen, result)
                if result == "win":
                    # 勝利 → 該当ボス撃破 → クリア画面へ（仕様：ボス倒したら終了）
                    collided.alive = False
                    self.mode = MODE_CLEAR
                else:
                    # 敗北 → マップに戻り、プレイヤー初期位置へ
                    self.player.rect.topleft = (465, 600)

    def draw(self):
        if self.mode == MODE_TITLE:
            self.draw_title()
        elif self.mode == MODE_SELECT:
            self.draw_select()
        elif self.mode == MODE_PLAY:
            self.draw_play()
        elif self.mode == MODE_CLEAR:
            self.draw_clear()

    def draw_title(self):
        self.screen.fill((0, 0, 0))
        t1 = get_jp_font(64).render("The Chamber of Beginnings", True, (255, 255, 0))
        t2 = get_jp_font(40).render("Press ENTER", True, (255, 255, 255))
        t3 = get_jp_font(28).render("A mysterious egg awaits...", True, (180, 180, 180))
        cx = WINDOW_W // 2
        self.screen.blit(t1, (cx - t1.get_width()//2, 200))
        self.screen.blit(t2, (cx - t2.get_width()//2, 280))
        self.screen.blit(t3, (cx - t3.get_width()//2, 330))

    def draw_select(self):
        self.screen.fill((10, 10, 30))
        cx, cy = WINDOW_W // 2, WINDOW_H // 2
        if self.egg_phase == 0:
            title = get_jp_font(40).render("A mysterious egg appeared...", True, (255, 255, 255))
            self.screen.blit(title, (cx - title.get_width()//2, 80))
            self.egg.draw(self.screen)
            guide = get_jp_font(28).render("Press ENTER to hatch the egg!", True, (255, 255, 255))
            self.screen.blit(guide, (cx - guide.get_width()//2, WINDOW_H - 100))
        else:
            title = get_jp_font(40).render("The egg hatched!", True, (255, 255, 255))
            self.screen.blit(title, (cx - title.get_width()//2, 60))
            sub = get_jp_font(28).render(f"Your partner is {self.partner.name}.", True, (255, 215, 0))
            self.screen.blit(sub, (cx - sub.get_width()//2, 110))
            self.partner.draw_center(self.screen, (cx, cy + 40))
            guide = get_jp_font(28).render("Press ENTER to start your journey!", True, (255, 255, 255))
            self.screen.blit(guide, (cx - guide.get_width()//2, WINDOW_H - 100))

    def draw_play(self):
        # 背景は画面に合わせてスケールして描画
        bg_scaled = pygame.transform.scale(self.bg_img, (WINDOW_W, WINDOW_H))
        self.screen.blit(bg_scaled, (0, 0))
        self.bosses.draw(self.screen)
        self.player.draw(self.screen)
        info = get_jp_font(24).render("F: ペットモード / ボスに触れるとバトル", True, (255, 255, 0))
        self.screen.blit(info, (10, 10))

    def draw_clear(self):
        self.screen.fill((20, 80, 90))
        cx, cy = WINDOW_W // 2, WINDOW_H // 2
        pygame.draw.polygon(self.screen, (255, 255, 255), [(cx - 80, 0), (cx - 20, 0), (cx + 40, cy)])
        pygame.draw.polygon(self.screen, (255, 255, 255), [(cx + 80, 0), (cx + 20, 0), (cx - 40, cy)])
        star_color = (255, 255, 200)
        for (sx, sy) in [(200,200),(300,150),(500,180),(600,240),(250,260),(450,120)]:
            pygame.draw.circle(self.screen, star_color, (sx, sy), 4)
            pygame.draw.circle(self.screen, star_color, (sx+8, sy+4), 2)
        line_top = get_jp_font(48).render("You are the Champion.", True, (255, 215, 0))
        self.screen.blit(line_top, (cx - line_top.get_width()//2, 80))
        line_name = get_jp_font(28).render(f"Your partner is {self.partner.name}!", True, (255, 255, 255))
        self.screen.blit(line_name, (cx - line_name.get_width()//2, 130))
        party_y = cy + 40
        self.partner.draw_midbottom(self.screen, (cx - 80, party_y))
        hero_rect = self.player.image.get_rect()
        hero_rect.midbottom = (cx + 40, party_y)
        self.screen.blit(self.player.image, hero_rect)
        line_press = get_jp_font(36).render("Press ENTER to finish", True, (255, 255, 255))
        self.screen.blit(line_press, (cx - line_press.get_width()//2, party_y + 40))

# ===== 実行部分 =====
if __name__ == "__main__":
    
    Game().run()
    