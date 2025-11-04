# main.py
import pygame
import sys
import os
import random
from typing import List
import math

# スクリプトの実行ディレクトリをカレントディレクトリに設定
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- グローバル設定 ---
USE_MANUAL_TOP_LIMIT = False
MANUAL_TOP_Y = 150
TOP_LIMIT_OFFSET = -300

# --- ユーティリティ関数 ---

def detect_top_walkable_y(bg_surf: pygame.Surface) -> int:
    """
    背景画像から、キャラクターが歩ける上端のY座標を自動検出します。
    画面中央下部（65%の位置）の色を「床の色」とみなし、
    画面中央を上からスキャンして最初に見つかった「床の色」のY座標を返します。
    """
    cx = bg_surf.get_rect().centerx
    h = bg_surf.get_height()
    sample_y = int(h * 0.65)
    
    # マップ中央下部の色を「床」の色としてサンプリング
    floor_color = bg_surf.get_at((cx, sample_y))
    
    # スキャンするX座標の範囲（中央の細い帯）
    band = range(cx - 6, cx + 7)
    
    # 画面の上から床の色を探す
    for y in range(0, sample_y + 1):
        is_floor_row = any(bg_surf.get_at((x, y)) == floor_color for x in band)
        if is_floor_row:
            return y + 2 # 見つかったY座標を返す
    return 2 # 見つからなければデフォルト値

def get_jp_font(size: int):
    """
    日本語表示用のフォントオブジェクトを取得します。
    Windows環境の標準的なフォントパスを探し、見つからなければPygame標準フォントを使います。
    """
    # Windowsの一般的な日本語フォントパス
    font_paths = ["C:/Windows/Fonts/msgothic.ttc", "C:/Windows/Fonts/meiryo.ttc"]
    for path in font_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    
    # 見つからない場合はPygameのデフォルトフォント
    return pygame.font.Font(None, size)

def draw_text(screen, text, x, y, size=36, color=(0, 0, 0)):
    """
    指定された座標に日本語テキストを描画するヘルパー関数です。
    """
    font = get_jp_font(size)
    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))

def _lerp(a, b, t):
    """線形補間: a から b へ t (0.0〜1.0) の割合で移動した値を返します。"""
    return a + (b - a) * t

def _dir(a, b):
    """
    2点間(a, b)の正規化された方向ベクトルと距離をタプルで返します。
    
    戻り値: ((dx, dy), distance)
    """
    ax, ay = a; bx, by = b
    dx, dy = (bx - ax, by - ay)
    # ゼロ除算を避けるため、距離は最低1.0とする
    d = max(1.0, math.hypot(dx, dy))
    # (正規化された方向ベクトル), (距離)
    return (dx / d, dy / d), d

# --- エフェクト・UIクラス ---

class FloatingNumber:
    """
    ダメージ量などを表示するための浮遊するテキストクラスです。
    指定時間(ttl)をかけて上昇し、徐々にフェードアウトします。
    """
    def __init__(self, text, x, y, vy=-1.0, ttl=60):
        self.text = text
        self.x, self.y = x, y
        self.vy = vy  # Y方向（上）への移動速度
        self.ttl = ttl # Time To Live (生存フレーム数)
        self.alpha = 255 # 透明度 (0-255)

    def update(self) -> bool:
        """
        座標と透明度を更新します。
        生存時間が0になったらFalseを返します。
        """
        self.y += self.vy
        self.ttl -= 1
        
        # 残り時間が少なくなったらフェードアウト開始
        if self.ttl < 20:
            self.alpha = int(255 * (self.ttl / 20))
            
        return self.ttl > 0 # 生存しているか否かを返す

    def draw(self, screen):
        """
        現在の座標と透明度でテキストを描画します。
        """
        font = get_jp_font(36)
        surf = font.render(self.text, True, (255, 255, 0)) # 黄色で描画
        surf.set_alpha(self.alpha) # 透明度を設定
        screen.blit(surf, (self.x, self.y))

class EffectBase:
    """
    すべてのバトルエフェクトの基底クラス（親クラス）です。
    """
    def __init__(self):
        self.alive = True # エフェクトが動作中かを示すフラグ

    def update(self) -> bool:
        """
        エフェクトの状態を更新します。
        エフェクトが終了したらFalseを返します。
        """
        return self.alive

    def draw(self, surf):
        """
        エフェクトを描画します。
        """
        pass

