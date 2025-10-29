import pygame
import sys
import os
import random
from typing import List, Dict

# 実行時にスクリプトのあるディレクトリをカレントに変更
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ===== 定数設定 =====
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300


def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    cx = bg_surf.get_rect().centerx
    h = bg_surf.get_height()
    sample_y = int(h * 0.65)
    floor_color = bg_surf.get_at((cx, sample_y))
    band = range(max(0, cx - 6), min(bg_surf.get_width(), cx + 7))
    for y in range(0, sample_y + 1):
        is_floor_row = any(bg_surf.get_at((x, y)) == floor_color for x in band)
        if is_floor_row:
            return y + 2
    return 2


def get_jp_font(size: int) -> pygame.font.Font:
    font_paths = [
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_text(screen: pygame.Surface, text: str, x: int, y: int, size: int = 36, color=(0, 0, 0)) -> None:
    font = get_jp_font(size)
    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))


class FloatingNumber:
    def __init__(self, text: str, x: int, y: int, vy: float = -1.0, ttl: int = 60):
        self.text = text
        self.x = x
        self.y = y
        self.vy = vy
        self.ttl = ttl
        self.alpha = 255

    def update(self) -> bool:
        self.y += self.vy
        self.ttl -= 1
        if self.ttl < 20:
            self.alpha = int(255 * (self.ttl / 20))
        return self.ttl > 0

    def draw(self, screen: pygame.Surface) -> None:
        font = get_jp_font(36)
        surf = font.render(self.text, True, (255, 255, 0))
        surf.set_alpha(self.alpha)
        screen.blit(surf, (self.x, self.y))


def battle_scene(screen: pygame.Surface, enemy_name: str = "ボス", debug: bool = False) -> str:
    clock = pygame.time.Clock()
    W, H = 800, 600

    bg_battle = pygame.image.load("battle_bg.png").convert()
    bg_battle = pygame.transform.scale(bg_battle, (W, H))

    player_poke = pygame.image.load("player_poke.png").convert_alpha()
    enemy_poke = pygame.image.load("boss_red.png").convert_alpha()
    player_poke = pygame.transform.scale(player_poke, (200, 200))
    enemy_poke = pygame.transform.scale(enemy_poke, (200, 200))
    player_rect = player_poke.get_rect(bottomleft=(200, 550))
    enemy_rect = enemy_poke.get_rect(topleft=(500, 150))

    player_hp = 100
    enemy_hp = 100

    commands = [
        ("たいあたり", 10),
        ("かえんほうしゃ", 25),
        ("でんこうせっか", 15),
        ("みずでっぽう", 20)
    ]
    selected = 0
    turn = "player"
    message = f"{enemy_name} が あらわれた！"

    floating: List[FloatingNumber] = []
    shake_timer = 0
    shake_magnitude = 0

    def start_shake(duration_frames=12, magnitude=6):
        nonlocal shake_timer, shake_magnitude
        shake_timer = duration_frames
        shake_magnitude = magnitude

    def get_shake_offset() -> tuple[int, int]:
        nonlocal shake_timer
        if shake_timer > 0:
            sx = random.randint(-shake_magnitude, shake_magnitude)
            sy = random.randint(-shake_magnitude, shake_magnitude)
            return sx, sy
        return 0, 0

    # ===== メインバトルループ =====
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if turn == "player":
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(commands)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(commands)
                    elif event.key == pygame.K_RETURN:
                        move, dmg = commands[selected]
                        enemy_hp -= dmg
                        message = f"{move}！ {dmg} ダメージ！"
                        fx = enemy_rect.centerx - 10 + random.randint(-8, 8)
                        fy = enemy_rect.top - 10 + random.randint(-6, 6)
                        floating.append(FloatingNumber(str(dmg), fx, fy))
                        start_shake(12, 6)
                        if enemy_hp <= 0:
                            return "win"
                        turn = "enemy"

        if turn == "enemy":
            pygame.time.delay(600)
            dmg = random.randint(8, 22)
            player_hp -= dmg
            message = f"{enemy_name} の こうげき！ {dmg} ダメージ！"
            fx = player_rect.centerx - 10 + random.randint(-8, 8)
            fy = player_rect.top - 10 + random.randint(-6, 6)
            floating.append(FloatingNumber(str(dmg), fx, fy))
            start_shake(12, 6)
            if player_hp <= 0:
                return "lose"
            turn = "player"

        floating = [f for f in floating if f.update()]
        if shake_timer > 0:
            shake_timer -= 1
            if shake_timer == 0:
                shake_magnitude = 0

        sx, sy = get_shake_offset()
        temp = pygame.Surface((W, H))
        temp.blit(bg_battle, (0, 0))
        temp.blit(player_poke, player_rect)
        temp.blit(enemy_poke, enemy_rect)

        # HPバー
        pygame.draw.rect(temp, (100, 100, 100), (80, 340, 220, 28))
        pygame.draw.rect(temp, (255, 0, 0), (82, 342, max(0, int(player_hp * 2)), 24))
        pygame.draw.rect(temp, (0, 0, 0), (80, 340, 220, 28), 2)
        draw_text(temp, f"あなた HP: {max(0, player_hp)}", 82, 308, 24, (0, 0, 0))

        pygame.draw.rect(temp, (100, 100, 100), (500, 80, 220, 28))
        pygame.draw.rect(temp, (255, 0, 0), (502, 82, max(0, int(enemy_hp * 2)), 24))
        pygame.draw.rect(temp, (0, 0, 0), (500, 80, 220, 28), 2)
        draw_text(temp, f"{enemy_name} HP: {max(0, enemy_hp)}", 500, 50, 24, (0, 0, 0))

        # メッセージウィンドウ
        pygame.draw.rect(temp, (255, 255, 255), (50, 400, 700, 170))
        pygame.draw.rect(temp, (0, 0, 0), (50, 400, 700, 170), 3)
        draw_text(temp, message, 80, 420, 28, (0, 0, 0))

        # === 修正版: コマンド選択肢をウィンドウ内に整列表示 ===
        if turn == "player":
            base_y = 450  # メッセージ枠内に配置
            line_height = 30
            for i, (cmd, _) in enumerate(commands):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                draw_text(temp, cmd, 100, base_y + i * line_height, 26, color)

        for f in floating:
            f.draw(temp)

        screen.fill((0, 0, 0))
        screen.blit(temp, (sx, sy))
        pygame.display.flip()
        clock.tick(60)


