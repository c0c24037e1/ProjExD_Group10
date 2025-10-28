import pygame
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ====== 設定 ======
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300

MODE_TITLE  = 0  # タイトル画面
MODE_SELECT = 1  # モンスター選択画面（3体から1体選ぶ）
MODE_PLAY   = 2  # フィールド移動
MODE_CLEAR  = 3  # チャンピオンおめでとう画面


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
    pygame.display.set_caption("Top View Demo")

    clock = pygame.time.Clock()

    # フォント
    font_big   = pygame.font.Font(None, 64)
    font_mid   = pygame.font.Font(None, 40)
    font_small = pygame.font.Font(None, 28)

    # ===== 背景 =====
    bg_img = pygame.image.load("background.png").convert()

    bg_scale = 1  # 背景の縮小率（必要なら0.6とかに変えてOK）
    bw, bh = bg_img.get_size()
    bg_img = pygame.transform.scale(bg_img, (int(bw * bg_scale), int(bh * bg_scale)))
    bg_rect = bg_img.get_rect()

    # 画面サイズ合わせ
    screen = pygame.display.set_mode((bg_rect.width, bg_rect.height))

    # ===== プレイヤー =====
    player_down_img = pygame.image.load("player_down.png").convert_alpha()
    player_left_img = pygame.image.load("player_side_left.png").convert_alpha()
    player_right_img = pygame.transform.flip(player_left_img, True, False)

    player_scale = 0.1
    pw, ph = player_down_img.get_size()
    new_size = (int(pw * player_scale), int(ph * player_scale))
    player_down_img  = pygame.transform.scale(player_down_img, new_size)
    player_left_img  = pygame.transform.scale(player_left_img, new_size)
    player_right_img = pygame.transform.scale(player_right_img, new_size)

    player_img = player_down_img
    player_rect = player_img.get_rect()
    player_rect.topleft = (465, 600)  # 初期座標は今まで通り

    # ===== 玉座3人（これも仲間候補として使う）=====
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

    # ===== 仲間候補（3体） =====
    # ここに並べる順番が “選択肢” になる
    partner_options = [boss_yellow_img, boss_red_img, boss_white_img]
    partner_names   = ["satoru", "jun", "kouki"]  # 画面に名前出したいなら
    selected_index = 0  # ←今選んでる子（←→で動かす）

    # プレイ中に連れている相棒の画像（最初はまだいない）
    partner_img = None

    # ===== top_limit =====
    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        auto_top = detect_top_walkable_y(bg_img)
        top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

    # ===== モード開始点 =====
    mode = MODE_TITLE

    # ===== メインループ =====
    while True:
        # ---------------- イベント処理 ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # タイトル
            if mode == MODE_TITLE:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    mode = MODE_SELECT  # タイトル → 選択へ

            # モンスター選択
            elif mode == MODE_SELECT:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        selected_index = (selected_index - 1) % len(partner_options)
                    elif event.key == pygame.K_RIGHT:
                        selected_index = (selected_index + 1) % len(partner_options)
                    elif event.key == pygame.K_RETURN:
                        # 決定したモンスターを相棒にする
                        partner_img = partner_options[selected_index]
                        # 決定したらゲーム開始
                        mode = MODE_PLAY

            # プレイ中（フィールド）
            elif mode == MODE_PLAY:
                # デバッグ用：Cキーでクリア画面へ
                if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                    mode = MODE_CLEAR

            # クリア画面
            elif mode == MODE_CLEAR:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    pygame.quit()
                    sys.exit()

        # ---------------- ロジック（動きなど） ----------------
        if mode == MODE_PLAY:
            keys = pygame.key.get_pressed()
            dx = 0
            dy = 0

            if keys[pygame.K_LEFT]:
                dx = -4
                player_img = player_left_img
            elif keys[pygame.K_RIGHT]:
                dx = 4
                player_img = player_right_img
            elif keys[pygame.K_UP]:
                dy = -4
                player_img = player_down_img  # 仮：上向きまだないからdownで代用
            elif keys[pygame.K_DOWN]:
                dy = 4
                player_img = player_down_img

            # 移動反映
            player_rect.x += dx
            player_rect.y += dy

            # 画面外に出ない
            player_rect.clamp_ip(bg_rect)

            # 上方向の上限
            if player_rect.top < top_limit:
                player_rect.top = top_limit

        # CLEARやTITLE、SELECTは特にフレームごと動かす処理は今はなし

        # ---------------- 描画 ----------------
        if mode == MODE_TITLE:
            # 黒背景にメッセージ
            screen.fill((0, 0, 0))
            t1 = font_big.render("The Chamber of Beginnings", True, (255, 255, 0))
            t2 = font_mid.render("Press ENTER", True, (255, 255, 255))
            t3 = font_small.render("Choose Your Partner Monster", True, (180, 180, 180))

            screen.blit(t1, (bg_rect.centerx - t1.get_width()//2, 200))
            screen.blit(t2, (bg_rect.centerx - t2.get_width()//2, 280))
            screen.blit(t3, (bg_rect.centerx - t3.get_width()//2, 330))

        elif mode == MODE_SELECT:
            # 選択画面
            screen.fill((20, 20, 40))

            title = font_mid.render("Choose Your Partner Monster", True, (255, 255, 255))
            screen.blit(title, (bg_rect.centerx - title.get_width()//2, 60))

            # 3体を横並びで描画
            base_x = bg_rect.centerx - 300  # 左の開始位置
            y = 180                         # 縦位置

            for i, img in enumerate(partner_options):
                # キャラ表示
                x = base_x + i * 300        # 300px 間隔
                rect = img.get_rect(midtop=(x, y))
                screen.blit(img, rect)

                # 選択中の枠（黄色い四角いアウトライン）
                if i == selected_index:
                    pygame.draw.rect(screen, (255, 255, 0), rect, 5)

                # 名前表示（ここが「名前が出る」とこ）
                name_surface = font_small.render(partner_names[i], True, (255, 255, 0))
                screen.blit(
                    name_surface,
                    (rect.centerx - name_surface.get_width()//2, rect.bottom + 10)
                )

                guide = font_small.render("← → で選ぶ    Enterで決定", True, (255, 255, 255))
                screen.blit(guide, (bg_rect.centerx - guide.get_width()//2, bg_rect.height - 80))


        elif mode == MODE_PLAY:
            # 通常プレイ画面
            screen.blit(bg_img, (0, 0))
            screen.blit(boss_yellow_img, boss_yellow_rect)
            screen.blit(boss_red_img,    boss_red_rect)
            screen.blit(boss_white_img,  boss_white_rect)

            screen.blit(player_img, player_rect)

        

            # デバッグ：クリア行き方
            info = font_small.render("C", True, (255, 255, 0))
            screen.blit(info, (10, 10))

        elif mode == MODE_CLEAR:
            # お祝い画面
            
            screen.fill((20, 80, 90))

            # スポットライトっぽい三角形
            pygame.draw.polygon(screen, (255, 255, 255), [
                (bg_rect.centerx - 80, 0),
                (bg_rect.centerx - 20, 0),
                (bg_rect.centerx + 40, bg_rect.centery)
            ], 0)
            pygame.draw.polygon(screen, (255, 255, 255), [
                (bg_rect.centerx + 80, 0),
                (bg_rect.centerx + 20, 0),
                (bg_rect.centerx - 40, bg_rect.centery)
            ], 0)

            # キラキラ
            star_color = (255, 255, 200)
            for (sx, sy) in [(200,200),(300,150),(500,180),(600,240),(250,260),(450,120)]:
                pygame.draw.circle(screen, star_color, (sx, sy), 4)
                pygame.draw.circle(screen, star_color, (sx+8, sy+4), 2)

            line_top = font_big.render("You are the Champion.", True, (255, 215, 0))
            screen.blit(line_top, (bg_rect.centerx - line_top.get_width()//2, 80))

            party_y = bg_rect.centery + 40

            # 相棒モンスター（選んだやつ）
            if partner_img is not None:
                buddy_rect = partner_img.get_rect()
                buddy_rect.midbottom = (bg_rect.centerx - 80, party_y)
                screen.blit(partner_img, buddy_rect)

            # 主人公
            hero_rect = player_img.get_rect()
            hero_rect.midbottom = (bg_rect.centerx + 40, party_y)
            screen.blit(player_img, hero_rect)

            line_press = font_mid.render("Press ENTER to finish", True, (255, 255, 255))
            screen.blit(line_press, (bg_rect.centerx - line_press.get_width()//2, party_y + 40))

        pygame.display.flip()
        clock.tick(60)
        


if __name__ == "__main__":
    main()
