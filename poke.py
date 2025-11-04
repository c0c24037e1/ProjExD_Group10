import pygame
import sys
import os
import time

# 実行フォルダをスクリプトの場所に固定
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ====== 定数設定 ======
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300

MODE_TITLE  = 0
MODE_SELECT = 1
MODE_PLAY   = 2
MODE_CLEAR  = 3


# ====== 関数群 ======
def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """背景から歩行可能上限を自動検出"""
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


def scale_img(img: pygame.Surface, s: float) -> pygame.Surface:
    w, h = img.get_size()
    return pygame.transform.scale(img, (int(w * s), int(h * s)))


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

        if keys[pygame.K_LEFT]:
            dx = -4
            self.image = self.left_img
        elif keys[pygame.K_RIGHT]:
            dx = 4
            self.image = self.right_img
        elif keys[pygame.K_UP]:
            dy = -4
            self.image = self.down_img
        elif keys[pygame.K_DOWN]:
            dy = 4
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


# ====== 相棒 ======
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
class BossGroup:
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


# ====== ふれあいシーン ======
class PetScene:
    def __init__(self, folder: str, screen: pygame.Surface):
        self.screen = screen
        self.folder = folder
        self.state = "normal"
        self.last_q_press_time = 0
        self.action_start_time = 0
        self.font = pygame.font.SysFont("meiryo", 28)

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


# ====== ゲーム全体 ======
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("ポケットコウカトン")
        self.clock = pygame.time.Clock()

        # 状態
        self.mode = MODE_TITLE
        self.egg_phase = 0
        self.pink_mode = False

        # フォント
        self.font_big   = pygame.font.Font(None, 64)
        self.font_mid   = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 28)

        # 背景
        self.bg_img = pygame.image.load("background.png").convert()
        self.bg_rect = self.bg_img.get_rect()

        # 各キャラ
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
        while True:
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
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    self.pink_mode = not self.pink_mode
                    continue

                if self.pink_mode:
                    self.pet_scene.handle_event(event)
                    continue

                if self.mode == MODE_TITLE:
                    if event.key == pygame.K_RETURN:
                        self.mode = MODE_SELECT

                elif self.mode == MODE_SELECT:
                    if event.key == pygame.K_RETURN:
                        if self.egg_phase == 0:
                            self.egg_phase = 1
                        else:
                            self.mode = MODE_PLAY

                elif self.mode == MODE_PLAY:
                    if event.key == pygame.K_c:
                        self.mode = MODE_CLEAR

                elif self.mode == MODE_CLEAR:
                    if event.key == pygame.K_RETURN:
                        pygame.quit()
                        sys.exit()

    def update(self):
        if self.mode == MODE_PLAY:
            keys = pygame.key.get_pressed()
            self.player.update(keys, self.top_limit)

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
        cx, cy = self.bg_rect.center
        if self.egg_phase == 0:
            title = self.font_mid.render("A mysterious egg appeared...", True, (255, 255, 255))
            self.screen.blit(title, (cx - title.get_width()//2, 80))
            self.egg.draw(self.screen)
            guide = self.font_small.render("Press ENTER to hatch the egg!", True, (255, 255, 255))
            self.screen.blit(guide, (cx - guide.get_width()//2, self.bg_rect.height - 100))
        else:
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
        info = self.font_small.render("Press F for Pet Mode / C for Clear", True, (255, 255, 0))
        self.screen.blit(info, (10, 10))

    def draw_clear(self):
        self.screen.fill((20, 80, 90))
        cx, cy = self.bg_rect.center
        pygame.draw.polygon(self.screen, (255, 255, 255), [(cx - 80, 0), (cx - 20, 0), (cx + 40, cy)])
        pygame.draw.polygon(self.screen, (255, 255, 255), [(cx + 80, 0), (cx + 20, 0), (cx - 40, cy)])
        star_color = (255, 255, 200)
        for (sx, sy) in [(200,200),(300,150),(500,180),(600,240),(250,260),(450,120)]:
            pygame.draw.circle(self.screen, star_color, (sx, sy), 4)
            pygame.draw.circle(self.screen, star_color, (sx+8, sy+4), 2)
        line_top = self.font_big.render("You are the Champion.", True, (255, 215, 0))
        self.screen.blit(line_top, (cx - line_top.get_width()//2, 80))
        line_name = self.font_small.render(f"Your partner is {self.partner.name}!", True, (255, 255, 255))
        self.screen.blit(line_name, (cx - line_name.get_width()//2, 130))
        party_y = cy + 40
        self.partner.draw_midbottom(self.screen, (cx - 80, party_y))
        hero_rect = self.player.image.get_rect()
        hero_rect.midbottom = (cx + 40, party_y)
        self.screen.blit(self.player.image, hero_rect)
        line_press = self.font_mid.render("Press ENTER to finish", True, (255, 255, 255))
        self.screen.blit(line_press, (cx - line_press.get_width()//2, party_y + 40))


# ===== 実行部分 =====
if __name__ == "__main__":
    Game().run()