class TackleEffect(EffectBase):
    """
    「たいあたり」のエフェクトクラス。
    指定されたRect（キャラクター）を目標地点まで移動させ、元の位置に戻します。
    """
    def __init__(self, attacker_rect, src_pos, dst_center, frames=10):
        """
        attacker_rect: アニメーションさせる対象のpygame.Rect
        src_pos:       元の位置 (topleft座標)
        dst_center:    目標地点 (相手のcenter座標)
        frames:        片道にかかるフレーム数
        """
        super().__init__()
        self.attacker_rect = attacker_rect
        self.start_pos = src_pos # 攻撃開始時の座標
        
        # 相手の中心に、自分の中心が来るような目標座標(topleft)を計算
        self.target_pos = (dst_center[0] - attacker_rect.width / 2, 
                           dst_center[1] - attacker_rect.height / 2) 
        
        self.f = 0 # 経過フレームカウンタ
        self.frames_one_way = max(1, frames) # 片道のフレーム数
        self.frames_total = self.frames_one_way * 2 # 往復の総フレーム数

    def update(self):
        self.f += 1
        
        if self.f <= self.frames_one_way:
            # 1. 行き（徐々に加速するイージング）
            t = math.sin((self.f / self.frames_one_way) * (math.pi / 2)) 
            x = _lerp(self.start_pos[0], self.target_pos[0], t)
            y = _lerp(self.start_pos[1], self.target_pos[1], t)
            self.attacker_rect.topleft = (int(x), int(y))
            
        elif self.f <= self.frames_total:
            # 2. 帰り（一定速度）
            t = (self.f - self.frames_one_way) / self.frames_one_way
            x = _lerp(self.target_pos[0], self.start_pos[0], t)
            y = _lerp(self.target_pos[1], self.start_pos[1], t)
            self.attacker_rect.topleft = (int(x), int(y))
            
        else:
            # 3. 終了
            self.attacker_rect.topleft = self.start_pos # 座標を元に戻す
            self.alive = False
            
        return self.alive

    def draw(self, surf):
        # このエフェクトはattacker_rectを直接動かすため、
        # battle_sceneのメインループがキャラクターを描画する。
        # したがって、このdrawメソッドでは何もしない。
        pass

class QuickAttackEffect(EffectBase):
    """
    「でんこうせっka」のエフェクトクラス。
    始点と終点の間に、複数のジグザグな線を描画します。
    """
    def __init__(self, src, dst, frames=20):
        super().__init__()
        self.src, self.dst = src, dst
        self.f = 0
        self.frames = frames
        self.paths = [] # 描画する線の座標リスト

    def update(self):
        self.f += 1
        if self.f > self.frames:
            self.alive = False
        else:
            # 生存期間中、毎フレーム新しいジグザグのパスを生成する
            self.paths = []
            for _ in range(3): # 3本の線を生成
                pts = []
                for i in range(6): # 6つの点で構成
                    t = i / 5
                    x = _lerp(self.src[0], self.dst[0], t)
                    y = _lerp(self.src[1], self.dst[1], t) + random.randint(-10, 10) # Y軸をランダムにずらす
                    pts.append((x, y))
                self.paths.append(pts)
        return self.alive

    def draw(self, surf):
        for pts in self.paths:
            # 白と黄色の線を重ねて描画
            pygame.draw.lines(surf, (255, 255, 100), False, pts, 4)
            pygame.draw.lines(surf, (255, 255, 255), False, pts, 2)

