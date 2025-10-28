import pygame
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

#  上限（上方向の到達位置）設定 
USE_MANUAL_TOP_LIMIT = False   # True: MANUAL_TOP_Y を使う / False: 背景から自動検出
MANUAL_TOP_Y = 150             # 手動で決める最小 top 座標（小さいほど上へ行ける）
TOP_LIMIT_OFFSET = -300        # 自動検出値に加えるオフセット（負でさらに上へ行ける）


def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """
    背景画像の中央付近の床色を基準に、
    画面中央の細い帯（±6px）を上方向へスキャンして
    「床が始まる最上端」の y を返す（プレイヤーrect.topの最小値に使う）。
    ※ドット絵など床と壁の色がはっきり分かれている前提の簡易版。
    """
    cx = bg_surf.get_rect().centerx
    h  = bg_surf.get_height()

    # まず中央やや下（確実に床のはず）から床色を取得
    sample_y = int(h * 0.65)
    floor_color = bg_surf.get_at((cx, sample_y))

    # 中央±6px帯で上に向かってスキャン
    band = range(cx - 6, cx + 7)
    for y in range(0, sample_y + 1):
        # 帯のどこか1pxでも床色なら床行とみなす
        is_floor_row = any(bg_surf.get_at((x, y)) == floor_color for x in band)
        if is_floor_row:
            # めり込み防止に +2
            return y + 2

    # 見つからなければ 0 付近を返す（安全側）
    return 2

def main():
    pygame.init()

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("ポケットコウカトン")

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
    player_start_x = 465  # ← プレイヤーの初期X座標
    player_start_y = 600  # ← プレイヤーの初期Y座標

    player_img = player_down_img
    player_rect = player_img.get_rect()
    player_rect.topleft = (player_start_x, player_start_y)

    # ===== 上方向の移動上限（top_limit）を決定 =====
    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        auto_top = detect_top_walkable_y(bg_img)
        top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)  # 画面外にならないよう0で下限

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
            player_img = player_down_img  # 上画像が無いなら暫定でdown
        elif keys[pygame.K_DOWN]:
            dy = speed
            player_img = player_down_img

        player_rect.x += dx
        player_rect.y += dy

        # まずは画面外に出ないように全体クランプ
        player_rect.clamp_ip(bg_rect)

        # 次に「上方向の上限」を適用（top が top_limit より小さくならない）
        if player_rect.top < top_limit:
            player_rect.top = top_limit

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