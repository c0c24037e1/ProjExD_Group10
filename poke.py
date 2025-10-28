import pygame
import sys

def main():
    pygame.init()

    # 仮ウィンドウ（convertのため）
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Top View Demo")

    # 背景読み込み
    bg_img = pygame.image.load("background.png").convert()
    bg_rect = bg_img.get_rect()

    # 背景に合わせて画面サイズ再設定
    screen = pygame.display.set_mode((bg_rect.width, bg_rect.height))

    # プレイヤー画像読み込み
    player_down_img = pygame.image.load("player_down.png").convert_alpha()
    player_left_img = pygame.image.load("player_side_left.png").convert_alpha()
    player_right_img = pygame.transform.flip(player_left_img, True, False)

    # ====== ここでサイズを小さくする ======
    scale = 0.1  # 小さくする倍率（例：0.5で半分）
    w, h = player_down_img.get_size()
    new_size = (int(w * scale), int(h * scale))

    player_down_img = pygame.transform.scale(player_down_img, new_size)
    player_left_img = pygame.transform.scale(player_left_img, new_size)
    player_right_img = pygame.transform.scale(player_right_img, new_size)
    # =====================================

    player_img = player_down_img
    player_rect = player_img.get_rect()
    player_rect.centerx = bg_rect.centerx
    player_rect.bottom = bg_rect.bottom - 10

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
        player_rect.clamp_ip(bg_rect)

        screen.blit(bg_img, (0, 0))
        screen.blit(player_img, player_rect)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