class FlamethrowerEffect(EffectBase):
    """
    「かえんほうしゃ」のエフェクトクラス。
    パーティクル（炎と煙）を発生させます。
    """
    def __init__(self, src, dst, frames=40):
        super().__init__()
        self.src, self.dst = src, dst
        self.f, self.frames = 0, frames
        self.flames = [] # [x, y, vx, vy, life]
        self.smoke = []  # [x, y, vx, vy, life]
        self._spawn(25) # 初期パーティクル生成

    def _spawn(self, n):
        """炎パーティクルをN個生成します。"""
        (ux, uy), _ = _dir(self.src, self.dst)
        base = math.atan2(uy, ux) # ターゲットへの基本角度
        for _ in range(n):
            ang = base + random.uniform(-0.4, 0.4) # 角度をランダムにばらけさせる
            spd = random.uniform(4, 8) # 速度もランダムに
            vx, vy = math.cos(ang) * spd, math.sin(ang) * spd
            life = random.randint(20, 35) # 生存時間
            self.flames.append([self.src[0], self.src[1], vx, vy, life])

    def update(self):
        self.f += 1
        
        # 技の持続時間中、定期的に炎を追加生成
        if self.f <= self.frames and self.f % 2 == 0:
            self._spawn(5)

        # 炎パーティクルの更新
        new_flames, new_smoke = [], []
        for p in self.flames:
            p[0] += p[2]; p[1] += p[3] # 座標更新
            p[3] += 0.05 # 炎を少し上に向かせる（重力とは逆）
            p[4] -= 1    # 生存時間減少
            
            if p[4] > 0:
                new_flames.append(p)
            else:
                # 炎が消えたら、その場所に煙を生成
                new_smoke.append([p[0], p[1], random.uniform(-0.5, 0.5), -1.0, 40])
        
        self.flames = new_flames
        self.smoke = self.smoke + new_smoke # 既存の煙リストに新しい煙を追加

        # 煙パーティクルの更新
        self.smoke = [s for s in self.smoke if s[4] > 0] # 生存期間が切れた煙を削除
        for s in self.smoke:
            s[0] += s[2]; s[1] += s[3] # 座標更新
            s[4] -= 1    # 生存時間減少

        # 技の持続時間が過ぎ、かつ全てのパーティクルが消えたら終了
        if self.f > self.frames and not self.flames and not self.smoke:
            self.alive = False
        return self.alive

    def draw(self, surf):
        # 炎パーティクル（円）を描画
        for x, y, _, _, life in self.flames:
            col = (255, random.randint(100, 200), random.randint(30, 60)) # 色をランダムに
            r = max(2, int(6 * (life / 35))) # 残り寿命でサイズ変更
            pygame.draw.circle(surf, col, (int(x), int(y)), r)
            
        # 煙パーティクル（半透明の円）を描画
        for x, y, _, _, life in self.smoke:
            alpha = int(180 * (life / 40)) # 残り寿命で透明度変更
            r = int(8 * (life / 40))
            # 透過サーフェスを作成してアルファブレンディング
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (80, 80, 80, alpha), (r, r), r)
            surf.blit(s, (x - r, y - r))

class WaterGunEffect(EffectBase):
    """
    「みずでっぽう」のエフェクトクラス。
    始点から終点への線と、飛び散る水しぶき（パーティクル）を描画します。
    """
    def __init__(self, src, dst, frames=45):
        super().__init__()
        self.src, self.dst, self.f, self.frames = src, dst, 0, frames
        self.drops = [] # 水しぶきパーティクル [x, y, vx, vy, life]

    def update(self):
        self.f += 1
        (ux, uy), dist = _dir(self.src, self.dst)
        
        # 技の持続時間中、水しぶきを生成
        if self.f <= self.frames:
            for _ in range(8):
                # 水の線上のランダムな位置から発生
                rand_dist = random.uniform(0, dist)
                px = self.src[0] + ux * rand_dist
                py = self.src[1] + uy * rand_dist
                
                # 進行方向をベースに、ランダムに速度を散らす
                vx = ux * random.uniform(3, 5) + random.uniform(-0.8, 0.8)
                vy = uy * random.uniform(3, 5) + random.uniform(-0.8, 0.8)
                life = random.randint(10, 25)
                self.drops.append([px, py, vx, vy, life])

        # 水しぶきパーティクルを更新
        self.drops = [[x + vx, y + vy, vx, vy, life - 1] 
                      for x, y, vx, vy, life in self.drops if life > 1]
        
        # 技の持続時間が過ぎ、かつ全てのパーティクルが消えたら終了
        if self.f > self.frames and not self.drops:
            self.alive = False
        return self.alive

    def draw(self, surf):
        # 水流の本体（太い線と細い線）
        pygame.draw.line(surf, (100, 200, 255), self.src, self.dst, 10)
        pygame.draw.line(surf, (220, 245, 255), self.src, self.dst, 4)
        
        # 水しぶき（円）を描画
        for x, y, _, _, life in self.drops:
            r = max(1, int(3 * (life / 20))) # 残り寿命でサイズ変更
            pygame.draw.circle(surf, (170, 220, 255), (int(x), int(y)), r)

# --- ゲームシーン ---

