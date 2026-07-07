"""
DAF OS Quest98 — Pillow Renderer

Quest90〜96で services/asset_generator_service.py に直接書かれていた
Pillow描画処理（表情・胴体・装飾・文字レイアウト等）をそのまま移設した
モジュール。services/image_generation_service.py が「現在の設定で
使うRenderer」として選択し、render_stamp() / render_icon() を呼び出す。

Asset Generatorはこのモジュールを直接importしない（Image Generation
Serviceを経由する）。将来 openai_renderer.py / google_renderer.py /
flux_renderer.py / stability_renderer.py を同じインターフェース
（render_stamp / render_icon）で追加する想定（Quest98では未実装）。

画像生成APIは使わない。Pillowで仮画像（プレースホルダー）を生成する
（Quest90からの方針を継続）。
"""

from pathlib import Path

RENDERER_ID = "pillow"
RENDERER_DISPLAY_NAME = "Pillow Renderer"

_STAMP_SIZE = (370, 320)

# 日本語（かな漢字）を描画できるフォント候補。上から順に試し、
# 使えるものが無ければPillowのデフォルトフォントにフォールバックする。
_FONT_CANDIDATES = [
    "/System/Library/Fonts/AquaKana.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

# Quest94 v2：スタンプごとのバリエーション（画像生成APIは使わず、Pillowのみで
# 表情・文字レイアウト・装飾を組み合わせて視覚的な差を出す）。
_EXPRESSIONS = ["normal", "smile", "sleepy", "surprised", "worried", "cheer", "sorry", "joy"]
_LAYOUTS = ["bottom_center", "top_center", "speech_bubble", "diagonal", "large_text", "two_line"]
_DECORATIONS = ["heart", "star", "note", "teardrop", "sparkle", "bg_circle", "pawprint"]

# Quest95 v3：フレーズの意味に合わせた（表情, 装飾, レイアウト）の明示的な割り当て。
# services/asset_generator_service._PHRASESの40件すべてをカバーする。ここに無い
# フレーズは_style_for_phrase()がQuest94のindexベース周期割り当てへフォールバックする。
_PHRASE_STYLES: dict[str, tuple[str, str, str]] = {
    "おはよう": ("smile", "sparkle", "top_center"),
    "こんにちは": ("smile", "sparkle", "top_center"),
    "ありがとう": ("smile", "heart", "bottom_center"),
    "だいすき": ("smile", "heart", "bottom_center"),
    "よろしくね": ("smile", "heart", "bottom_center"),
    "おやすみ": ("sleepy", "moon", "bottom_center"),
    "眠いよ": ("sleepy", "moon", "bottom_center"),
    "ゆっくりしてね": ("sleepy", "moon", "two_line"),
    "ごめんね": ("sorry", "teardrop", "speech_bubble"),
    "気をつけてね": ("worried", "teardrop", "speech_bubble"),
    "がんばれ": ("cheer", "star", "diagonal"),
    "応援してるよ": ("cheer", "star", "diagonal"),
    "頑張ろう": ("cheer", "star", "diagonal"),
    "まかせて": ("cheer", "star", "diagonal"),
    "大丈夫？": ("worried", "none", "speech_bubble"),
    "無理しないで": ("worried", "teardrop", "speech_bubble"),
    "おめでとう": ("joy", "sparkle", "large_text"),
    "すごいね": ("joy", "sparkle", "large_text"),
    "さすが！": ("joy", "sparkle", "large_text"),
    "楽しみ！": ("joy", "sparkle", "large_text"),
    "うれしい": ("joy", "heart", "bottom_center"),
    "嬉しいな": ("joy", "heart", "bottom_center"),
    "たのしい": ("joy", "sparkle", "speech_bubble"),
    "よし！": ("cheer", "star", "large_text"),
    "散歩いこう": ("cheer", "pawprint", "two_line"),
    "ごはんまだ？": ("worried", "pawprint", "speech_bubble"),
    "お腹すいた": ("worried", "pawprint", "two_line"),
    "元気だよ": ("cheer", "star", "two_line"),
    "待ってるよ": ("normal", "heart", "bottom_center"),
    "おつかれさま": ("smile", "teardrop", "bottom_center"),
    "了解です": ("normal", "none", "top_center"),
    "OK!": ("normal", "star", "large_text"),
    "またね": ("smile", "star", "top_center"),
    "わかった": ("normal", "star", "top_center"),
    "なるほど": ("normal", "none", "top_center"),
    "いってきます": ("smile", "pawprint", "two_line"),
    "ただいま": ("smile", "heart", "bottom_center"),
    "おかえり": ("smile", "heart", "bottom_center"),
    "また明日": ("smile", "star", "top_center"),
    "だいじょうぶ": ("smile", "heart", "bottom_center"),
}


def _style_for_phrase(phrase: str, index: int) -> tuple[str, str, str]:
    """
    Quest95：フレーズの意味に合わせて（表情, 装飾, レイアウト）を選ぶ。
    _PHRASE_STYLESに登録が無いフレーズは、Quest94のindexベース周期割り当て
    （表情8種・レイアウト6種・装飾7種）へフォールバックする（例外を投げない）。
    """
    style = _PHRASE_STYLES.get(phrase)
    if style:
        return style
    return (
        _EXPRESSIONS[index % len(_EXPRESSIONS)],
        _DECORATIONS[index % len(_DECORATIONS)],
        _LAYOUTS[index % len(_LAYOUTS)],
    )


def _load_font(size: int):
    from PIL import ImageFont
    for path in _FONT_CANDIDATES:
        try:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_body(draw, cx: float, cy: float, radius: float, expression: str) -> None:
    """
    Quest95：頭だけの丸アイコン感を減らすため、胴体・しっぽ・前足を追加する。
    expression=="cheer"の場合のみ前足を顔の横まで上げる（応援ポーズ）。
    """
    body_fill = (255, 224, 178, 255)
    outline = (120, 90, 60, 255)

    body_top = cy + radius * 0.62
    body_w = radius * 1.7
    body_h = radius * 0.85
    draw.ellipse(
        [cx - body_w / 2, body_top, cx + body_w / 2, body_top + body_h],
        fill=body_fill, outline=outline, width=4,
    )

    # しっぽ（右後ろの小さな丸）
    tail_r = radius * 0.22
    tail_cx = cx + body_w * 0.42
    tail_cy = body_top + body_h * 0.32
    draw.ellipse(
        [tail_cx - tail_r, tail_cy - tail_r, tail_cx + tail_r, tail_cy + tail_r],
        fill=body_fill, outline=outline, width=3,
    )

    paw_r = radius * 0.24
    if expression == "cheer":
        # 応援：前足を顔の横まで振り上げる
        for side in (-1, 1):
            px = cx + side * radius * 1.05
            py = cy + radius * 0.1
            draw.ellipse(
                [px - paw_r, py - paw_r * 1.7, px + paw_r, py + paw_r * 0.5],
                fill=body_fill, outline=outline, width=3,
            )
    else:
        # 通常：お腹の下に前足
        paw_y = body_top + body_h * 0.62
        for side in (-1, 1):
            px = cx + side * body_w * 0.24
            draw.ellipse(
                [px - paw_r, paw_y - paw_r, px + paw_r, paw_y + paw_r],
                fill=body_fill, outline=outline, width=3,
            )


def _draw_cheeks(draw, cx: float, cy: float, radius: float) -> None:
    """Quest95：頬の赤み（血色）を加えて可愛らしさ・キャラクター感を強める。"""
    blush = (255, 165, 165, 130)
    r = radius * 0.16
    dx = radius * 0.62
    dy = radius * 0.3
    draw.ellipse([cx - dx - r, cy + dy - r, cx - dx + r, cy + dy + r], fill=blush)
    draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=blush)


