"""make_assets.py - 프로필 README 에 들어가는 그림을 만든다

    assets/banner.svg     동방 슈팅 게임 화면처럼 꾸민 머리 배너
    assets/card-*.svg     대표 프로젝트 스펠카드 3장
    assets/taskbar.svg    Hokora 처럼 캐릭터들이 작업표시줄 위를 걸어 다니는 꼬리 그림

GitHub 은 README 의 SVG 를 <img> 로 띄우기 때문에 SVG 안에서 바깥 글꼴을 불러올 수 없다.
그래서 글자는 Noto Sans KR / Noto Serif KR 글리프를 경로로 바꿔 넣는다.
보는 사람 컴퓨터에 어떤 글꼴이 깔려 있든 같은 모양으로 보인다.

캐릭터와 신사 그림은 Hokora (github.com/19GHYun/hokora-shrine) 의 스프라이트를 쓴다.

    python tools/make_assets.py --hokora ../hokora-shrine

프로젝트 수 같은 숫자는 포트폴리오(19ygh.netlify.app) 의 projects.ts 에 맞춰 STATS 를 고친다.
"""

import argparse
import base64
import io
import json
import math
import os
import random
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets'
FONT_DIR = Path(os.environ.get('FONT_DIR', 'C:/Windows/Fonts'))
FONT_FILES = {'sans': 'NotoSansKR-VF.ttf', 'serif': 'NotoSerifKR-VF.ttf'}

# 포트폴리오 projects.ts / skills.ts 기준 (2026.10)
STATS = {
    'projects': 17,
    'active': 6,
    'featured': 3,
    'skills': 45,
    'span': '2021–2026',
}

# solved.ac 프로필에서 옮겨 적는다 (2026.10.13 기준)
SOLVED = {
    'tier': 'Platinum',
    'level': 'IV',
    'rating': 1768,
    'floor': 1750,                 # 지금 티어가 시작하는 레이팅
    'next': ('Platinum III', 1900),
    'solved': 482,
    'class': 5,
    'rank': 5949,
}

TIER_COLOR = {
    'Bronze': '#ad5600', 'Silver': '#435f7a', 'Gold': '#ec9a00',
    'Platinum': '#27e2a4', 'Diamond': '#00b4fc', 'Ruby': '#ff0062',
}
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}

# 배너의 ♪ BGM 문구와 README 의 BGM 버튼에 쓰는 곡.
# 곡을 바꾸면 README 의 BGM 버튼 링크도 같이 바꾼다.
BGM = {
    'title': '少女綺想曲 ～ Dream Battle',
    'game': '동방영야초',
}

RED = '#e8364f'
WINE = '#2a0a18'
CREAM = '#fdf6e9'
INK = '#2a0a16'
PINK = '#ffd2de'
GOLD = '#f6c453'


