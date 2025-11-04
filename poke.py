import pygame
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ====== 設定 ======
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300

MODE_TITLE  = 0  # タイトル画面
MODE_SELECT = 1  # タマゴ＆孵化演出画面
MODE_PLAY   = 2  # フィールド移動
MODE_CLEAR  = 3  # チャンピオンおめでとう画面


def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """元のままのtop判定関数"""
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


def scale_img(img: pygame.Surface, s: float) -> pygame.Surface:
    w, h = img.get_size()
    return pygame.transform.scale(img, (int(w * s), int(h * s)))


class Player:
    def __init__(self, bg_rect: pygame.Rect):
        # 画像読み込み
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
        self.rect = self.image.get_rect()
        self.rect.topleft = (465, 600)
        self.bg_rect = bg_rect

    def update(self, keys, top_limit: int):
        dx = 0
        dy = 0

        if keys[pygame.K_LEFT]:
            dx = -4
            self.image = self.left_img
        elif keys[pygame.K_RIGHT]:
            dx = 4
            self.image = self.right_img
        elif keys[pygame.K_UP]:
            dy = -4
            self.image = self.down_img  # 上画像がないので仮でdown
        elif keys[pygame.K_DOWN]:
            dy = 4
            self.image = self.down_img

        self.rect.x += dx
        self.rect.y += dy

        # 画面外に出ない
        self.rect.clamp_ip(self.bg_rect)

        # 上方向の上限
        if self.rect.top < top_limit:
            self.rect.top = top_limit

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, self.rect)


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


class Partner:
    def __init__(self, name: str):
        img = pygame.image.load("3.png").convert_alpha()
        img = scale_img(img, 5)  # こうかとんをドーンと大きく
        self.image = img
        self.name = name

    def draw_center(self, screen: pygame.Surface, center_pos):
        rect = self.image.get_rect(center=center_pos)
        screen.blit(self.image, rect)

    def draw_midbottom(self, screen: pygame.Surface, midbottom_pos):
        rect = self.image.get_rect()
        rect.midbottom = midbottom_pos
        screen.blit(self.image, rect)


