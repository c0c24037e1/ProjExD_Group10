import pygame
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 上限（上方向の到達位置）設定
USE_MANUAL_TOP_LIMIT = False  # True: MANUAL_TOP_Y を使う / False: 背景から自動検出
MANUAL_TOP_Y = 150  # 手動で決める最小 top 座標（小さいほど上へ行ける）
TOP_LIMIT_OFFSET = -300  # 自動検出値に加えるオフセット（負でさらに上へ行ける）


def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """
    背景画像の中央付近の床色を基準に、
    画面中央の細い帯（±6px）を上方向へスキャンして
    「床が始まる最上端」の y を返す（プレイヤーrect.topの最小値に使う）。

    ※ドット絵など床と壁の色がはっきり分かれている前提の簡易版。
    """
    cx = bg_surf.get_rect().centerx
    h = bg_surf.get_height()

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


# ===========================
# モンスタークラス（仮実装）
# ===========================
class Monster:
    def __init__(self, name, max_hp):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.status = None  # None, "Poison", "Paralysis", など

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.max_hp)

    def status_heal(self):
        self.status = None


# ===========================
# インベントリークラス
# ===========================
class Inventory:
    """
    Bキーを押すとインベントリ画面が開き、バッグ、キーアイテム、モンスターの3つのタブが出てくる。
    ポーションを選択すると回復、解毒、異常状態回復の3つが選べ、使う事でその効果をモンスターに与える事ができる。
    モンスタータブではモンスターのHPや状態を確認する事ができる。
    """

    def __init__(self, screen: pygame.Surface, monster: Monster) -> None:
        self.screen = screen
        self.monster = monster

        self.bg_img = pygame.image.load("インベントリ背景画像.png").convert()
        self.bg_img = pygame.transform.scale(self.bg_img, (800, 600))
        self.bg_rect = self.bg_img.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

        self.font_tab = pygame.font.Font(None, 50)
        self.font_item = pygame.font.Font(None, 40)

        self.tabs = ["Bag", "Key Items", "Monster"]
        self.items = {
            "Bag": ["Potion", "Items"],
            "Key Items": ["Bicycle", "Map", "Coin"]
        }

        self.current_tab = 0
        self.cursor = 0

    # ==== 共通：メッセージ表示関数 ====
    def show_message(self, text: str, delay=800):
        """中央下に小さめの黒背景＋白文字でメッセージを表示"""
        # 背景サイズ（画面幅の7割、縦100px程度）
        msg_width = int(self.screen.get_width() * 0.7)
        msg_height = 100

        # 背景の位置（画面中央）
        msg_x = (self.screen.get_width() - msg_width) // 2
        msg_y = (self.screen.get_height() - msg_height) // 2

        # 半透明黒背景を作成（より黒く、透明度220/255）
        overlay = pygame.Surface((msg_width, msg_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))  # ← 透明度を上げることでより黒く

        # テキストを白で描画
        font = pygame.font.Font(None, 36)
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(msg_width // 2, msg_height // 2))

        # 背景を描画
        self.screen.blit(overlay, (msg_x, msg_y))
        self.screen.blit(text_surface, (msg_x + text_rect.x, msg_y + text_rect.y))

        pygame.display.flip()
        pygame.time.delay(delay)


    def open(self) -> None:
        """インベントリ画面を開く"""
        pygame.mixer.music.play(loops = -1)
        while True:
            self.draw()
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_b, pygame.K_ESCAPE]:
                        pygame.mixer.music.stop()
                        return
                    elif event.key == pygame.K_RIGHT:
                        self.current_tab = (self.current_tab + 1) % len(self.tabs)
                        self.cursor = 0
                    elif event.key == pygame.K_LEFT:
                        self.current_tab = (self.current_tab - 1) % len(self.tabs)
                        self.cursor = 0
                    elif event.key == pygame.K_DOWN:
                        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
                            current_items = self.items[self.tabs[self.current_tab]]
                            if len(current_items) > 1:
                                self.cursor = (self.cursor + 1) % len(current_items)
                    elif event.key == pygame.K_UP:
                        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
                            current_items = self.items[self.tabs[self.current_tab]]
                            if len(current_items) > 1:
                                self.cursor = (self.cursor - 1) % len(current_items)
                    elif event.key == pygame.K_RETURN:
                        self.select_item()

    def draw(self) -> None:
        """インベントリの描画"""
        self.screen.blit(self.bg_img, self.bg_rect.topleft)

        # タブ描画
        for i, tab in enumerate(self.tabs):
            color = (255, 255, 0) if i == self.current_tab else (200, 200, 200)
            tab_text = self.font_tab.render(tab, True, color)
            tab_x = self.bg_rect.left + 50 + i * 200
            tab_y = self.bg_rect.top + 20
            self.screen.blit(tab_text, (tab_x, tab_y))

        # アイテム描画
        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
            current_items = self.items[self.tabs[self.current_tab]]
            for i, item in enumerate(current_items):
                color = (255, 255, 255) if i == self.cursor else (150, 150, 150)
                item_text = self.font_item.render(item, True, color)
                self.screen.blit(item_text, (self.bg_rect.left + 100, self.bg_rect.top + 100 + i * 50))

        elif self.tabs[self.current_tab] == "Monster":
            m = self.monster
            color = (255, 255, 255)
            self.screen.blit(self.font_item.render(m.name, True, color), (self.bg_rect.left + 50, self.bg_rect.top + 100))
            self.screen.blit(self.font_item.render(f"HP: {m.hp}/{m.max_hp}", True, color),
                             (self.bg_rect.left + 50, self.bg_rect.top + 130))
            self.screen.blit(self.font_item.render(f"Status: {m.status if m.status else 'Normal'}", True, color),
                             (self.bg_rect.left + 50, self.bg_rect.top + 160))

    def select_item(self) -> None:
        """選択中のアイテムを使用"""
        if self.tabs[self.current_tab] in ["Bag", "Key Items"]:
            current_items = self.items[self.tabs[self.current_tab]]
            selected_item = current_items[self.cursor]
            if selected_item == "Potion":
                self.potion_select()
            else:
                self.draw()
                self.show_message(f"{selected_item} is not implemented yet!", delay=800)

    def potion_select(self) -> None:
        """ポーション選択と使用（ESC/Bで一段階戻る）"""
        potions = ["Heal Potion", "Antidote", "Status Heal"]
        cursor = 0
        font = pygame.font.Font(None, 40)

        while True:
            self.screen.blit(self.bg_img, self.bg_rect.topleft)
            self.draw()

            for i, potion in enumerate(potions):
                color = (255, 255, 255) if i == cursor else (150, 150, 150)
                self.screen.blit(font.render(potion, True, color),
                                 (self.bg_rect.left + 300, self.bg_rect.top + 100 + i * 50))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_b]:
                        return
                    elif event.key == pygame.K_RETURN:
                        potion_name = potions[cursor]
                        if potion_name == "Heal Potion":
                            self.monster.heal(50)
                        elif potion_name == "Antidote":
                            if self.monster.status == "Poison":
                                self.monster.status_heal()
                        elif potion_name == "Status Heal":
                            self.monster.status_heal()
                        self.draw()
                        self.show_message(f"Used {potion_name} on {self.monster.name}!", delay=800)
                        return
                    elif event.key == pygame.K_UP:
                        cursor = (cursor - 1) % len(potions)
                    elif event.key == pygame.K_DOWN:
                        cursor = (cursor + 1) % len(potions)