def _draw_character(
    draw, cx: float, cy: float, radius: float,
    expression: str = "normal", with_body: bool = True,
) -> None:
    """
    犬っぽいキャラクターを描画する。Quest94 v2：expression（表情パターン）に
    応じて目・口を_draw_face()へ委譲する。Quest95 v3：with_body=Trueの場合
    （スタンプ本体）は胴体・しっぽ・前足・頬の赤みも追加し、単なる丸アイコン感を
    減らす。main.png/tab.png（アイコン）はwith_body=Falseで顔だけのまま維持する。
    """
    body_fill = (255, 224, 178, 255)
    outline = (120, 90, 60, 255)

    if with_body:
        _draw_body(draw, cx, cy, radius, expression)

    # 耳（先に描いて、頭で上から重ねる）
    ear_r = radius * 0.42
    draw.ellipse(
        [cx - radius - ear_r * 0.3, cy - radius - ear_r * 0.5,
         cx - radius + ear_r * 1.3, cy - radius + ear_r * 0.9],
        fill=body_fill, outline=outline, width=3,
    )
    draw.ellipse(
        [cx + radius - ear_r * 1.3, cy - radius - ear_r * 0.5,
         cx + radius + ear_r * 0.3, cy - radius + ear_r * 0.9],
        fill=body_fill, outline=outline, width=3,
    )

    # 頭（本体）
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 fill=body_fill, outline=outline, width=4)

    if with_body:
        _draw_cheeks(draw, cx, cy, radius)

    _draw_face(draw, cx, cy, radius, expression)


