import pygame
import sys
import os
import random
from typing import List, Tuple

# === 実行ディレクトリ固定（講義指定：提出時に必須） ===
# これを入れておくと、Python実行時に画像ファイルなどのパスが
# スクリプトと同じフォルダ内から正しく読み込まれるようになる。
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# === 定数設定 ===
# 手動で上方向の移動制限を設定するか、自動検出にするかを選べる。
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150              # 手動設定時に使う上方向の限界Y座標
TOP_LIMIT_OFFSET = -300         # 自動検出結果に対して上方向へ追加オフセット


# === 地面（歩行可能範囲）を検出する関数 ===
def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """
    背景画像を走査して、プレイヤーが立てる最上位置（地面Y座標）を自動検出する。
    ・背景の中央付近を走査し、「床」と同じ色を持つ最上行を探す。
    ・これにより背景画像が変わっても自動で上限を判定できる。
    """
    cx = bg_surf.get_rect().centerx
    h = bg_surf.get_height()

    # 背景中央付近の床色を取得（例：緑や灰色など）
    sample_y = int(h * 0.65)
    floor_color = bg_surf.get_at((cx, sample_y))

    # 中央付近（±6px）をスキャンして床の始まりを見つける
    band = range(max(0, cx - 6), min(bg_surf.get_width(), cx + 7))
    for y in range(0, sample_y + 1):
        # 1行でも床色があればそこを地面とみなす
        if any(bg_surf.get_at((x, y)) == floor_color for x in band):
            return y + 2  # +2はキャラのめり込み防止
    return 2  # 見つからなかった場合の安全値


# === 日本語フォントを安全に読み込む関数 ===
def get_jp_font(size: int) -> pygame.font.Font:
    """
    OSによって異なる日本語フォントを優先的に読み込む。
    存在しない場合はpygame標準フォントを使う。
    """
    font_paths = [
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


# === 日本語テキストを画面に描画する関数 ===
def draw_text(screen: pygame.Surface, text: str, x: int, y: int,
              size: int = 28, color=(0, 0, 0)) -> None:
    """
    任意の位置に日本語文字列を描画する。
    pygame標準フォントは日本語非対応なので、上で取得したフォントを使用。
    """
    font = get_jp_font(size)
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))


# === 浮遊する数値（ダメージ値など）を管理するクラス ===
class FloatingNumber:
    """戦闘中のダメージ値を上方向に浮かせて表示・フェードアウトさせるクラス"""

    def __init__(self, text: str, pos: Tuple[int, int], vy: float = -1.0, ttl: int = 60):
        # text：表示する文字（ダメージ数値など）
        # pos：初期表示位置（x, y）
        # vy：上昇速度、ttl：寿命（フレーム数）
        self.text = text
        self.x, self.y = pos
        self.vy = vy
        self.ttl = ttl
        self.alpha = 255  # 不透明度（寿命が尽きるにつれ減少）

    def update(self) -> bool:
        """位置と寿命を更新。寿命が尽きたらFalseを返して削除される。"""
        self.y += self.vy
        self.ttl -= 1
        # 寿命が20以下になると徐々に透明化
        if self.ttl < 20:
            self.alpha = int(255 * (self.ttl / 20))
        return self.ttl > 0

    def draw(self, screen: pygame.Surface):
        """現在位置に半透明でテキストを描画する。"""
        font = get_jp_font(36)
        surf = font.render(self.text, True, (255, 255, 0))
        surf.set_alpha(self.alpha)
        screen.blit(surf, (self.x, self.y))