def battle_scene(screen, enemy_name="ボス"):
    """
    バトルシーンのメインループです。
    """
    clock = pygame.time.Clock()
    W, H = 1024, 768
    
    # --- アセットの読み込み ---
    bg = pygame.transform.scale(pygame.image.load("battle_bg.png").convert(), (W, H))
    player_poke = pygame.transform.scale(pygame.image.load("9.png").convert_alpha(), (200, 200))
    enemy_poke = pygame.transform.scale(pygame.image.load("9.png").convert_alpha(), (200, 200))
    
    # --- オブジェクトの初期化 ---
    player_rect = player_poke.get_rect(bottomleft=(200, 550))
    enemy_rect = enemy_poke.get_rect(topleft=(500, 150))
    
    effects: List[EffectBase] = [] # 実行中のエフェクトリスト
    floating: List[FloatingNumber] = [] # 表示中のダメージテキストリスト

    player_hp = enemy_hp = 100
    commands = [("たいあたり", 10), ("かえんほうしゃ", 25), ("でんこうせっか", 15), ("みずでっぽう", 20)]
    selected = 0 # 選択中のコマンドインデックス
    turn = "player" # 現在のターン
    message = f"{enemy_name} が あらわれた！"

    while True:
        # --- 1. イベント処理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.KEYDOWN and turn == "player":
                # プレイヤーのターンのみキー入力を受け付ける
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(commands)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(commands)
                elif event.key == pygame.K_RETURN:
                    # 技の決定
                    move, dmg = commands[selected]
                    
                    if move == "たいあたり":
                        # TackleEffectはRectを直接操作するため、特別な引数を渡す
                        effects.append(TackleEffect(player_rect, player_rect.topleft, enemy_rect.center, frames=10))
                    else:
                        # 他のエフェクトは始点と終点の座標を渡す
                        src = (player_rect.right - 20, player_rect.top + 40)
                        dst = (enemy_rect.left + 20, enemy_rect.top + 40)
                        if move == "でんこうせっか":
                            effects.append(QuickAttackEffect(src, dst))
                        elif move == "かえんほうしゃ":
                            effects.append(FlamethrowerEffect(src, dst))
                        elif move == "みずでっぽう":
                            effects.append(WaterGunEffect(src, dst))
                    
                    # ダメージ処理とメッセージ更新
                    enemy_hp -= dmg
                    message = f"{move}！ {dmg} ダメージ！"
                    floating.append(FloatingNumber(str(dmg), enemy_rect.centerx, enemy_rect.top))
                    
                    if enemy_hp <= 0:
                        return "win" # 勝利
                    
                    turn = "enemy" # ターンを敵に渡す

        # --- 2. ゲームロジック更新 ---
        
        if turn == "enemy":
            # 敵のターン処理
            pygame.time.delay(600) # 少し待機
            dmg = random.randint(8, 22)
            player_hp -= dmg
            message = f"{enemy_name} の こうげき！ {dmg} ダメージ！"
            floating.append(FloatingNumber(str(dmg), player_rect.centerx, player_rect.top))
            
            if player_hp <= 0:
                return "lose" # 敗北
                
            turn = "player" # ターンをプレイヤーに戻す

        # エフェクトとダメージテキストの生存確認と更新
        floating = [f for f in floating if f.update()]
        effects = [e for e in effects if e.update()]

        # --- 3. 描画処理 ---
        temp = pygame.Surface((W, H), pygame.SRCALPHA)
        temp.blit(bg, (0, 0))
        
        # キャラクター描画
        # (TackleEffectがplayer_rectを直接更新していることに注意)
        temp.blit(player_poke, player_rect) 
        temp.blit(enemy_poke, enemy_rect)
        
        # UI（メッセージウィンドウ）
        pygame.draw.rect(temp, (255, 255, 255), (50, 400, 700, 230))
        pygame.draw.rect(temp, (0, 0, 0), (50, 400, 700, 230), 3)
        draw_text(temp, message, 80, 420, 28)
        
        # UI（コマンドリスト）
        if turn == "player":
            for i, (cmd, _) in enumerate(commands):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                draw_text(temp, cmd, 100, 460 + i * 35, 28, color)
        
        # エフェクトとダメージテキストの描画
        for f in floating: f.draw(temp)
        for ef in effects: ef.draw(temp)

        # 最終的な描画を画面に反映
        screen.blit(temp, (0, 0))
        pygame.display.flip()
        
        # フレームレート制御
        clock.tick(60)