def _draw_zzz(draw, x: float, y: float, size: float) -> None:
    """Quest95：sleepy表情に添える「Zzz」。"""
    font = _load_font(max(int(size * 1.7), 12))
    draw.text((x, y), "Zzz", font=font, fill=(120, 130, 200, 255),
              stroke_width=1, stroke_fill=(255, 255, 255, 255))


def _draw_burst(draw, cx: float, cy: float, radius: float) -> None:
    """Quest95：surprised表情に添えるびっくり線（頭の周囲の放射線）。"""
    import math
    for i in range(6):
        angle = math.pi / 3 * i + math.pi / 6
        x1 = cx + math.cos(angle) * radius * 1.12
        y1 = cy + math.sin(angle) * radius * 1.12
        x2 = cx + math.cos(angle) * radius * 1.32
        y2 = cy + math.sin(angle) * radius * 1.32
        draw.line([x1, y1, x2, y2], fill=(255, 190, 60, 255), width=3)


def _draw_face(draw, cx: float, cy: float, radius: float, expression: str) -> None:
    """
    Quest94 v2：表情パターン（_EXPRESSIONS）ごとに目・口の描き方を変える。
    未知のexpressionが渡された場合はnormalにフォールバックする。
    """
    dark = (60, 40, 30, 255)
    outline = (120, 90, 60, 255)
    eye_r = max(radius * 0.08, 4)
    eye_dx = radius * 0.42
    eye_dy = radius * 0.15
    lx, ly = cx - eye_dx, cy - eye_dy
    rx, ry = cx + eye_dx, cy - eye_dy
    mouth_cx, mouth_cy = cx, cy + radius * 0.1
    mouth_r = radius * 0.35
    lw = max(int(radius * 0.05), 2)

    if expression == "sleepy":
        for ex in (lx, rx):
            draw.line([ex - eye_r * 1.4, ly, ex + eye_r * 1.4, ly], fill=dark, width=lw)
        draw.arc([mouth_cx - mouth_r * 0.5, mouth_cy, mouth_cx + mouth_r * 0.5, mouth_cy + mouth_r * 0.5],
                  start=20, end=160, fill=outline, width=lw)
        _draw_zzz(draw, cx + radius * 0.85, cy - radius * 1.05, radius * 0.22)
    elif expression == "surprised":
        big_r = eye_r * 1.6
        draw.ellipse([lx - big_r, ly - big_r, lx + big_r, ly + big_r], fill=dark)
        draw.ellipse([rx - big_r, ly - big_r, rx + big_r, ly + big_r], fill=dark)
        o_r = mouth_r * 0.35
        draw.ellipse(
            [mouth_cx - o_r, mouth_cy - o_r + mouth_r * 0.2, mouth_cx + o_r, mouth_cy + o_r + mouth_r * 0.2],
            outline=outline, width=lw,
        )
        _draw_burst(draw, cx, cy, radius)
    elif expression == "smile":
        for ex in (lx, rx):
            draw.arc([ex - eye_r * 1.3, ly - eye_r, ex + eye_r * 1.3, ly + eye_r * 1.3],
                      start=200, end=340, fill=dark, width=lw)
        draw.arc([mouth_cx - mouth_r, mouth_cy, mouth_cx + mouth_r, mouth_cy + mouth_r],
                  start=10, end=170, fill=outline, width=lw + 1)
    elif expression == "worried":
        for ex, sign in ((lx, -1), (rx, 1)):
            draw.ellipse([ex - eye_r, ly - eye_r, ex + eye_r, ly + eye_r], fill=dark)
            draw.line([ex - eye_r * 1.5, ly - eye_r * 2.2, ex + sign * eye_r * 0.5, ly - eye_r * 3.2],
                       fill=outline, width=lw)
        draw.line([mouth_cx - mouth_r * 0.4, mouth_cy + mouth_r * 0.3,
                    mouth_cx + mouth_r * 0.4, mouth_cy + mouth_r * 0.1], fill=outline, width=lw)
    elif expression == "cheer":
        for ex in (lx, rx):
            draw.arc([ex - eye_r * 1.3, ly - eye_r, ex + eye_r * 1.3, ly + eye_r * 1.3],
                      start=200, end=340, fill=dark, width=lw)
        draw.pieslice([mouth_cx - mouth_r * 0.8, mouth_cy, mouth_cx + mouth_r * 0.8, mouth_cy + mouth_r],
                       start=10, end=170, fill=(180, 60, 60, 255))
    elif expression == "sorry":
        for ex, sign in ((lx, -1), (rx, 1)):
            draw.line([ex - eye_r, ly - eye_r, ex + eye_r, ly + eye_r], fill=dark, width=lw)
            draw.line([ex - eye_r, ly + eye_r, ex + eye_r, ly - eye_r], fill=dark, width=lw)
            # 困り眉（下がり眉）
            draw.line([ex - eye_r * 1.4, ly - eye_r * 2.6, ex + sign * eye_r * 1.2, ly - eye_r * 1.8],
                       fill=outline, width=lw)
        draw.line([mouth_cx - mouth_r * 0.4, mouth_cy + mouth_r * 0.2,
                    mouth_cx + mouth_r * 0.4, mouth_cy - mouth_r * 0.05], fill=outline, width=lw)
        _draw_teardrop(draw, rx + eye_r * 1.6, ly + eye_r * 1.4, radius * 0.11, (110, 175, 230, 255))
    elif expression == "joy":
        for ex in (lx, rx):
            draw.arc([ex - eye_r * 1.4, ly - eye_r * 1.4, ex + eye_r * 1.4, ly + eye_r * 0.6],
                      start=190, end=350, fill=dark, width=lw + 1)
        draw.arc([mouth_cx - mouth_r * 1.1, mouth_cy - mouth_r * 0.1, mouth_cx + mouth_r * 1.1, mouth_cy + mouth_r * 1.1],
                  start=10, end=170, fill=outline, width=lw + 1)
    else:  # normal（未知のexpressionもここへフォールバック）
        draw.ellipse([lx - eye_r, ly - eye_r, lx + eye_r, ly + eye_r], fill=dark)
        draw.ellipse([rx - eye_r, ly - eye_r, rx + eye_r, ly + eye_r], fill=dark)
        draw.arc([mouth_cx - mouth_r, mouth_cy, mouth_cx + mouth_r, mouth_cy + mouth_r],
                  start=20, end=160, fill=outline, width=lw)