# === プレイヤークラス ===
class Player:
    """プレイヤーキャラクター（コウカトン）の管理クラス"""

    def __init__(self, x: int, y: int):
        # 各方向ごとの画像をロード
        self.images = {
            "down": pygame.image.load("player_down.png").convert_alpha(),
            "left": pygame.image.load("player_side_left.png").convert_alpha(),
            "right": pygame.transform.flip(pygame.image.load("player_side_left.png"), True, False)
        }

        # スケーリング（縮小率）
        self.scale = 0.1
        self.images = {k: pygame.transform.scale(v, self.scaled_size(v)) for k, v in self.images.items()}

        # 初期画像と位置
        self.image = self.images["down"]
        self.rect = self.image.get_rect(topleft=(x, y))

    def scaled_size(self, img: pygame.Surface) -> Tuple[int, int]:
        """元画像のスケーリング後サイズを返す"""
        w, h = img.get_size()
        return int(w * self.scale), int(h * self.scale)

    def move(self, keys, speed: int, top_limit: int, bounds: pygame.Rect):
        """キー入力に応じて移動方向と座標を更新"""
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx = -speed
            self.image = self.images["left"]
        elif keys[pygame.K_RIGHT]:
            dx = speed
            self.image = self.images["right"]
        elif keys[pygame.K_UP]:
            dy = -speed
            self.image = self.images["down"]  # 上画像がないためdownを代用
        elif keys[pygame.K_DOWN]:
            dy = speed
            self.image = self.images["down"]

        # 移動と範囲制限
        self.rect.x += dx
        self.rect.y += dy
        self.rect.clamp_ip(bounds)
        if self.rect.top < top_limit:
            self.rect.top = top_limit

    def draw(self, screen: pygame.Surface):
        """現在位置にプレイヤーを描画"""
        screen.blit(self.image, self.rect)


# === ボス（敵）クラス ===
class Boss:
    """各ボス（敵）キャラクターを管理するクラス"""

    def __init__(self, name: str, img_path: str, scale: float, x: int, y: int):
        self.name = name
        img = pygame.image.load(img_path).convert_alpha()
        w, h = img.get_size()
        self.image = pygame.transform.scale(img, (int(w * scale), int(h * scale)))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.alive = True  # 撃破されたかどうか

    def draw(self, screen: pygame.Surface):
        """生存中のみ描画"""
        if self.alive:
            screen.blit(self.image, self.rect)


# === 戦闘シーン関数 ===
def battle_scene(screen: pygame.Surface, enemy_name: str) -> str:
    """
    プレイヤーと敵が交互に攻撃するターン制バトル。
    勝利時は "win"、敗北時は "lose" を返す。
    """
    W, H = 800, 600
    clock = pygame.time.Clock()

    # まず仮のウィンドウを作成してconvert()エラーを防ぐ
    pygame.display.set_mode((W, H))

    # 背景・キャラ画像の読み込みと整形
    bg = pygame.transform.scale(pygame.image.load("battle_bg.png"), (W, H))
    player_img = pygame.transform.scale(pygame.image.load("player_poke.png"), (200, 200))
    enemy_img = pygame.transform.scale(pygame.image.load("enemy_poke.png"), (200, 200))
    player_rect = player_img.get_rect(bottomleft=(200, 550))
    enemy_rect = enemy_img.get_rect(topleft=(500, 150))

    # HPやコマンドの初期化
    player_hp, enemy_hp = 100, 100
    commands = [("たいあたり", 10), ("かえんほうしゃ", 25), ("でんこうせっか", 15), ("みずでっぽう", 20)]
    selected = 0
    turn = "player"
    message = f"{enemy_name} が あらわれた！"
    floating: List[FloatingNumber] = []

    # === 戦闘メインループ ===
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN and turn == "player":
                # コマンド選択（上下キーで切り替え）
                if e.key == pygame.K_UP:
                    selected = (selected - 1) % len(commands)
                elif e.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(commands)
                elif e.key == pygame.K_RETURN:
                    # Enterキーで攻撃実行
                    move, dmg = commands[selected]
                    enemy_hp -= dmg
                    message = f"{move}！ {dmg} ダメージ！"
                    floating.append(FloatingNumber(str(dmg), enemy_rect.midtop))
                    if enemy_hp <= 0:
                        return "win"  # 勝利
                    turn = "enemy"  # ターン交代

        # 敵のターン処理
        if turn == "enemy":
            pygame.time.delay(600)
            dmg = random.randint(8, 22)
            player_hp -= dmg
            message = f"{enemy_name} の こうげき！ {dmg} ダメージ！"
            floating.append(FloatingNumber(str(dmg), player_rect.midtop))
            if player_hp <= 0:
                return "lose"  # 敗北
            turn = "player"

        # エフェクト更新
        floating = [f for f in floating if f.update()]

        # 描画処理（背景、HPバー、メッセージ、コマンド）
        temp = pygame.Surface((W, H))
        temp.blit(bg, (0, 0))
        temp.blit(player_img, player_rect)
        temp.blit(enemy_img, enemy_rect)
        pygame.draw.rect(temp, (255, 0, 0), (80, 340, max(0, player_hp * 2), 20))
        pygame.draw.rect(temp, (255, 0, 0), (500, 80, max(0, enemy_hp * 2), 20))
        draw_text(temp, message, 80, 420, 26)

        # プレイヤーの選択肢表示（赤が選択中）
        if turn == "player":
            for i, (cmd, _) in enumerate(commands):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                draw_text(temp, cmd, 100, 450 + i * 30, 24, color)

        # ダメージ浮遊エフェクト
        for f in floating:
            f.draw(temp)

        # 画面更新
        screen.blit(temp, (0, 0))
        pygame.display.flip()
        clock.tick(60)


