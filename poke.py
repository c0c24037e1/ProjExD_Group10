import pygame
import sys
import os
import random
from typing import List, Tuple

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
        if any(bg_surf.get_at((x, y)) == floor_color for x in band):
            return y + 2
    return 2


def get_jp_font(size: int) -> pygame.font.Font:
    font_paths = ["C:/Windows/Fonts/msgothic.ttc", "C:/Windows/Fonts/meiryo.ttc"]
    for path in font_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_text(screen, text, x, y, size=28, color=(0, 0, 0)):
    font = get_jp_font(size)
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))


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


class Player:
    def __init__(self, x: int, y: int):
        self.images = {
            "down": pygame.image.load("player_down.png").convert_alpha(),
            "left": pygame.image.load("player_side_left.png").convert_alpha(),
            "right": pygame.transform.flip(pygame.image.load("player_side_left.png"), True, False),
        }
        self.scale = 0.1
        self.images = {k: pygame.transform.scale(v, self.scaled_size(v)) for k, v in self.images.items()}
        self.image = self.images["down"]
        self.rect = self.image.get_rect(topleft=(x, y))

    def scaled_size(self, img: pygame.Surface):
        w, h = img.get_size()
        return int(w * self.scale), int(h * self.scale)

    def move(self, keys, speed, top_limit, bounds):
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx = -speed
            self.image = self.images["left"]
        elif keys[pygame.K_RIGHT]:
            dx = speed
            self.image = self.images["right"]
        elif keys[pygame.K_UP]:
            dy = -speed
            self.image = self.images["down"]
        elif keys[pygame.K_DOWN]:
            dy = speed
            self.image = self.images["down"]

        self.rect.x += dx
        self.rect.y += dy
        self.rect.clamp_ip(bounds)
        if self.rect.top < top_limit:
            self.rect.top = top_limit

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class Boss:
    def __init__(self, name: str, img_path: str, type_: str, scale: float, x: int, y: int):
        self.name = name
        self.type = type_
        img = pygame.image.load(img_path).convert_alpha()
        w, h = img.get_size()
        self.image = pygame.transform.scale(img, (int(w * scale), int(h * scale)))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.alive = True

    def draw(self, screen):
        if self.alive:
            screen.blit(self.image, self.rect)


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


def battle_scene(screen, enemy_name: str, enemy_type: str) -> str:
    W, H = 800, 600
    clock = pygame.time.Clock()
    pygame.display.set_mode((W, H))

    bg = pygame.transform.scale(pygame.image.load("battle_bg.png"), (W, H))
    player_img = pygame.transform.scale(pygame.image.load("player_poke.png"), (200, 200))
    enemy_img = pygame.transform.scale(pygame.image.load("enemy_poke.png"), (200, 200))
    player_rect = player_img.get_rect(bottomleft=(200, 550))
    enemy_rect = enemy_img.get_rect(topleft=(500, 150))

    player_hp, enemy_hp = 100, 100
    commands = [
        ("たいあたり", 10, "ノーマル"),
        ("かえんほうしゃ", 25, "ほのお"),
        ("ほうでん", 15, "でんき"),
        ("みずでっぽう", 20, "みず"),
    ]
    selected = 0
    turn = "player"
    message = f"{enemy_name} ({enemy_type}) が あらわれた！"
    floating: List[FloatingNumber] = []
    effect_text = None
    effect_timer = 0

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN and turn == "player":
                if e.key == pygame.K_UP:
                    selected = (selected - 1) % len(commands)
                elif e.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(commands)
                elif e.key == pygame.K_RETURN:
                    move, base_dmg, move_type = commands[selected]
                    mult = get_type_multiplier(move_type, enemy_type)
                    dmg = int(base_dmg * mult)
                    enemy_hp -= dmg
                    floating.append(FloatingNumber(str(dmg), enemy_rect.midtop))

                    if mult > 1:
                        effect_text = "こうかはばつぐんだ！"
                        effect_timer = 60  # 約1秒表示
                    elif mult < 1:
                        effect_text = "こうかはいまひとつだ…"
                        effect_timer = 60
                    else:
                        effect_text = None

                    message = f"{move}！ {dmg}ダメージ！"
                    if enemy_hp <= 0:
                        return "win"
                    turn = "enemy"

        if turn == "enemy":
            pygame.time.delay(600)
            dmg = random.randint(8, 22)
            player_hp -= dmg
            message = f"{enemy_name} の こうげき！ {dmg}ダメージ！"
            floating.append(FloatingNumber(str(dmg), player_rect.midtop))
            if player_hp <= 0:
                return "lose"
            turn = "player"

        floating = [f for f in floating if f.update()]

        temp = pygame.Surface((W, H))
        temp.blit(bg, (0, 0))
        temp.blit(player_img, player_rect)
        temp.blit(enemy_img, enemy_rect)
        pygame.draw.rect(temp, (255, 0, 0), (80, 340, max(0, player_hp * 2), 20))
        pygame.draw.rect(temp, (255, 0, 0), (500, 80, max(0, enemy_hp * 2), 20))
        draw_text(temp, message, 80, 420, 26)

        if turn == "player":
            for i, (cmd, _, t) in enumerate(commands):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                draw_text(temp, f"{cmd}（{t}）", 100, 450 + i * 30, 24, color)

        for f in floating:
            f.draw(temp)

        # 効果抜群・いまひとつ表示
        if effect_text:
            draw_text(temp, effect_text, 280, 250, 40, (255, 255, 0))
            effect_timer -= 1
            if effect_timer <= 0:
                effect_text = None

        screen.blit(temp, (0, 0))
        pygame.display.flip()
        clock.tick(60)


def show_result(screen, result: str):
    W, H = 800, 600
    pygame.display.set_mode((W, H))
    img = pygame.transform.scale(
        pygame.image.load("win.png" if result == "win" else "lose.png"), (W, H))
    clock = pygame.time.Clock()

    if result == "win":
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < 3000:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            screen.blit(img, (0, 0))
            draw_text(screen, "WIN!", 350, 500, 40, (255, 255, 255))
            pygame.display.flip()
            clock.tick(30)
        return

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return
        screen.blit(img, (0, 0))
        draw_text(screen, "Enterで戻る", 300, 500, 30, (255, 255, 255))
        pygame.display.flip()
        clock.tick(30)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    bg = pygame.image.load("background.png").convert()
    bw, bh = bg.get_size()
    screen = pygame.display.set_mode((bw, bh))
    pygame.display.set_caption("ポケットコウカトン")

    player = Player(465, 600)
    bosses = [
        Boss("イエローボス", "boss_yellow.png", "でんき", 0.2, 200, 200),
        Boss("レッドボス", "boss_red.png", "ほのお", 0.2, 400, 200),
        Boss("ブルーボス", "boss_white.png", "みず", 0.18, 600, 180),
    ]

    top_limit = MANUAL_TOP_Y if USE_MANUAL_TOP_LIMIT else max(0, detect_top_walkable_y(bg) + TOP_LIMIT_OFFSET)
    clock = pygame.time.Clock()
    speed = 4

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        player.move(keys, speed, top_limit, bg.get_rect())

        collided = next((b for b in bosses if b.alive and player.rect.colliderect(b.rect)), None)
        if collided:
            result = battle_scene(screen, collided.name, collided.type)
            show_result(screen, result)
            if result == "win":
                collided.alive = False
                show_result(screen, "win")
                pygame.quit()
                sys.exit()
            player.rect.topleft = (465, 600)

        screen.blit(bg, (0, 0))
        for b in bosses:
            b.draw(screen)
        player.draw(screen)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