# ──────────────────────────────────────────
# Quest94 v2：装飾（_DECORATIONS）
# ──────────────────────────────────────────

_DECORATION_COLORS = {
    "heart": (230, 70, 90, 255),
    "star": (250, 200, 60, 255),
    "note": (90, 90, 200, 255),
    "teardrop": (100, 170, 230, 255),
    "sparkle": (250, 170, 40, 255),
    "bg_circle": (255, 220, 180, 110),
    "pawprint": (150, 110, 80, 255),
    "moon": (250, 210, 120, 255),
}


def _draw_star(draw, cx: float, cy: float, r: float, fill) -> None:
    import math
    points = []
    for i in range(10):
        angle = math.pi / 5 * i - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.45
        points.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
    draw.polygon(points, fill=fill)


def _draw_heart(draw, cx: float, cy: float, r: float, fill) -> None:
    draw.ellipse([cx - r, cy - r * 0.6, cx, cy + r * 0.4], fill=fill)
    draw.ellipse([cx, cy - r * 0.6, cx + r, cy + r * 0.4], fill=fill)
    draw.polygon([(cx - r, cy), (cx + r, cy), (cx, cy + r * 1.3)], fill=fill)


def _draw_note(draw, cx: float, cy: float, r: float, fill) -> None:
    draw.ellipse([cx - r * 0.5, cy, cx + r * 0.5, cy + r], fill=fill)
    draw.line([cx + r * 0.45, cy + r * 0.5, cx + r * 0.45, cy - r * 1.2], fill=fill, width=max(int(r * 0.18), 2))
    draw.line([cx + r * 0.45, cy - r * 1.2, cx + r * 0.9, cy - r], fill=fill, width=max(int(r * 0.18), 2))


