import pygame
import sys
import os
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300


def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    cx = bg_surf.get_rect().centerx
    h = bg_surf.get_height()
    sample_y = int(h * 0.65)
    floor_color = bg_surf.get_at((cx, sample_y))
    band = range(cx - 6, cx + 7)
    for y in range(0, sample_y + 1):
        is_floor_row = any(bg_surf.get_at((x, y)) == floor_color for x in band)
        if is_floor_row:
            return y + 2
    return 2


# ふれあいモードを管理するクラス

class PetScene:
    def __init__(self, folder: str, screen: pygame.Surface):
        """ふれあいシーンを初期化"""
        self.screen = screen
        self.folder = folder
        self.state = "normal"  # "normal", "pet", "hit", "hit_strong"
        self.last_q_press_time = 0
        self.action_start_time = 0

        # フォント
        self.font = pygame.font.SysFont("meiryo", 28)

        # 画像をロード
        self.images = {
            "normal": pygame.image.load(os.path.join(folder, "1.png")).convert_alpha(),
            "pet": pygame.image.load(os.path.join(folder, "9.png")).convert_alpha(),
            "hit": pygame.image.load(os.path.join(folder, "7.png")).convert_alpha(),
            "hit_strong": pygame.image.load(os.path.join(folder, "8.png")).convert_alpha(),
        }

    def handle_event(self, event):
        """キー入力処理"""
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
        """状態更新（一定時間でnormalに戻す）"""
        if self.state != "normal" and time.time() - self.action_start_time > 3:
            self.state = "normal"

    def draw(self):
        """画面描画"""
        screen = self.screen
        screen.fill((255, 200, 220))

        sw, sh = screen.get_size()
        pet_img = self.images[self.state]

        # 画像を画面中央に拡大して表示
        ih, iw = pet_img.get_height(), pet_img.get_width()
        scale_factor = (sh * 0.6) / ih
        scaled = pygame.transform.scale(pet_img, (int(iw * scale_factor), int(ih * scale_factor)))
        rect = scaled.get_rect(center=(sw // 2, sh // 2))
        screen.blit(scaled, rect)

        # 説明テキスト
        msg1 = self.font.render("A：なでる", True, (100, 0, 50))
        msg2 = self.font.render("Q：なぐる（連打で強）", True, (100, 0, 50))
        msg3 = self.font.render("F：もどる", True, (100, 0, 50))
        screen.blit(msg1, (sw - msg1.get_width() - 20, 20))
        screen.blit(msg2, (sw - msg2.get_width() - 20, 60))
        screen.blit(msg3, (sw - msg3.get_width() - 20, 100))


# メインゲーム部分（元のmain関数）

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("ポケットコウカトン")

    # ===== 背景 =====
    bg_img = pygame.image.load("background.png").convert()
    bg_rect = bg_img.get_rect()
    screen = pygame.display.set_mode((bg_rect.width, bg_rect.height))

    # ===== プレイヤー画像 =====
    player_down_img = pygame.image.load("player_down.png").convert_alpha()
    player_left_img = pygame.image.load("player_side_left.png").convert_alpha()
    player_right_img = pygame.transform.flip(player_left_img, True, False)

    player_scale = 0.1
    pw, ph = player_down_img.get_size()
    new_size = (int(pw * player_scale), int(ph * player_scale))
    player_down_img = pygame.transform.scale(player_down_img, new_size)
    player_left_img = pygame.transform.scale(player_left_img, new_size)
    player_right_img = pygame.transform.scale(player_right_img, new_size)

    # ===== 玉座3人 =====
    def scale_img(img, s):
        w, h = img.get_size()
        return pygame.transform.scale(img, (int(w * s), int(h * s)))

    boss_yellow_img = scale_img(pygame.image.load("boss_yellow.png").convert_alpha(), 0.2)
    boss_red_img    = scale_img(pygame.image.load("boss_red.png").convert_alpha(),    0.2)
    boss_white_img  = scale_img(pygame.image.load("boss_white.png").convert_alpha(),  0.18)

    boss_yellow_rect = boss_yellow_img.get_rect(topleft=(200, 200))
    boss_red_rect    = boss_red_img.get_rect(topleft=(400, 200))
    boss_white_rect  = boss_white_img.get_rect(topleft=(600, 180))

    # ===== プレイヤー初期位置 =====
    player_rect = player_down_img.get_rect(topleft=(465, 600))
    player_img = player_down_img

    # ===== 上方向の移動上限 =====
    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        auto_top = detect_top_walkable_y(bg_img)
        top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

    clock = pygame.time.Clock()
    speed = 4
    pink_mode = False

    font = pygame.font.SysFont("meiryo", 28)
    info_text = font.render("Fキーでふれあい画面へ", True, (255, 255, 255))

    # ===== PetSceneのインスタンス作成 =====
    pet_scene = PetScene("こうかとん", screen)

    # ===== ゲームループ =====
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    pink_mode = not pink_mode
                    pet_scene.state = "normal"
                elif pink_mode:
                    pet_scene.handle_event(event)

        # ===== ふれあいモード =====
        if pink_mode:
            pet_scene.update()
            pet_scene.draw()
            pygame.display.flip()
            clock.tick(60)
            continue

        # ===== 通常モード =====
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
        player_rect.clamp_ip(bg_rect)
        if player_rect.top < top_limit:
            player_rect.top = top_limit

        # ===== 描画 =====
        screen.blit(bg_img, (0, 0))
        screen.blit(boss_yellow_img, boss_yellow_rect)
        screen.blit(boss_red_img, boss_red_rect)
        screen.blit(boss_white_img, boss_white_rect)
        screen.blit(player_img, player_rect)
        screen.blit(info_text, (20, 20))
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
