import pygame
import sys

def main():
    pygame.init()

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Top View Demo")

    # ===== 背景読み込み =====
    bg_img = pygame.image.load("background.png").convert()

    # 背景の縮小倍率
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

    boss_yellow_scale = 0.2
    boss_red_scale    = 0.2
    boss_white_scale  = 0.18

    def scale_img(img, s):
        w, h = img.get_size()
        return pygame.transform.scale(img, (int(w * s), int(h * s)))

    boss_yellow_img = scale_img(boss_yellow_img, boss_yellow_scale)
    boss_red_img    = scale_img(boss_red_img,    boss_red_scale)
    boss_white_img  = scale_img(boss_white_img,  boss_white_scale)

    boss_yellow_rect = boss_yellow_img.get_rect(topleft=(200, 200))
    boss_red_rect    = boss_red_img.get_rect(topleft=(400, 200))
    boss_white_rect  = boss_white_img.get_rect(topleft=(600, 180))

    # ===== プレイヤー初期位置 =====
    # ★ ここを自由に設定できるようにした！
    player_start_x = 465  # ← プレイヤーの初期X座標
    player_start_y = 600  # ← プレイヤーの初期Y座標

    player_img = player_down_img
    player_rect = player_img.get_rect()
    player_rect.topleft = (player_start_x, player_start_y)  # ←ここで反映

    clock = pygame.time.Clock()
    speed = 4

    # ===== ゲームループ =====
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
        player_rect.clamp_ip(bg_rect)

        # ===== 描画 =====
        screen.blit(bg_img, (0, 0))
        screen.blit(boss_yellow_img, boss_yellow_rect)
        screen.blit(boss_red_img, boss_red_rect)
        screen.blit(boss_white_img, boss_white_rect)
        screen.blit(player_img, player_rect)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