def _draw_teardrop(draw, cx: float, cy: float, r: float, fill) -> None:
    draw.ellipse([cx - r * 0.6, cy, cx + r * 0.6, cy + r * 1.2], fill=fill)
    draw.polygon([(cx - r * 0.6, cy + r * 0.4), (cx + r * 0.6, cy + r * 0.4), (cx, cy - r)], fill=fill)


def _draw_sparkle(draw, cx: float, cy: float, r: float, fill) -> None:
    draw.line([cx - r, cy, cx + r, cy], fill=fill, width=max(int(r * 0.25), 2))
    draw.line([cx, cy - r, cx, cy + r], fill=fill, width=max(int(r * 0.25), 2))
    draw.line([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], fill=fill, width=max(int(r * 0.15), 1))
    draw.line([cx - r * 0.7, cy + r * 0.7, cx + r * 0.7, cy - r * 0.7], fill=fill, width=max(int(r * 0.15), 1))


def _draw_pawprint(draw, cx: float, cy: float, r: float, fill) -> None:
    draw.ellipse([cx - r * 0.5, cy - r * 0.3, cx + r * 0.5, cy + r * 0.7], fill=fill)
    for dx, dy in ((-0.5, -0.7), (-0.15, -0.95), (0.2, -0.95), (0.55, -0.7)):
        pr = r * 0.22
        draw.ellipse([cx + dx * r - pr, cy + dy * r - pr, cx + dx * r + pr, cy + dy * r + pr], fill=fill)


def _draw_moon(draw, cx: float, cy: float, r: float, fill) -> None:
    """
    Quest95：三日月装飾。円を描いた後、ずらした円を透明色で直接上書きして
    欠けを作る（ImageDrawはRGBA画像でも直接ピクセルを上書きするため、
    fill=(0,0,0,0)で描画した部分はその場で透明に戻る）。
    """
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    off = r * 0.55
    draw.ellipse([cx - r + off, cy - r - off * 0.3, cx + r + off, cy + r - off * 0.3], fill=(0, 0, 0, 0))


def _draw_bg_circle(draw, w: int, h: int) -> None:
    """装飾"bg_circle"（背景丸）。キャラクターを描く前に呼ぶ。"""
    color = _DECORATION_COLORS["bg_circle"]
    r = min(w, h) * 0.46
    draw.ellipse([w / 2 - r, h * 0.42 - r, w / 2 + r, h * 0.42 + r], fill=color)


