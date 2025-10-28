import pygame
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

#  上限（上方向の到達位置）設定 
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300


def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    cx = bg_surf.get_rect().centerx
    h  = bg_surf.get_height()
    sample_y = int(h * 0.65)
    floor_color = bg_surf.get_at((cx, sample_y))
    band = range(cx - 6, cx + 7)
    for y in range(0, sample_y + 1):
        is_floor_row = any(bg_surf.get_at((x, y)) == floor_color for x in band)
        if is_floor_row:
            return y + 2
    return 2


def main():
    pygame.init()

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("ポケットコウカトン")

    # ===== 背景読み込み =====
    bg_img = pygame.image.load("background.png").convert()
    bg_scale = 1
    bw, bh = bg_img.get_size()
    bg_img = pygame.transform.scale(bg_img, (int(bw * bg_scale), int(bh * bg_scale)))
    bg_rect = bg_img.get_rect()
    screen = pygame.display.set_mode((bg_rect.width, bg_rect.height))

    # ===== プレイヤー画像読み込み =====
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
    boss_yellow_img = pygame.image.load("boss_yellow.png").convert_alpha()
    boss_red_img    = pygame.image.load("boss_red.png").convert_alpha()
    boss_white_img  = pygame.image.load("boss_white.png").convert_alpha()

    def scale_img(img, s):
        w, h = img.get_size()
        return pygame.transform.scale(img, (int(w * s), int(h * s)))

    boss_yellow_img = scale_img(boss_yellow_img, 0.2)
    boss_red_img    = scale_img(boss_red_img,    0.2)
    boss_white_img  = scale_img(boss_white_img,  0.18)

    boss_yellow_rect = boss_yellow_img.get_rect(topleft=(200, 200))
    boss_red_rect    = boss_red_img.get_rect(topleft=(400, 200))
    boss_white_rect  = boss_white_img.get_rect(topleft=(600, 180))

    # ===== プレイヤー初期位置 =====
    player_start_x = 465
    player_start_y = 600

    player_img = player_down_img
    player_rect = player_img.get_rect()
    player_rect.topleft = (player_start_x, player_start_y)

    # ===== 上方向の移動上限 =====
    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        auto_top = detect_top_walkable_y(bg_img)
        top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

    clock = pygame.time.Clock()
    speed = 4

    # ===== ゲーム状態フラグ =====
    pink_mode = False  # ← Fキーで切り替わる

    # ===== フォント設定 =====
    font = pygame.font.SysFont("meiryo", 28)
    info_text = font.render("Fキー:ふれあい", True, (255, 255, 255))

    # ===== ゲームループ =====
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                # Fキーでモード切り替え
                if event.key == pygame.K_f:
                    pink_mode = not pink_mode

        # ===== ピンク画面モード =====
        if pink_mode:
            screen.fill((255, 200, 220))  # 薄ピンク
            msg = font.render("Fキーでもどる", True, (100, 0, 50))
            screen.blit(msg, (50, 50))
            pygame.display.flip()
            clock.tick(60)
            continue  # 通常ゲーム部分はスキップ

        # ===== 通常ゲームモード =====
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
        screen.blit(info_text, (20, 20))  # ← 説明表示
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