class BossGroup:
    """玉座の3人をまとめて管理・描画"""
    def __init__(self):
        yellow = pygame.image.load("boss_yellow.png").convert_alpha()
        red    = pygame.image.load("boss_red.png").convert_alpha()
        white  = pygame.image.load("boss_white.png").convert_alpha()

        self.yellow_img = scale_img(yellow, 0.2)
        self.red_img    = scale_img(red,    0.2)
        self.white_img  = scale_img(white,  0.18)

        self.yellow_rect = self.yellow_img.get_rect(topleft=(200, 200))
        self.red_rect    = self.red_img.get_rect(topleft=(400, 200))
        self.white_rect  = self.white_img.get_rect(topleft=(600, 180))

    def draw(self, screen: pygame.Surface):
        screen.blit(self.yellow_img, self.yellow_rect)
        screen.blit(self.red_img,    self.red_rect)
        screen.blit(self.white_img,  self.white_rect)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Top View Demo")
        self.clock = pygame.time.Clock()

        # フォント
        self.font_big   = pygame.font.Font(None, 64)
        self.font_mid   = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 28)

        # 背景
        bg_img = pygame.image.load("background.png").convert()
        bg_scale = 1
        bw, bh = bg_img.get_size()
        bg_img = pygame.transform.scale(bg_img, (int(bw * bg_scale), int(bh * bg_scale)))
        self.bg_img = bg_img
        self.bg_rect = self.bg_img.get_rect()

        self.screen = pygame.display.set_mode((self.bg_rect.width, self.bg_rect.height))

        # 各オブジェクト
        self.player = Player(self.bg_rect)
        self.egg = Egg(self.bg_rect)
        self.partner = Partner("koukaton")
        self.bosses = BossGroup()

        # top_limit
        if USE_MANUAL_TOP_LIMIT:
            self.top_limit = MANUAL_TOP_Y
        else:
            auto_top = detect_top_walkable_y(self.bg_img)
            self.top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

        # 状態
        self.mode = MODE_TITLE
        self.egg_phase = 0  # 0:タマゴ, 1:孵化後（相棒お披露目）

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

    # ===== イベント処理 =====
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # タイトル
            if self.mode == MODE_TITLE:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.mode = MODE_SELECT

            # タマゴ＆孵化演出
            elif self.mode == MODE_SELECT:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    if self.egg_phase == 0:
                        # 1回目：孵化させて相棒出現
                        self.egg_phase = 1
                    else:
                        # 2回目：ゲーム開始
                        self.mode = MODE_PLAY

            # プレイ中
            elif self.mode == MODE_PLAY:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                    self.mode = MODE_CLEAR

            # クリア画面
            elif self.mode == MODE_CLEAR:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    pygame.quit()
                    sys.exit()

    # ===== ロジック =====
    def update(self):
        if self.mode == MODE_PLAY:
            keys = pygame.key.get_pressed()
            self.player.update(keys, self.top_limit)

    # ===== 描画 =====
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
        t1 = self.font_big.render("The Chamber of Beginnings", True, (255, 255, 0))
        t2 = self.font_mid.render("Press ENTER", True, (255, 255, 255))
        t3 = self.font_small.render("A mysterious egg awaits...", True, (180, 180, 180))
        cx = self.bg_rect.centerx
        self.screen.blit(t1, (cx - t1.get_width()//2, 200))
        self.screen.blit(t2, (cx - t2.get_width()//2, 280))
        self.screen.blit(t3, (cx - t3.get_width()//2, 330))

    def draw_select(self):
        self.screen.fill((10, 10, 30))
        cx = self.bg_rect.centerx
        cy = self.bg_rect.centery

        if self.egg_phase == 0:
            # タマゴ状態
            title = self.font_mid.render("A mysterious egg appeared...", True, (255, 255, 255))
            self.screen.blit(title, (cx - title.get_width()//2, 80))

            self.egg.draw(self.screen)

            guide = self.font_small.render("Press ENTER to hatch the egg!", True, (255, 255, 255))
            self.screen.blit(guide, (cx - guide.get_width()//2, self.bg_rect.height - 100))
        else:
            # 孵化後：相棒お披露目
            title = self.font_mid.render("The egg hatched!", True, (255, 255, 255))
            self.screen.blit(title, (cx - title.get_width()//2, 60))

            sub = self.font_small.render(f"Your partner is {self.partner.name}.", True, (255, 215, 0))
            self.screen.blit(sub, (cx - sub.get_width()//2, 110))

            self.partner.draw_center(self.screen, (cx, cy + 40))

            guide = self.font_small.render("Press ENTER to start your journey!", True, (255, 255, 255))
            self.screen.blit(guide, (cx - guide.get_width()//2, self.bg_rect.height - 100))

    def draw_play(self):
        self.screen.blit(self.bg_img, (0, 0))
        self.bosses.draw(self.screen)
        self.player.draw(self.screen)
        info = self.font_small.render("C", True, (255, 255, 0))
        self.screen.blit(info, (10, 10))

    def draw_clear(self):
        self.screen.fill((20, 80, 90))
        cx = self.bg_rect.centerx
        cy = self.bg_rect.centery

        # スポットライト
        pygame.draw.polygon(self.screen, (255, 255, 255), [
            (cx - 80, 0),
            (cx - 20, 0),
            (cx + 40, cy)
        ], 0)
        pygame.draw.polygon(self.screen, (255, 255, 255), [
            (cx + 80, 0),
            (cx + 20, 0),
            (cx - 40, cy)
        ], 0)

        # キラキラ
        star_color = (255, 255, 200)
        for (sx, sy) in [(200,200),(300,150),(500,180),(600,240),(250,260),(450,120)]:
            pygame.draw.circle(self.screen, star_color, (sx, sy), 4)
            pygame.draw.circle(self.screen, star_color, (sx+8, sy+4), 2)

        line_top = self.font_big.render("You are the Champion.", True, (255, 215, 0))
        self.screen.blit(line_top, (cx - line_top.get_width()//2, 80))

        name_text = f"Your partner is {self.partner.name}!"
        line_name = self.font_small.render(name_text, True, (255, 255, 255))
        self.screen.blit(line_name, (cx - line_name.get_width()//2, 130))

        party_y = cy + 40

        # 相棒
        self.partner.draw_midbottom(self.screen, (cx - 80, party_y))
        # 主人公
        hero_rect = self.player.image.get_rect()
        hero_rect.midbottom = (cx + 40, party_y)
        self.screen.blit(self.player.image, hero_rect)

        line_press = self.font_mid.render("Press ENTER to finish", True, (255, 255, 255))
        self.screen.blit(line_press, (cx - line_press.get_width()//2, party_y + 40))


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