def _draw_decorations(draw, w: int, h: int, decoration: str) -> None:
    """
    Quest94 v2：スタンプ左上・右上に小さな装飾アイコンを描画する
    （bg_circleはキャラクター描画前に_draw_bg_circle()で別途処理済みのため、ここでは何もしない）。
    """
    if decoration == "bg_circle" or decoration not in _DECORATION_COLORS:
        return
    color = _DECORATION_COLORS[decoration]
    r = min(w, h) * 0.07
    positions = [(w * 0.14, h * 0.16), (w * 0.86, h * 0.16)]
    for px, py in positions:
        if decoration == "heart":
            _draw_heart(draw, px, py, r, color)
        elif decoration == "star":
            _draw_star(draw, px, py, r, color)
        elif decoration == "note":
            _draw_note(draw, px, py, r, color)
        elif decoration == "teardrop":
            _draw_teardrop(draw, px, py, r, color)
        elif decoration == "sparkle":
            _draw_sparkle(draw, px, py, r, color)
        elif decoration == "pawprint":
            _draw_pawprint(draw, px, py, r, color)
        elif decoration == "moon":
            _draw_moon(draw, px, py, r, color)


# ──────────────────────────────────────────
# Quest94 v2：文字レイアウト（_LAYOUTS）
# ──────────────────────────────────────────

def _wrap_phrase(phrase: str, max_chars: int = 6) -> list[str]:
    """
    長いフレーズを自動で2行に折り返す。日本語はスペース区切りが無いため、
    文字数がmax_charsを超える場合は中央付近で2分割する。
    """
    if len(phrase) <= max_chars:
        return [phrase]
    mid = (len(phrase) + 1) // 2
    return [phrase[:mid], phrase[mid:]]


def _measure_lines(draw, lines: list[str], font, stroke_width: int = 0) -> list[tuple]:
    sizes = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
        sizes.append((line, bbox[2] - bbox[0], bbox[3] - bbox[1], bbox))
    return sizes


def _fit_font(draw, lines: list[str], base_size: int, max_width: float, min_size: int = 16):
    """
    Quest95：フレーズごとに文字サイズを自動調整する。base_sizeから開始し、
    最も幅の広い行がmax_widthに収まるまでフォントサイズを縮める
    （min_sizeまで縮めても収まらない場合はmin_sizeで確定する）。
    """
    size = base_size
    while size > min_size:
        font = _load_font(size)
        stroke_w = _stroke_width_for(font)
        widest = max(
            draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)[2]
            - draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)[0]
            for line in lines
        )
        if widest <= max_width:
            return font
        size -= 2
    return _load_font(min_size)


def _stroke_width_for(font) -> int:
    """フォントサイズに応じた縁取りの太さ（Quest95：文字を太く読みやすくする）。"""
    size = getattr(font, "size", 26)
    return max(2, int(size * 0.14))


def _draw_lines(draw, sizes: list[tuple], font, cx: float, start_y: float) -> None:
    """
    中央揃えで複数行のフレーズを描画する。Quest95：手動オフセットの縁取りから
    Pillow標準のstroke_width/stroke_fillへ切り替え、より太く滲みの無い縁取りにする。
    """
    stroke_w = _stroke_width_for(font)
    y = start_y
    for line, tw, th, bbox in sizes:
        x = cx - tw / 2 - bbox[0]
        ty = y - bbox[1]
        draw.text((x, ty), line, font=font, fill=(45, 30, 20, 255),
                  stroke_width=stroke_w, stroke_fill=(255, 255, 255, 255))
        y += th + 8


def _draw_speech_bubble(draw, sizes: list[tuple], font, w: int, h: int) -> None:
    """layout="speech_bubble"：頭上に吹き出し風の枠を描き、その中にフレーズを入れる。"""
    max_tw = max(tw for _, tw, _, _ in sizes)
    total_th = sum(th for _, _, th, _ in sizes) + (len(sizes) - 1) * 6
    pad_x, pad_y = 14, 10
    bubble_w = max_tw + pad_x * 2
    bubble_h = total_th + pad_y * 2
    bx0 = w / 2 - bubble_w / 2
    by0 = h * 0.05
    bx1 = bx0 + bubble_w
    by1 = by0 + bubble_h

    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=12,
                            fill=(255, 255, 255, 235), outline=(120, 90, 60, 255), width=3)
    draw.polygon(
        [(w / 2 - 8, by1 - 2), (w / 2 + 8, by1 - 2), (w / 2, by1 + 14)],
        fill=(255, 255, 255, 235), outline=(120, 90, 60, 255),
    )
    _draw_lines(draw, sizes, font, w / 2, by0 + pad_y)