# ===========================
# メイン処理
# ===========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Top View Demo")

    # ===== 背景読み込み =====
    bg_img = pygame.image.load("background.png").convert()
    bg_scale = 1
    bw, bh = bg_img.get_size()
    bg_img = pygame.transform.scale(bg_img, (int(bw * bg_scale), int(bh * bg_scale)))
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
    boss_yellow_img = pygame.image.load("boss_yellow.png").convert_alpha()
    boss_red_img = pygame.image.load("boss_red.png").convert_alpha()
    boss_white_img = pygame.image.load("boss_white.png").convert_alpha()

    boss_yellow_img = pygame.transform.scale(boss_yellow_img, (100, 100))
    boss_red_img = pygame.transform.scale(boss_red_img, (100, 100))
    boss_white_img = pygame.transform.scale(boss_white_img, (100, 100))

    boss_yellow_rect = boss_yellow_img.get_rect(topleft=(200, 200))
    boss_red_rect = boss_red_img.get_rect(topleft=(400, 200))
    boss_white_rect = boss_white_img.get_rect(topleft=(600, 180))

    # ===== プレイヤー初期位置 =====
    player_rect = player_down_img.get_rect()
    player_rect.topleft = (465, 600)
    player_img = player_down_img

    # ===== 上方向の移動上限 =====
    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        auto_top = detect_top_walkable_y(bg_img)
        top_limit = max(0, auto_top + TOP_LIMIT_OFFSET)

    clock = pygame.time.Clock()
    speed = 4

    # 以下追加コード
    monster = Monster("Dragon", 200)
    monster.status = "Poison"
    inventory = Inventory(screen, monster)
    pygame.mixer.music.load("poke_center.wav")  # BGMファイル読み込み

    # ===== メインループ =====
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Bキーでインベントリを開く
            if event.type == pygame.KEYDOWN and event.key == pygame.K_b:
                inventory.open()

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

        # 画面外に出ないよう制限
        player_rect.clamp_ip(bg_rect)

        # 上方向の上限適用
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