def fmt(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


# ── 글자를 경로로 ──────────────────────────────────────────────

_FONTS = {}


def _font(face):
    if face not in _FONTS:
        _FONTS[face] = TTFont(FONT_DIR / FONT_FILES[face])
    return _FONTS[face]


class Type:
    """글리프를 <defs> 에 한 번씩만 넣고 <use> 로 찍는다"""

    def __init__(self):
        self.defs = {}
        self._sets = {}

    def _set(self, face, weight):
        key = (face, weight)
        if key not in self._sets:
            font = _font(face)
            self._sets[key] = (font.getGlyphSet(location={'wght': weight}), font.getBestCmap())
        return self._sets[key]

    def _glyph(self, ch, face, weight):
        gs, cmap = self._set(face, weight)
        name = cmap.get(ord(ch))
        if name is None:
            raise KeyError(f'{face} 글꼴에 {ch!r} 글리프가 없다')
        glyph = gs[name]
        gid = f'{face[0]}{weight}-{name}'.replace('.', '_')
        if gid not in self.defs:
            pen = SVGPathPen(gs, ntos=lambda v: str(round(v)))
            glyph.draw(pen)
            self.defs[gid] = pen.getCommands()
        return gid, glyph.width

    def width(self, s, size, face='sans', weight=400, ls=0):
        units = sum(self._glyph(ch, face, weight)[1] for ch in s)
        return units * size / 1000 + ls * max(len(s) - 1, 0)

    def fit(self, s, size, maxw, face='sans', weight=400, ls=0):
        """maxw 안에 들어갈 때까지 글자 크기를 줄인다"""
        while size > 6 and self.width(s, size, face, weight, ls) > maxw:
            size -= 0.25
        return size

    def text(self, s, x, y, size, face='sans', weight=400, fill='#fff', anchor='start',
             ls=0, stroke=None, sw=0, skew=0, attrs=''):
        w = self.width(s, size, face, weight, ls)
        if anchor == 'middle':
            x -= w / 2
        elif anchor == 'end':
            x -= w
        k = size / 1000
        uses, pen = [], 0.0
        for ch in s:
            gid, adv = self._glyph(ch, face, weight)
            if self.defs[gid]:
                uses.append(f'<use href="#{gid}" x="{round(pen)}"/>')
            pen += adv + ls / k
        paint = f' fill="{fill}"'
        if stroke:
            paint += (f' stroke="{stroke}" stroke-width="{round(sw / k)}"'
                      ' stroke-linejoin="round" paint-order="stroke"')
        tilt = f' skewX({-skew})' if skew else ''
        return (f'<g transform="translate({fmt(x)} {fmt(y)}){tilt} scale({k:.5f} {-k:.5f})"'
                f'{paint}{attrs}>{"".join(uses)}</g>')

    def defs_svg(self):
        return ''.join(f'<path id="{gid}" d="{d}"/>' for gid, d in self.defs.items() if d)


# ── Hokora 스프라이트 ──────────────────────────────────────────


class Sprites:
    def __init__(self, hokora):
        self.root = Path(hokora) / 'hokora' / 'sprites'
        self._manifests = {}

    def _anchor(self, ch, name):
        if ch not in self._manifests:
            path = self.root / ch / 'manifest.json'
            self._manifests[ch] = json.loads(path.read_text(encoding='utf-8'))
        return self._manifests[ch]['frames'][name]

    def image(self, ch, name, height, attrs=''):
        """발끝 가운데를 (0, 0) 에 맞춘 <image>. height 는 서 있는 키(200px) 를 몇 px 로 그릴지"""
        k = height / 200
        ax, ay = self._anchor(ch, name)
        im = Image.open(self.root / ch / f'{name}.png').convert('RGBA')
        x0, y0, x1, y1 = im.getchannel('A').getbbox()
        im = im.crop((x0, y0, x1, y1))
        ax, ay = ax - x0, ay - y0
        w, h = im.size
        # 고해상도 화면에서도 또렷하도록 표시 크기의 2배로 저장한다
        px = min(1.0, 2 * k)
        im = im.resize((max(1, round(w * px)), max(1, round(h * px))), Image.LANCZOS)
        im = im.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        buf = io.BytesIO()
        im.save(buf, 'PNG', optimize=True)
        uri = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
        return (f'<image href="{uri}" x="{fmt(-ax * k)}" y="{fmt(-ay * k)}" '
                f'width="{fmt(w * k)}" height="{fmt(h * k)}"{attrs}/>')

    def cycle(self, ch, names, height, period, keyframes):
        """프레임을 번갈아 보여 주는 걷기 애니메이션. 움직임을 끄면 첫 프레임만 남는다"""
        n = len(names)
        keyframes.add(n)
        out = []
        for i, name in enumerate(names):
            delay = -((n - i) % n) * period / n
            style = f' style="animation:fr{n} {fmt(period)}s step-end {fmt(delay)}s infinite"'
            hidden = '' if i == 0 else ' opacity="0"'
            out.append(self.image(ch, name, height, hidden + style))
        return ''.join(out)


def frame_keyframes(counts):
    return ''.join(
        f'@keyframes fr{n}{{0%{{opacity:1}}{fmt(100 / n)}%{{opacity:0}}100%{{opacity:0}}}}'
        for n in sorted(counts)
    )


# ── 공용 도형 ─────────────────────────────────────────────────


def yin_yang(r, light='#fff', dark=RED, ring=None):
    """음양옥. 원점이 가운데"""
    h = r / 2
    eye = r / 6
    edge = f' stroke="{ring}" stroke-width="{fmt(r / 7)}"' if ring else ''
    return (
        f'<circle r="{fmt(r)}" fill="{light}"{edge}/>'
        f'<path d="M0 {fmt(-r)}A{fmt(r)} {fmt(r)} 0 0 1 0 {fmt(r)}'
        f'A{fmt(h)} {fmt(h)} 0 0 1 0 0A{fmt(h)} {fmt(h)} 0 0 0 0 {fmt(-r)}Z" fill="{dark}"/>'
        f'<circle cy="{fmt(h)}" r="{fmt(eye)}" fill="{light}"/>'
        f'<circle cy="{fmt(-h)}" r="{fmt(eye)}" fill="{dark}"/>'
    )


def petal(fill='#ffc4d4'):
    return f'<path d="M0 -6C4 -6 6 -1 0 6C-6 -1 -4 -6 0 -6Z" fill="{fill}"/>'


def asanoha(pid, a, color, opacity):
    """삼베잎 무늬. 정삼각형 격자의 각 삼각형에 꼭짓점과 무게중심을 잇는 선을 긋는다"""
    h = a * 3 ** 0.5
    m = h / 2
    tris = [
        ((0, 0), (a, 0), (a / 2, m)),
        ((0, 0), (a / 2, m), (-a / 2, m)),
        ((a, 0), (3 * a / 2, m), (a / 2, m)),
        ((a / 2, m), (0, h), (a, h)),
        ((-a / 2, m), (a / 2, m), (0, h)),
        ((a / 2, m), (3 * a / 2, m), (a, h)),
    ]
    d = []
    for t in tris:
        cx = sum(p[0] for p in t) / 3
        cy = sum(p[1] for p in t) / 3
        for i, p in enumerate(t):
            q = t[(i + 1) % 3]
            d.append(f'M{fmt(p[0])} {fmt(p[1])}L{fmt(q[0])} {fmt(q[1])}')
            d.append(f'M{fmt(p[0])} {fmt(p[1])}L{fmt(cx)} {fmt(cy)}')
    return (f'<pattern id="{pid}" width="{fmt(a)}" height="{fmt(h)}" patternUnits="userSpaceOnUse">'
            f'<path d="{"".join(d)}" stroke="{color}" stroke-opacity="{opacity}" '
            f'stroke-width="0.8" fill="none"/></pattern>')


def torii(x, base, w, hgt, fill):
    top = base - hgt
    return (
        f'<g fill="{fill}">'
        f'<path d="M{fmt(x - w / 2 - 6)} {fmt(top)}Q{fmt(x)} {fmt(top + 4)} {fmt(x + w / 2 + 6)} {fmt(top)}'
        f'L{fmt(x + w / 2 + 4)} {fmt(top + 5)}Q{fmt(x)} {fmt(top + 8)} {fmt(x - w / 2 - 4)} {fmt(top + 5)}Z"/>'
        f'<rect x="{fmt(x - w / 2)}" y="{fmt(top + 11)}" width="{fmt(w)}" height="3.5"/>'
        f'<rect x="{fmt(x - w / 2 + 5)}" y="{fmt(top + 4)}" width="4" height="{fmt(hgt - 4)}"/>'
        f'<rect x="{fmt(x + w / 2 - 9)}" y="{fmt(top + 4)}" width="4" height="{fmt(hgt - 4)}"/>'
        '</g>'
    )


def svg_doc(w, h, title, defs, style, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{title}"><title>{title}</title>'
        f'<defs>{defs}</defs><style>{style}'
        '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'
        f'</style>{body}</svg>'
    )


# ── 배너 ─────────────────────────────────────────────────────


def banner(sp):
    W, H = 960, 420
    X0, Y0, X1, Y1 = 18, 18, 606, 402        # 플레이 화면
    BX, BY = 312, 128                        # 보스
    PX, PY = 312, 392                        # 레이무 발끝
    t = Type()
    rnd = random.Random(7)
    frames = set()
    body = []

    # 바깥 틀: 자주색 바탕에 삼베잎 무늬
    body.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#frame)"/>')
    body.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#asa)"/>')

    pf = []
    pf.append(f'<rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{Y1 - Y0}" fill="url(#sky)"/>')

    # 별
    for i in range(48):
        x = rnd.uniform(X0 + 6, X1 - 6)
        y = rnd.uniform(Y0 + 6, 300)
        r = rnd.choice([0.6, 0.8, 1.0, 1.3])
        tw = f' class="tw" style="animation-delay:{fmt(-rnd.uniform(0, 4))}s"' if i % 4 == 0 else ''
        pf.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{r}" fill="#fff" opacity="0.8"{tw}/>')

    # 달
    pf.append('<circle cx="110" cy="92" r="120" fill="url(#moonglow)"/>')
    pf.append('<circle cx="110" cy="92" r="40" fill="#fff4d8"/>')
    pf.append('<circle cx="96" cy="82" r="8" fill="#f2e2b6" opacity="0.6"/>'
              '<circle cx="122" cy="104" r="11" fill="#f2e2b6" opacity="0.5"/>'
              '<circle cx="124" cy="76" r="4" fill="#f2e2b6" opacity="0.6"/>')

    # 언덕과 도리이 실루엣
    pf.append(f'<path d="M{X0} {Y1}L{X0} 344C90 326 150 340 210 348C270 356 330 334 400 336'
              f'C470 338 520 322 {X1} 328L{X1} {Y1}Z" fill="#1b0f33"/>')
    pf.append(torii(520, 330, 46, 40, '#1b0f33'))
    pf.append(f'<path d="M{X0} {Y1}L{X0} 370C120 358 200 376 300 372C400 368 480 382 {X1} 364'
              f'L{X1} {Y1}Z" fill="#110822"/>')

    # 보스 뒤 마법진
    hexa = []
    for rot in (0, 60):
        pts = []
        for j in range(3):
            ang = math.radians(rot + j * 120 - 90)
            pts.append(f'{fmt(56 * math.cos(ang))} {fmt(56 * math.sin(ang))}')
        hexa.append('M' + 'L'.join(pts) + 'Z')
    pf.append(
        f'<g transform="translate({BX} {BY})" opacity="0.75">'
        '<g class="spin" style="animation-duration:24s">'
        '<circle r="66" fill="none" stroke="#ff9cc0" stroke-width="1.4"/>'
        '<circle r="58" fill="none" stroke="#ff9cc0" stroke-width="0.8" stroke-dasharray="2 4"/>'
        f'<path d="{"".join(hexa)}" fill="none" stroke="#ff9cc0" stroke-width="1"/>'
        '</g>'
        '<g class="spin rev" style="animation-duration:16s">'
        '<circle r="36" fill="none" stroke="#ffd36b" stroke-width="1" stroke-dasharray="7 4"/>'
        '</g></g>'
    )

    # 탄막: 보스에서 퍼져 나가는 원형 탄 6겹
    colors = ['#ff4b6e', '#4fa8ff', '#ff7ad9', '#36d6e7', '#ffb340', '#a07bff']
    WAVES, PER, DUR = 6, 16, 6.0
    bl = [f'<g transform="translate({BX} {BY})">']
    for w in range(WAVES):
        delay = -w * DUR / WAVES
        start = 36 + (520 - 36) * (w / WAVES)
        c = colors[w]
        if w % 2 == 0:
            shape = (f'<circle r="7" fill="{c}" opacity="0.35"/>'
                     f'<circle r="3.8" fill="#fff" stroke="{c}" stroke-width="1.8"/>')
        else:
            shape = (f'<ellipse rx="4.6" ry="9" fill="{c}" opacity="0.3"/>'
                     f'<ellipse rx="2.6" ry="6.4" fill="#fff" stroke="{c}" stroke-width="1.6"/>')
        for j in range(PER):
            ang = j * 360 / PER + w * 9
            bl.append(f'<g transform="rotate({fmt(ang)})"><g class="bl" transform="translate(0 {fmt(-start)})" '
                      f'style="animation-delay:{fmt(delay)}s">{shape}</g></g>')
    bl.append('</g>')
    pf.append(''.join(bl))

    # 보스 본체: 빛나는 신호
    pf.append(
        f'<g transform="translate({BX} {BY})"><g class="pulse">'
        '<circle r="30" fill="url(#core)"/>'
        '<path d="M-20 0C-15 -10 -10 -10 -5 0S5 10 10 0 15 -10 20 0" fill="none" '
        'stroke="#fff7cc" stroke-width="2.2" stroke-linecap="round"/>'
        '</g></g>'
    )

    # 레이무의 부적 탄
    for lane in (-7, 7):
        for k in range(4):
            pf.append(
                f'<g transform="translate({PX + lane} {PY - 64})"><g class="shot" '
                f'transform="translate(0 {-k * 50})" style="animation-delay:{fmt(-k * 0.2)}s">'
                '<rect x="-2.6" y="-7" width="5.2" height="14" rx="1" fill="#fff" stroke="#e8364f" stroke-width="0.8"/>'
                '<rect x="-0.8" y="-5" width="1.6" height="10" fill="#e8364f"/></g></g>'
            )

    # 레이무: 조준 원, 음양옥 두 개, 본인
    pf.append(f'<g transform="translate({PX} {PY - 30})"><g class="spin" style="animation-duration:6s">'
              '<circle r="27" fill="none" stroke="#fff" stroke-opacity="0.4" stroke-dasharray="3 5"/>'
              '</g></g>')
    for side in (-1, 1):
        pf.append(f'<g transform="translate({PX + side * 38} {PY - 36})"><g class="bob" '
                  f'style="animation-delay:{fmt(side * 0.4)}s"><g class="spin" style="animation-duration:2.4s">'
                  f'{yin_yang(8, ring="#fff")}</g></g></g>')
    pf.append(
        f'<g transform="translate({PX} {PY})"><g class="bob">'
        + sp.image('reimu', 'idle_0', 62)
        + sp.image('reimu', 'blink', 62, ' class="blink" opacity="0"')
        + '</g></g>'
    )

    # 위쪽 보스 이름, 체력 막대, 스펠카드 이름
    pf.append(t.text('미지의 신호', 30, 38, 12, weight=700, fill=PINK, stroke=WINE, sw=3))
    pf.append('<g transform="translate(30 44)"><rect width="566" height="4" rx="2" fill="#fff" opacity="0.15"/>'
              '<rect class="hp" width="566" height="4" rx="2" fill="url(#hp)"/></g>')
    spells = [
        ('測符', '「부반송파 · 차수 · 펄스 판별」', 'RF 신호 분석 도구 3종'),
        ('結符', '「무인기 탐지 실시간 공유」', '전술 상황인식 앱 플러그인'),
        ('星符', '「저비용 위성 기지국」', '위성 데이터 수신 · 처리'),
    ]
    period = 12
    for i, (kind, name, sub) in enumerate(spells):
        delay = [0, -8, -4][i]
        label = kind + name
        size = t.fit(label, 14, 330, weight=800)
        width = t.width(label, size, weight=800)
        hidden = '' if i == 0 else ' opacity="0"'
        pf.append(
            f'<g class="sc" style="animation-delay:{delay}s"{hidden}>'
            f'<rect x="{fmt(596 - width - 40)}" y="54" width="{fmt(width + 46)}" height="40" fill="url(#scbar)"/>'
            + t.text(label, 596, 72, size, weight=800, fill='#fff', anchor='end', stroke=WINE, sw=3.5)
            + t.text(f'SPELL {i + 1:02d} · {sub}', 596, 87, 9.5, weight=600, fill=GOLD, anchor='end',
                     stroke=WINE, sw=2.5)
            + '</g>'
        )

    pf.append(t.text(f'♪ BGM : {BGM["title"]}', 598, 396, 10, weight=500, fill=PINK,
                     anchor='end', stroke=WINE, sw=3))

    body.append(f'<g clip-path="url(#pfclip)">{"".join(pf)}</g>')
    body.append(f'<rect x="{X0 - 1.5}" y="{Y0 - 1.5}" width="{X1 - X0 + 3}" height="{Y1 - Y0 + 3}" rx="4" '
                f'fill="none" stroke="{GOLD}" stroke-opacity="0.55" stroke-width="1.5"/>')

    # 오른쪽 점수판
    LX, VX = 646, 926
    rows = [
        ('HiScore', f'{STATS["projects"]:010d}', '프로젝트'),
        ('Score', f'{STATS["active"]:010d}', '진행 중'),
        ('Rank', f'{SOLVED["tier"]} {SOLVED["level"]}', 'solved.ac'),
        ('Spell', '★' * STATS['featured'], '대표 프로젝트'),
        ('Graze', str(STATS['skills']), '다뤄 본 기술'),
        ('Point', STATS['span'], '활동 기간'),
    ]
    for i, (label, value, cap) in enumerate(rows):
        y = 52 + i * 42 + (8 if i >= 2 else 0)
        body.append(t.text(label, LX, y, 16, face='serif', weight=700, fill='#ffe9f0', stroke=WINE,
                           sw=3, skew=12))
        if label == 'Spell':
            body.append(t.text(value, VX, y, 18, weight=700, fill='#6dffa8', anchor='end', stroke=WINE,
                               sw=3, ls=3))
        elif label == 'Rank':
            body.append(t.text(value, VX, y, 18, weight=800, fill=TIER_COLOR[SOLVED['tier']], anchor='end',
                               stroke=WINE, sw=3))
        else:
            body.append(t.text(value, VX, y, 18, weight=700, fill='#fff', anchor='end', stroke=WINE,
                               sw=3, ls=1))
        body.append(t.text(cap, VX, y + 16, 10, weight=500, fill='#e0a9bc', anchor='end'))

    # 게임 로고
    body.append(f'<g transform="translate(784 346)" opacity="0.14"><g class="spin" style="animation-duration:30s">'
                f'{yin_yang(56, light="#fff", dark="#ffb3c6")}</g></g>')
    body.append(t.text('東方信號錄', 786, 358, 42, face='serif', weight=900, fill='#12030a', anchor='middle'))
    body.append(t.text('東方信號錄', 784, 355, 42, face='serif', weight=900, fill=RED, anchor='middle',
                       stroke='#fff6e8', sw=5))
    body.append(t.text('~ the Embodiment of Embedded Developer.', 784, 380, 11.5, face='serif',
                       weight=600, fill=PINK, anchor='middle', skew=10, stroke=WINE, sw=2.5))
    body.append(t.text('19ygh.netlify.app', 784, 400, 9.5, weight=500, fill='#c48ea0', anchor='middle',
                       ls=1))

    # 맨 위에 흩날리는 벚꽃잎
    for i in range(12):
        x = rnd.uniform(20, W - 20)
        dur = rnd.uniform(9, 15)
        delay = -rnd.uniform(0, dur)
        y0 = rnd.uniform(-20, H)
        body.append(f'<g transform="translate({fmt(x)} 0)"><g class="petal" transform="translate(0 {fmt(y0)})" '
                    f'style="animation-duration:{fmt(dur)}s;animation-delay:{fmt(delay)}s">{petal()}</g></g>')

    defs = (
        '<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#4a1129"/><stop offset="1" stop-color="#1f0614"/></linearGradient>'
        + asanoha('asa', 26, GOLD, 0.13) +
        '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#0b0920"/><stop offset="0.6" stop-color="#22134a"/>'
        '<stop offset="1" stop-color="#5a1e55"/></linearGradient>'
        '<radialGradient id="moonglow"><stop offset="0" stop-color="#fff1c8" stop-opacity="0.35"/>'
        '<stop offset="1" stop-color="#fff1c8" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="core"><stop offset="0" stop-color="#fff"/>'
        '<stop offset="0.45" stop-color="#7ee8ff" stop-opacity="0.85"/>'
        '<stop offset="1" stop-color="#7ee8ff" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="hp"><stop offset="0" stop-color="#ff5c7c"/>'
        '<stop offset="1" stop-color="#ffd36b"/></linearGradient>'
        '<linearGradient id="scbar"><stop offset="0" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="0.35" stop-color="#2a0a18" stop-opacity="0.7"/>'
        '<stop offset="1" stop-color="#2a0a18" stop-opacity="0.85"/></linearGradient>'
        f'<clipPath id="pfclip"><rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{Y1 - Y0}" rx="3"/></clipPath>'
        + t.defs_svg()
    )
    style = (
        '.spin{animation:spin linear infinite}.rev{animation-direction:reverse}'
        '@keyframes spin{to{transform:rotate(360deg)}}'
        f'.bl{{animation:bl {fmt(DUR)}s linear infinite}}'
        '@keyframes bl{from{transform:translate(0,-36px);opacity:0}6%{opacity:1}'
        'to{transform:translate(0,-520px);opacity:1}}'
        '.shot{animation:shot .8s linear infinite}'
        '@keyframes shot{from{transform:translate(0,0);opacity:.85}to{transform:translate(0,-200px);opacity:0}}'
        '.pulse{animation:pulse 1.6s ease-in-out infinite alternate}'
        '@keyframes pulse{to{transform:scale(1.12)}}'
        '.bob{animation:bob 1.8s ease-in-out infinite alternate}'
        '@keyframes bob{to{transform:translate(0,-4px)}}'
        '.blink{animation:blink 4.5s step-end infinite}'
        '@keyframes blink{0%{opacity:0}93%{opacity:1}97%{opacity:0}}'
        '.tw{animation:tw 3s ease-in-out infinite alternate}@keyframes tw{to{opacity:.15}}'
        f'.hp{{animation:hp {period}s linear infinite}}'
        '@keyframes hp{from{transform:scaleX(1)}to{transform:scaleX(.08)}}'
        f'.sc{{animation:sc {period}s linear infinite}}'
        '@keyframes sc{0%{opacity:0;transform:translate(14px,0)}3%{opacity:1;transform:translate(0,0)}'
        '30%{opacity:1;transform:translate(0,0)}33.3%{opacity:0}100%{opacity:0}}'
        '.petal{animation:petal linear infinite}'
        '@keyframes petal{from{transform:translate(0,-20px) rotate(0)}'
        'to{transform:translate(-70px,440px) rotate(600deg)}}'
        + frame_keyframes(frames)
    )
    return svg_doc(W, H, '슈팅 게임 화면처럼 꾸민 프로필 배너', defs, style, ''.join(body))


# ── 스펠카드 ─────────────────────────────────────────────────


CARDS = [
    {
        'file': 'card-rf.svg',
        'seal': '測',
        'no': 1,
        'spell': '測符「부반송파 · 차수 · 펄스 판별」',
        'title': 'RF 신호 분석 도구 3종',
        'desc': ['OFDM 부반송파 · QAM 차수 · 펄스 내', '변조를 자동으로 분류하고 계측'],
        'chips': ['Python', 'PySide6', 'NumPy', 'C#'],
        'foot': '회사 · 2026.06 – 진행 중',
        'who': ('nitori', 'idle_0'),
    },
    {
        'file': 'card-sa.svg',
        'seal': '結',
        'no': 2,
        'spell': '結符「무인기 탐지 실시간 공유」',
        'title': '전술 상황인식 앱 플러그인',
        'desc': ['현장 센서가 찾은 무인기를 지도에', '띄우고 단말끼리 실시간으로 공유'],
        'chips': ['Java', 'Android', 'ESP32', 'BLE · UDP'],
        'foot': '회사 · 2025.12 – 2026.02',
        'who': ('aya', 'skill_0'),
    },
    {
        'file': 'card-sat.svg',
        'seal': '星',
        'no': 3,
        'spell': '星符「저비용 위성 기지국」',
        'title': '저비용 위성 기지국',
        'desc': ['라즈베리파이와 RTL-SDR로 위성 사진을', '받아 AI로 후처리하고 학회에서 발표'],
        'chips': ['Python', 'RTL-SDR', 'TensorFlow'],
        'foot': '학부 · 연구실 · 2024.01 – 2024.06',
        'who': ('marisa', 'idle_0'),
    },
]


def card(sp, c):
    W, H = 300, 200
    t = Type()
    rnd = random.Random(c['no'])
    b = []
    b.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{CREAM}" stroke="#ecd6c4"/>')
    b.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#asa)"/>')
    b.append(f'<rect x="7" y="7" width="{W - 14}" height="{H - 14}" rx="10" fill="none" stroke="{RED}" stroke-width="1.6"/>')
    b.append(f'<rect x="11" y="11" width="{W - 22}" height="{H - 22}" rx="8" fill="none" stroke="{RED}" '
             'stroke-width="0.6" stroke-opacity="0.6"/>')

    # 도장
    b.append(f'<rect x="20" y="20" width="40" height="40" rx="6" fill="{RED}"/>')
    b.append(t.text(c['seal'], 40, 50, 28, face='serif', weight=900, fill=CREAM, anchor='middle'))
    b.append(t.text(f'SPELL CARD  No.{c["no"]}', 70, 31, 9, weight=700, fill=RED, ls=1.5))
    size = t.fit(c['spell'], 13, 212, weight=800)
    b.append(t.text(c['spell'], 70, 52, size, weight=800, fill=INK))
    b.append(f'<line x1="20" y1="71" x2="280" y2="71" stroke="{RED}" stroke-opacity="0.45" stroke-dasharray="3 3"/>')

    b.append(t.text(c['title'], 20, 97, t.fit(c['title'], 16, 260, weight=800), weight=800, fill=INK))
    for i, line in enumerate(c['desc']):
        b.append(t.text(line, 20, 117 + i * 16, t.fit(line, 11, 214, weight=500), weight=500, fill='#5b3a46'))

    # 기술 칩
    x, y = 20, 148
    for chip in c['chips']:
        w = t.width(chip, 9.5, weight=600) + 14
        if x + w > 230:
            raise ValueError(f'{c["file"]}: 기술 칩이 한 줄을 넘는다 ({chip})')
        b.append(f'<rect x="{fmt(x)}" y="{y}" width="{fmt(w)}" height="17" rx="8.5" fill="#f7dbe1"/>')
        b.append(t.text(chip, x + 7, y + 12, 9.5, weight=600, fill='#a3233a'))
        x += w + 5

    b.append(t.text(c['foot'], 20, 186, 9.5, weight=500, fill='#9a6b78'))

    # 반짝이와 캐릭터
    for _ in range(3):
        sx, sy = rnd.uniform(222, 285), rnd.uniform(90, 130)
        b.append(f'<g transform="translate({fmt(sx)} {fmt(sy)})"><path class="tw" style="animation-delay:'
                 f'{fmt(-rnd.uniform(0, 2))}s" d="M0 -5L1.2 -1.2 5 0 1.2 1.2 0 5-1.2 1.2-5 0-1.2-1.2Z" fill="{GOLD}"/></g>')
    ch, frame = c['who']
    b.append(f'<g transform="translate(258 189)"><g class="bob">{sp.image(ch, frame, 80)}</g></g>')

    defs = asanoha('asa', 22, RED, 0.05) + t.defs_svg()
    style = (
        '.bob{animation:bob 2s ease-in-out infinite alternate}@keyframes bob{to{transform:translate(0,-3px)}}'
        '.tw{animation:tw 1.6s ease-in-out infinite alternate}@keyframes tw{to{opacity:.1}}'
    )
    title = f'{c["title"]} — {c["desc"][0]} {c["desc"][1]}'
    return svg_doc(W, H, title, defs, style, ''.join(b))


# ── 작업표시줄 ───────────────────────────────────────────────


def taskbar(sp):
    W, H = 960, 170
    G = 124                         # 작업표시줄 윗면 (캐릭터가 서는 곳)
    t = Type()
    frames = set()
    b = []

    # 신사와 장식
    b.append(f'<g transform="translate(640 {G})">{sp.image("props", "lantern", 50)}</g>')
    b.append(f'<g transform="translate(692 {G})">{sp.image("props", "mini_torii", 74)}</g>')
    b.append(f'<g transform="translate(842 {G})">{sp.image("shrines", "sakura", 104)}</g>')

    # 신사 옆에서 자는 치르노
    b.append(f'<g transform="translate(590 {G})">'
             + sp.cycle('cirno', ['sleep_0', 'sleep_1'], 54, 2.4, frames)
             + '</g>')
    for i in range(3):
        b.append(f'<g transform="translate(598 {G - 44})"><g class="zz" style="animation-delay:{fmt(-i)}s">'
                 + t.text('z', 0, 0, 9 + i * 2, weight=800, fill='#7fc8ff', stroke='#fff', sw=2)
                 + '</g></g>')

    # 걸어 다니는 아이들
    walkers = [
        ('reimu', [f'walk_{i}' for i in range(0, 16, 2)], 1.1, 90, 470, 24, 0),
        ('marisa', [f'walk_{i}' for i in range(0, 12, 2)], 0.9, 200, 540, 19, -7),
        ('sakuya', [f'walk_{i}' for i in range(0, 12, 2)], 0.9, 40, 330, 15, -11),
    ]
    keyframes = []
    for n, (ch, names, period, x_from, x_to, dur, delay) in enumerate(walkers):
        dist = x_to - x_from
        keyframes.append(f'@keyframes go{n}{{0%{{transform:translate(0,0)}}50%{{transform:translate({dist}px,0)}}'
                         f'100%{{transform:translate(0,0)}}}}')
        bubble = ''
        if ch == 'reimu':
            msg = '새전 넣고 가~ ♪'
            bw = t.width(msg, 10, weight=700) + 18
            bubble = (f'<g class="say" opacity="0"><g transform="translate(0 -84)">'
                      f'<rect x="{fmt(-bw / 2)}" y="-14" width="{fmt(bw)}" height="20" rx="10" fill="#fff" stroke="{RED}" stroke-width="1"/>'
                      '<path d="M-4 5.5L0 11 4 5.5Z" fill="#fff"/>'
                      + t.text(msg, 0, 0, 10, weight=700, fill=RED, anchor='middle')
                      + '</g></g>')
        b.append(
            f'<g transform="translate({x_from} {G})"><g style="animation:go{n} {dur}s linear {delay}s infinite">'
            f'<g style="animation:flip {dur}s step-end {delay}s infinite">'
            + sp.cycle(ch, names, 66, period, frames)
            + f'</g>{bubble}</g></g>'
        )

    # 작업표시줄
    b.append(f'<rect x="0" y="{G}" width="{W}" height="{H - G}" rx="12" fill="#1f1d2e"/>')
    b.append(f'<rect x="12" y="{G}" width="{W - 24}" height="1" fill="#fff" opacity="0.12"/>')
    mid = G + (H - G) / 2
    b.append(f'<g transform="translate(30 {fmt(mid)})">{yin_yang(12, ring="#fff")}</g>')
    b.append(f'<rect x="54" y="{fmt(mid - 12)}" width="226" height="24" rx="12" fill="#2d2a40"/>')
    b.append(f'<circle cx="69" cy="{fmt(mid - 1)}" r="4.5" fill="none" stroke="#bcb6d8" stroke-width="1.6"/>'
             f'<line x1="72.5" y1="{fmt(mid + 2.5)}" x2="76" y2="{fmt(mid + 6)}" stroke="#bcb6d8" stroke-width="1.6" stroke-linecap="round"/>')
    b.append(t.text('검색하려면 여기에 입력하십시오', 84, mid + 4, 11, weight=500, fill='#bcb6d8'))

    # 작업표시줄 아이콘: 신사, 달력, 말풍선, 마작패
    ix = [300, 334, 368, 402]
    y0 = mid - 12
    icons = [
        f'<rect width="24" height="24" rx="6" fill="{RED}"/>' + torii(12, 19, 12, 12, '#fff'),
        '<rect width="24" height="24" rx="6" fill="#fff"/><rect width="24" height="8" rx="4" fill="#e8364f"/>'
        '<rect y="4" width="24" height="4" fill="#e8364f"/>'
        + t.text('28', 12, 20, 10, weight=800, fill=INK, anchor='middle'),
        '<rect width="24" height="24" rx="6" fill="#ff9cc0"/>'
        '<path d="M5 7Q5 5 7 5H17Q19 5 19 7V14Q19 16 17 16H11L7 19.5V16Q5 16 5 14Z" fill="#fff"/>'
        + t.text('?', 12, 14.5, 9, weight=900, fill='#e8364f', anchor='middle'),
        '<rect x="3" width="18" height="24" rx="3.5" fill="#f4ecd8" stroke="#c9b48a"/>'
        + t.text('中', 12, 17.5, 13, face='serif', weight=900, fill=RED, anchor='middle'),
    ]
    for x, icon in zip(ix, icons):
        b.append(f'<g transform="translate({x - 12} {fmt(y0)})">{icon}</g>')
    b.append(f'<rect x="{ix[0] - 6}" y="{H - 5}" width="12" height="2.5" rx="1.2" fill="#ff9cc0"/>')

    # 오른쪽 알림 영역
    b.append(f'<g transform="translate(812 {fmt(mid)})"><circle r="7" fill="{GOLD}"/>'
             '<rect x="-2" y="-2" width="4" height="4" fill="#1f1d2e"/></g>')
    b.append(t.text(f'새전 {STATS["projects"]}', 826, mid + 4, 11, weight=600, fill='#e7e3f5'))
    b.append(t.text('12:34', 934, mid + 4, 11, weight=600, fill='#e7e3f5', anchor='end'))

    defs = t.defs_svg()
    style = (
        '@keyframes flip{0%{transform:scale(1,1)}50%{transform:scale(-1,1)}100%{transform:scale(-1,1)}}'
        + ''.join(keyframes)
        + '.say{animation:say 9s linear infinite}'
        '@keyframes say{0%{opacity:0}4%{opacity:1}30%{opacity:1}34%{opacity:0}100%{opacity:0}}'
        '.zz{animation:zz 3s linear infinite}'
        '@keyframes zz{from{transform:translate(0,0);opacity:0}20%{opacity:1}'
        'to{transform:translate(14px,-26px);opacity:0}}'
        + frame_keyframes(frames)
    )
    return svg_doc(W, H, '작업표시줄 위를 걸어 다니는 레이무 · 마리사 · 사쿠야와 신사', defs, style, ''.join(b))


# ── solved.ac 티어 카드 ───────────────────────────────────────


def tier_shield(num_svg):
    """solved.ac 티어 아이콘을 닮은 방패. 원점이 가운데"""
    return (
        '<path d="M-34 -40H34V20L0 42-34 20Z" fill="url(#shield)" stroke="#fff" stroke-opacity="0.85" '
        'stroke-width="2.5" stroke-linejoin="round"/>'
        '<path d="M-34 -40H34V-26H-34Z" fill="#fff" opacity="0.18"/>'
        '<path d="M-24 22L0 36 24 22" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" '
        'stroke-linejoin="round"/>'
        + num_svg
    )


def solved_card(sp):
    W, H = 720, 200
    t = Type()
    rnd = random.Random(11)
    frames = set()
    color = TIER_COLOR[SOLVED['tier']]
    b = []
    b.append(f'<rect width="{W}" height="{H}" rx="16" fill="url(#frame)"/>')
    b.append(f'<rect width="{W}" height="{H}" rx="16" fill="url(#asa)"/>')
    b.append(f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="11" fill="none" stroke="{GOLD}" '
             'stroke-opacity="0.55" stroke-width="1.5"/>')

    # 티어 방패와 뒤의 마법진
    cx, cy = 104, 100
    b.append(f'<circle cx="{cx}" cy="{cy}" r="74" fill="url(#halo)"/>')
    b.append(
        f'<g transform="translate({cx} {cy})" opacity="0.6">'
        '<g class="spin" style="animation-duration:20s">'
        f'<circle r="66" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="2 5"/>'
        f'<circle r="58" fill="none" stroke="{color}" stroke-width="0.8"/></g>'
        '<g class="spin rev" style="animation-duration:14s">'
        f'<circle r="50" fill="none" stroke="{GOLD}" stroke-width="1" stroke-dasharray="8 5"/></g></g>'
    )
    num = t.text(str(ROMAN[SOLVED['level']]), 0, 14, 46, weight=900, fill='#fff', anchor='middle',
                 stroke='#0b5e46', sw=4)
    b.append(f'<g transform="translate({cx} {cy - 2})"><g class="bob">{tier_shield(num)}</g></g>')
    for _ in range(4):
        sx, sy = cx + rnd.uniform(-70, 70), cy + rnd.uniform(-70, 60)
        b.append(f'<g transform="translate({fmt(sx)} {fmt(sy)})"><path class="tw" style="animation-delay:'
                 f'{fmt(-rnd.uniform(0, 2))}s" d="M0 -6L1.4 -1.4 6 0 1.4 1.4 0 6-1.4 1.4-6 0-1.4-1.4Z" '
                 'fill="#fff"/></g>')

    # 티어 이름과 레이팅
    x = 200
    b.append(t.text('solved.ac  ·  BAEKJOON', x, 46, 10, weight=700, fill=PINK, ls=2))
    b.append(t.text(f'{SOLVED["tier"].upper()} {SOLVED["level"]}', x, 84, 30, weight=900, fill=color,
                    stroke=WINE, sw=4, ls=1))
    rating = f'{SOLVED["rating"]:,}'
    b.append(t.text(rating, x, 120, 24, weight=800, fill='#fff', stroke=WINE, sw=3))
    b.append(t.text('RATING', x + t.width(rating, 24, weight=800) + 8, 120, 10, weight=700,
                    fill='#e0a9bc', ls=1.5))

    # 다음 티어까지 막대
    nxt_name, nxt = SOLVED['next']
    frac = (SOLVED['rating'] - SOLVED['floor']) / (nxt - SOLVED['floor'])
    bw = 250
    b.append(f'<g transform="translate({x} 134)"><rect width="{bw}" height="8" rx="4" fill="#fff" opacity="0.14"/>'
             f'<rect class="grow" width="{fmt(max(8, bw * frac))}" height="8" rx="4" fill="url(#bar)"/></g>')
    b.append(t.text(f'{nxt_name}까지 {nxt - SOLVED["rating"]}점', x, 160, 10.5, weight=600, fill=PINK))
    b.append(t.text(f'{round(frac * 100)}%', x + bw, 160, 10.5, weight=700, fill=GOLD, anchor='end'))

    # 오른쪽 점수판
    LX, VX = 480, 596
    rows = [
        ('Solved', f'{SOLVED["solved"]:,}', '해결한 문제'),
        ('Class', str(SOLVED['class']), '클래스'),
        ('Rank', f'#{SOLVED["rank"]:,}', '전체 랭킹'),
    ]
    for i, (label, value, cap) in enumerate(rows):
        y = 58 + i * 46
        b.append(t.text(label, LX, y, 15, face='serif', weight=700, fill='#ffe9f0', stroke=WINE, sw=3,
                        skew=12))
        b.append(t.text(value, VX, y, 18, weight=800, fill='#fff', anchor='end', stroke=WINE, sw=3))
        b.append(t.text(cap, VX, y + 15, 9.5, weight=500, fill='#e0a9bc', anchor='end'))

    # 책 읽는 파츄리
    b.append('<g transform="translate(660 182)"><g class="bob">'
             + sp.cycle('patchouli', ['skill_0', 'skill_1'], 112, 2.4, frames)
             + '</g></g>')

    defs = (
        '<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#4a1129"/><stop offset="1" stop-color="#1f0614"/></linearGradient>'
        + asanoha('asa', 26, GOLD, 0.13) +
        '<linearGradient id="shield" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b9ffe8"/>'
        f'<stop offset="0.45" stop-color="{color}"/><stop offset="1" stop-color="#0f9c74"/></linearGradient>'
        f'<radialGradient id="halo"><stop offset="0" stop-color="{color}" stop-opacity="0.35"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="bar"><stop offset="0" stop-color="{color}"/><stop offset="1" stop-color="{GOLD}"/>'
        '</linearGradient>'
        + t.defs_svg()
    )
    style = (
        '.spin{animation:spin linear infinite}.rev{animation-direction:reverse}'
        '@keyframes spin{to{transform:rotate(360deg)}}'
        '.bob{animation:bob 2s ease-in-out infinite alternate}@keyframes bob{to{transform:translate(0,-3px)}}'
        '.tw{animation:tw 1.6s ease-in-out infinite alternate}@keyframes tw{to{opacity:.1}}'
        '.grow{animation:grow 1.6s ease-out both}@keyframes grow{from{transform:scaleX(0)}}'
        + frame_keyframes(frames)
    )
    title = (f'solved.ac {SOLVED["tier"]} {SOLVED["level"]}, 레이팅 {SOLVED["rating"]}, '
             f'해결한 문제 {SOLVED["solved"]}개, CLASS {SOLVED["class"]}, 전체 랭킹 {SOLVED["rank"]}위')
    return svg_doc(W, H, title, defs, style, ''.join(b))


# ── 참배객 현판 ─────────────────────────────────────────────


def visitors_plaque(sp):
    """방문자 수 카운터 위에 거는 현판. 숫자는 README 에서 Moe-Counter 가 붙인다"""
    W, H = 520, 132
    G = 124                         # 바닥 (레이무와 새전함이 서는 곳)
    t = Type()
    frames = set()
    b = []

    # 시메나와와 시데
    b.append('<path d="M120 22Q260 52 400 22" fill="none" stroke="#8a6a3c" stroke-width="9" stroke-linecap="round"/>'
             '<path d="M120 22Q260 52 400 22" fill="none" stroke="#e9d3a3" stroke-width="9" stroke-linecap="round" '
             'stroke-dasharray="4 5" stroke-opacity="0.9"/>')
    for x in (140, 380):
        y = 22 + 30 * (1 - ((x - 260) / 140) ** 2)
        b.append(f'<g transform="translate({x} {fmt(y + 2)})"><g class="sway">'
                 '<path d="M-5 0H5L1 8H7L1 17H7L0 28-2 19H-7L-1 11H-7Z" fill="#fff" stroke="#d9d0c0" '
                 'stroke-width="0.6"/></g></g>')

    # 나무 현판
    b.append('<rect x="160" y="44" width="200" height="70" rx="7" fill="url(#wood)" stroke="#f6c453" '
             'stroke-width="2"/>')
    b.append('<rect x="167" y="51" width="186" height="56" rx="4" fill="none" stroke="#f6c453" '
             'stroke-opacity="0.45"/>')
    b.append(t.text('참배객', 260, 88, 30, face='serif', weight=900, fill='#ffe9b8', anchor='middle',
                    stroke='#2a0e05', sw=3, ls=4))
    b.append(t.text('參拜客 · VISITORS', 260, 102, 8.5, weight=700, fill='#f6c453', anchor='middle', ls=1.5))

    # 손 흔드는 레이무와 말풍선
    b.append(f'<g transform="translate(74 {G})">'
             + sp.cycle('reimu', ['wave_0', 'wave_1'], 92, 0.9, frames)
             + '</g>')
    msg = '어서 오세요~'
    bw = t.width(msg, 10, weight=700) + 18
    b.append(f'<g transform="translate(74 16)"><rect x="{fmt(-bw / 2)}" y="-11" width="{fmt(bw)}" height="20" '
             f'rx="10" fill="#fff" stroke="{RED}"/><path d="M-4 8.5L0 14 4 8.5Z" fill="#fff"/>'
             + t.text(msg, 0, 3, 10, weight=700, fill=RED, anchor='middle') + '</g>')

    # 새전함과 떨어지는 동전
    b.append(f'<g transform="translate(446 {G})">{sp.image("props", "saisen_box", 70)}</g>')
    for i in range(2):
        b.append(f'<g transform="translate({438 + i * 16} 0)"><g class="coin" style="animation-delay:{-i * 1.3}s">'
                 f'<circle r="6" fill="{GOLD}" stroke="#b8862b"/><rect x="-1.8" y="-1.8" width="3.6" height="3.6" '
                 'fill="#b8862b"/></g></g>')

    defs = ('<linearGradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a4424"/>'
            '<stop offset="1" stop-color="#4a2412"/></linearGradient>' + t.defs_svg())
    style = (
        '.sway{animation:sway 2.4s ease-in-out infinite alternate;transform-origin:0 0}'
        '@keyframes sway{from{transform:rotate(-6deg)}to{transform:rotate(6deg)}}'
        '.coin{animation:coin 2.6s ease-in infinite}'
        '@keyframes coin{0%{transform:translate(0,40px);opacity:0}10%{opacity:1}'
        '45%{transform:translate(0,92px);opacity:1}50%,100%{transform:translate(0,92px);opacity:0}}'
        + frame_keyframes(frames)
    )
    return svg_doc(W, H, '참배객 현판. 레이무가 손을 흔들고 새전함에 동전이 떨어진다', defs, style, ''.join(b))


# ── BGM 버튼 ─────────────────────────────────────────────────


def bgm_button():
    """README 의 shields 배지와 높이를 맞춘 BGM 버튼. 링크는 README 에서 건다"""
    H = 28
    t = Type()
    left = 92
    title = BGM['title']
    tw = t.width(title, 11, weight=700)
    W = round(left + 14 + tw + 14)
    b = []
    b.append(f'<clipPath id="r"><rect width="{W}" height="{H}" rx="4"/></clipPath>')
    b.append(f'<g clip-path="url(#r)"><rect width="{left}" height="{H}" fill="{WINE}"/>'
             f'<rect x="{left}" width="{W - left}" height="{H}" fill="{RED}"/></g>')
    # 재생 버튼, 글자, 들썩이는 막대
    b.append('<path d="M10 8.5L19 14 10 19.5Z" fill="#fff"/>')
    b.append(t.text('BGM', 25, 18.5, 11, weight=800, fill='#fff', ls=1.5))
    for i, (x, d) in enumerate([(62, 0), (67, -0.35), (72, -0.7), (77, -0.2)]):
        b.append(f'<g transform="translate({x} 20)"><rect class="eq" x="-1.5" y="-10" width="3" height="10" rx="1" '
                 f'fill="{GOLD}" style="animation-delay:{d}s"/></g>')
    b.append(t.text(title, left + 14, 18.5, 11, weight=700, fill='#fff'))
    style = ('.eq{animation:eq .9s ease-in-out infinite alternate;transform-origin:0 0}'
             '@keyframes eq{from{transform:scaleY(.25)}to{transform:scaleY(1)}}')
    body = ''.join(b[1:])
    return svg_doc(W, H, f'BGM 틀기: {title} ({BGM["game"]})', b[0] + t.defs_svg(), style, body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hokora', default=str(ROOT.parent / 'hokora-shrine'),
                    help='Hokora 저장소 경로 (스프라이트를 읽는다)')
    args = ap.parse_args()
    sp = Sprites(args.hokora)
    OUT.mkdir(exist_ok=True)
    outputs = {'banner.svg': banner(sp), 'taskbar.svg': taskbar(sp), 'solved.svg': solved_card(sp),
               'visitors.svg': visitors_plaque(sp), 'bgm.svg': bgm_button()}
    for c in CARDS:
        outputs[c['file']] = card(sp, c)
    for name, svg in outputs.items():
        (OUT / name).write_text(svg, encoding='utf-8')
        print(f'{name:14s} {len(svg.encode()) / 1024:7.1f} KB')


if __name__ == '__main__':
    main()