def _draw_diagonal_text(img, sizes: list[tuple], font, w: int, h: int) -> None:
    """layout="diagonal"：フレーズを別レイヤーに描いてから回転させ、スタンプへ貼り付ける。"""
    from PIL import Image as PILImage, ImageDraw as PILImageDraw

    stroke_w = _stroke_width_for(font)
    text = "\n".join(line for line, _, _, _ in sizes)
    probe = PILImageDraw.Draw(PILImage.new("RGBA", (10, 10)))
    bbox = probe.multiline_textbbox((0, 0), text, font=font, align="center", spacing=6, stroke_width=stroke_w)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad = 12
    layer = PILImage.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    layer_draw = PILImageDraw.Draw(layer)
    x = pad - bbox[0]
    y = pad - bbox[1]
    layer_draw.multiline_text(
        (x, y), text, font=font, fill=(45, 30, 20, 255), align="center", spacing=6,
        stroke_width=stroke_w, stroke_fill=(255, 255, 255, 255),
    )

    rotated = layer.rotate(-14, expand=True, resample=PILImage.BICUBIC)
    px = int(w / 2 - rotated.width / 2)
    py = int(h - rotated.height - 18)
    img.paste(rotated, (px, py), rotated)


def render_stamp(phrase: str, index: int) -> "Image.Image":
    """
    Quest98：Renderer共通インターフェース。1枚のスタンプ画像を描画して返す。
    Quest95 v3までの実装をそのまま移設したもので、フレーズの意味に合わせた
    （表情, 装飾, レイアウト）を_style_for_phrase()で選び、体・しっぽ・前足付きの
    キャラクターと自動サイズ調整済みの文字を組み合わせる。
    """
    from PIL import Image, ImageDraw

    expression, decoration, layout = _style_for_phrase(phrase, index)

    img = Image.new("RGBA", _STAMP_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = _STAMP_SIZE
    # Quest95：体を追加した分、頭の半径を小さめ・重心を上寄りにして
    # 下部にテキスト用の余白を確保する（キャラクターに文字が被らないように）。
    cx, cy, r = w / 2, h * 0.42, min(w, h) * 0.23

    if decoration == "bg_circle":
        _draw_bg_circle(draw, w, h)

    _draw_character(draw, cx, cy, r, expression=expression, with_body=True)
    _draw_decorations(draw, w, h, decoration)

    max_text_width = w * 0.84
    if layout == "large_text":
        base_size, max_chars = 36, 8
    elif layout == "two_line":
        base_size, max_chars = 22, 3
    else:
        base_size, max_chars = 30, 6

    lines = _wrap_phrase(phrase, max_chars=max_chars)
    font = _fit_font(draw, lines, base_size, max_text_width)
    stroke_w = _stroke_width_for(font)
    sizes = _measure_lines(draw, lines, font, stroke_width=stroke_w)

    if layout == "speech_bubble":
        _draw_speech_bubble(draw, sizes, font, w, h)
    elif layout == "diagonal":
        _draw_diagonal_text(img, sizes, font, w, h)
    elif layout == "top_center":
        _draw_lines(draw, sizes, font, w / 2, h * 0.03)
    else:  # bottom_center / large_text / two_line
        total_h = sum(th for _, _, th, _ in sizes) + (len(sizes) - 1) * 8
        _draw_lines(draw, sizes, font, w / 2, h - total_h - 16)

    return img


def render_icon(size: tuple[int, int]) -> "Image.Image":
    """
    Quest98：Renderer共通インターフェース。main.png / tab.png
    （チャット一覧アイコン）を描画して返す。体無し・顔だけのまま維持する。
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx, cy = w / 2, h / 2
    r = min(w, h) * 0.38
    _draw_character(draw, cx, cy, r, expression="normal", with_body=False)
    return img