# === 勝利／敗北画面 ===
def show_result(screen: pygame.Surface, result: str):
    """戦闘後に勝利・敗北画像を表示"""
    W, H = 800, 600
    pygame.display.set_mode((W, H))
    img = pygame.transform.scale(
        pygame.image.load("win.png" if result == "win" else "lose.png"), (W, H))
    clock = pygame.time.Clock()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return  # Enterで戻る

        # 背景画像＋メッセージ描画
        screen.blit(img, (0, 0))
        draw_text(screen, "Enterで戻る", 300, 500, 30, (255, 255, 255))
        pygame.display.flip()
        clock.tick(30)


# === メイン関数（全体制御） ===
def main():
    """ゲーム全体の流れを制御するメインループ"""
    pygame.init()

    # convert()前に仮ディスプレイを作成（エラー防止）
    pygame.display.set_mode((1, 1))

    # 背景画像読み込みと画面サイズ設定
    bg = pygame.image.load("background.png").convert()
    bw, bh = bg.get_size()
    screen = pygame.display.set_mode((bw, bh))
    pygame.display.set_caption("ポケットコウカトン")

    # プレイヤーとボスの生成
    player = Player(465, 600)
    bosses = [
        Boss("イエローボス", "boss_yellow.png", 0.2, 200, 200),
        Boss("レッドボス", "boss_red.png", 0.2, 400, 200),
        Boss("ホワイトボス", "boss_white.png", 0.18, 600, 180),
    ]

    # 上方向の移動上限を自動または手動で設定
    top_limit = MANUAL_TOP_Y if USE_MANUAL_TOP_LIMIT else max(0, detect_top_walkable_y(bg) + TOP_LIMIT_OFFSET)

    clock = pygame.time.Clock()
    speed = 4  # プレイヤー移動速度

    # === メインゲームループ ===
    while True:
        # イベント処理（終了キー対応）
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # プレイヤー移動
        keys = pygame.key.get_pressed()
        player.move(keys, speed, top_limit, bg.get_rect())

        # ボスと衝突したらバトル開始
        collided = next((b for b in bosses if b.alive and player.rect.colliderect(b.rect)), None)
        if collided:
            result = battle_scene(screen, collided.name)
            show_result(screen, result)
            if result == "win":
                collided.alive = False  # 撃破処理
            # プレイヤーを初期位置に戻す
            player.rect.topleft = (465, 600)

        # 背景＋キャラ描画
        screen.blit(bg, (0, 0))
        for b in bosses:
            b.draw(screen)
        player.draw(screen)
        pygame.display.flip()
        clock.tick(60)


# === エントリーポイント ===
if __name__ == "__main__":
    main()