def show_result(screen: pygame.Surface, result: str) -> None:
    clock = pygame.time.Clock()
    W, H = 800, 600
    img_name = "win.png" if result == "win" else "lose.png"
    img = pygame.image.load(img_name).convert()
    img = pygame.transform.scale(img, (W, H))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return
        screen.blit(img, (0, 0))
        draw_text(screen, "Enterで戻る", 300, 500, 36, (255, 255, 255))
        pygame.display.flip()
        clock.tick(30)


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    bg_img = pygame.image.load("background.png").convert()
    bw, bh = bg_img.get_size()
    screen = pygame.display.set_mode((bw, bh))
    pygame.display.set_caption("ポケットコウカトン")

    player_down_img = pygame.image.load("player_down.png").convert_alpha()
    player_left_img = pygame.image.load("player_side_left.png").convert_alpha()
    player_right_img = pygame.transform.flip(player_left_img, True, False)

    player_scale = 0.1
    pw, ph = player_down_img.get_size()
    new_size = (int(pw * player_scale), int(ph * player_scale))
    player_down_img = pygame.transform.scale(player_down_img, new_size)
    player_left_img = pygame.transform.scale(player_left_img, new_size)
    player_right_img = pygame.transform.scale(player_right_img, new_size)

    def scale_img(img, s):
        w, h = img.get_size()
        return pygame.transform.scale(img, (int(w * s), int(h * s)))

    boss_yellow_img = scale_img(pygame.image.load("boss_yellow.png").convert_alpha(), 0.2)
    boss_red_img = scale_img(pygame.image.load("boss_red.png").convert_alpha(), 0.2)
    boss_white_img = scale_img(pygame.image.load("boss_white.png").convert_alpha(), 0.18)

    boss_yellow_rect = boss_yellow_img.get_rect(topleft=(200, 200))
    boss_red_rect = boss_red_img.get_rect(topleft=(400, 200))
    boss_white_rect = boss_white_img.get_rect(topleft=(600, 180))

    bosses = [
        {"name": "イエローボス", "img": boss_yellow_img, "rect": boss_yellow_rect, "alive": True},
        {"name": "レッドボス", "img": boss_red_img, "rect": boss_red_rect, "alive": True},
        {"name": "ホワイトボス", "img": boss_white_img, "rect": boss_white_rect, "alive": True},
    ]

    player_img = player_down_img
    player_rect = player_img.get_rect(topleft=(465, 600))

    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        auto_top = detect_top_walkable_y(bg_img)
        top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

    clock = pygame.time.Clock()
    speed = 4

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx = -speed
            player_img = player_left_img
        elif keys[pygame.K_RIGHT]:
            dx = speed
            player_img = player_right_img
        elif keys[pygame.K_UP]:
            dy = -speed
            player_img = player_down_img
        elif keys[pygame.K_DOWN]:
            dy = speed
            player_img = player_down_img

        player_rect.x += dx
        player_rect.y += dy
        player_rect.clamp_ip(bg_img.get_rect())
        if player_rect.top < top_limit:
            player_rect.top = top_limit

        collided_boss = None
        for boss in bosses:
            if boss["alive"] and player_rect.colliderect(boss["rect"]):
                collided_boss = boss
                break

        if collided_boss:
            result = battle_scene(screen, collided_boss["name"])
            show_result(screen, result)
            if result == "win":
                collided_boss["alive"] = False
            player_rect.topleft = (465, 600)

        screen.blit(bg_img, (0, 0))
        for boss in bosses:
            if boss["alive"]:
                screen.blit(boss["img"], boss["rect"])
        screen.blit(player_img, player_rect)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