def show_result(screen, result):
    """
    勝敗結果を表示するシーンです。
    Enterキーが押されるまでループします。
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()
    
    # 結果に応じて背景色とテキストを決定
    if result == "win":
        color, text = ((30, 160, 80), "勝利！")
    else:
        color, text = ((160, 40, 40), "敗北…")

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Enterキーでシーンを終了し、フィールドマップに戻る
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return

        screen.fill(color)
        draw_text(screen, text, W // 2 - 80, H // 2 - 40, 72, (255, 255, 255))
        draw_text(screen, "Enterで戻る", W // 2 - 100, H // 2 + 40, 36, (255, 255, 255))
        
        pygame.display.flip()
        clock.tick(30)

def main():
    """
    ゲームのメインエントリーポイント（フィールドマップシーン）。
    """
    pygame.init()
    
    # ★ 修正点: .convert() のために一時的な画面モードを設定
    pygame.display.set_mode((1, 1)) 

    # --- アセットの読み込み ---
    bg_img = pygame.image.load("background.png").convert()
    bw, bh = bg_img.get_size()
    
    # 画面サイズを背景画像に合わせる
    screen = pygame.display.set_mode((bw, bh))
    pygame.display.set_caption("ポケットコウカトン")

    # プレイヤー画像の読み込み
    player_down_img = pygame.image.load("player_down.png").convert_alpha()
    player_left_img = pygame.image.load("player_side_left.png").convert_alpha()
    player_right_img = pygame.transform.flip(player_left_img, True, False) # 右向きは左の反転

    # プレイヤー画像をスケーリング
    player_scale = 0.1
    pw, ph = player_down_img.get_size()
    new_size = (int(pw * player_scale), int(ph * player_scale))
    player_down_img = pygame.transform.scale(player_down_img, new_size)
    player_left_img = pygame.transform.scale(player_left_img, new_size)
    player_right_img = pygame.transform.scale(player_right_img, new_size)

    # 画像スケーリング用のヘルパー関数
    def scale_img(img, s):
        w, h = img.get_size()
        return pygame.transform.scale(img, (int(w * s), int(h * s)))

    # ボス画像の読み込みとスケーリング
    boss_yellow_img = scale_img(pygame.image.load("boss_yellow.png").convert_alpha(), 0.2)
    boss_red_img = scale_img(pygame.image.load("boss_red.png").convert_alpha(), 0.2)
    boss_white_img = scale_img(pygame.image.load("boss_white.png").convert_alpha(), 0.18)

    # --- オブジェクトの初期化 ---
    bosses = [
        {"name": "イエローボス", "img": boss_yellow_img, "rect": boss_yellow_img.get_rect(topleft=(200, 200)), "alive": True},
        {"name": "レッドボス", "img": boss_red_img, "rect": boss_red_img.get_rect(topleft=(400, 200)), "alive": True},
        {"name": "ブルーボス", "img": boss_white_img, "rect": boss_white_img.get_rect(topleft=(600, 180)), "alive": True},
    ]

    player_img = player_down_img
    player_rect = player_img.get_rect(topleft=(465, 600)) # 初期位置
    
    # プレイヤーが移動できるY座標の上限を決定
    if USE_MANUAL_TOP_LIMIT:
        top_limit = MANUAL_TOP_Y
    else:
        top_limit = max(0, detect_top_walkable_y(bg_img) + TOP_LIMIT_OFFSET)

    clock = pygame.time.Clock()
    speed = 4

    # --- メインループ (フィールド) ---
    while True:
        # --- 1. イベント処理 ---
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # --- 2. ゲームロジック更新 ---
        
        # キー入力に基づくプレイヤーの移動
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx, player_img = -speed, player_left_img
        elif keys[pygame.K_RIGHT]:
            dx, player_img = speed, player_right_img
        elif keys[pygame.K_UP]:
            dy, player_img = -speed, player_down_img
        elif keys[pygame.K_DOWN]:
            dy, player_img = speed, player_down_img

        player_rect.x += dx
        player_rect.y += dy
        
        # プレイヤーが画面外に出ないように制限
        player_rect.clamp_ip(bg_img.get_rect())
        # プレイヤーが設定された上限より上に行かないように制限
        if player_rect.top < top_limit:
            player_rect.top = top_limit

        # ボスとの当たり判定
        for boss in bosses:
            if boss["alive"] and player_rect.colliderect(boss["rect"]):
                # 衝突したらバトルシーンへ移行
                result = battle_scene(screen, boss["name"])
                
                # バトルシーン終了後、結果を表示
                show_result(screen, result)
                
                if result == "win":
                    boss["alive"] = False # 勝利したらボスを非表示に
                    
                # バトル終了後、プレイヤーを初期位置に戻す
                player_rect.topleft = (465, 600)

        # --- 3. 描画処理 ---
        screen.blit(bg_img, (0, 0))
        
        # 生きているボスのみを描画
        for boss in bosses:
            if boss["alive"]:
                screen.blit(boss["img"], boss["rect"])
                
        screen.blit(player_img, player_rect)
        
        pygame.display.flip()
        
        # フレームレート制御
        clock.tick(60)


if __name__ == "__main__":
    main()