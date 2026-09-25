# -*- coding: utf-8 -*-
"""빌드 시점 SVG 차트 (자바스크립트 없이 모든 뷰어에서 표시)

규칙
  - 값 축 없이 막대 끝에 수치 (천 단위 콤마 · 차트 안 소수 자리 통일)
  - x축 라벨은 기울이지 않고 두 줄로 나눠 전부 표시
  - PC용 세로 막대(.ch-d)와 모바일용 가로 막대(.ch-m)를 함께 만들어 화면 폭에 따라 하나만 보임
  - 수치 라벨 폭을 추정해 막대 폭을 넘으면 글자를 줄임 (라벨 겹침 방지)
"""
import html
from common import fmt


def esc(s):
    return html.escape(str(s), quote=True)


def tw(s, size):
    """글자 폭 추정(px) : 숫자 0.58em · 콤마/점 0.3em · 한글 1em · 기타 0.6em"""
    w = 0
    for ch in str(s):
        if ch.isdigit():
            w += .58
        elif ch in ',.':
            w += .3
        elif '가' <= ch <= '힣':
            w += 1.0
        else:
            w += .6
    return w * size


def fit(texts, room, size=12, low=8.5):
    """모든 라벨이 room(px) 안에 들어가는 가장 큰 글자 크기"""
    s = size
    while s > low and max([tw(t, s) for t in texts] or [0]) > room:
        s -= .5
    return s


def vbars(labels, series, nd=0, w=580, h=230, unit=''):
    """세로 묶음 막대. labels=[(1줄, 2줄)], series=[{'name','color','values'}]"""
    n, k = len(labels), len(series)
    if not n:
        return ''
    top, bot, pad = 26, 40, 6
    slot = (w - 2 * pad) / n
    bw = min(46, slot * (0.78 if k == 1 else 0.86) / k)
    vmax = max([v or 0 for s in series for v in s['values']] + [0]) or 1
    texts = [fmt(v, nd) for s in series for v in s['values']]
    vs = fit(texts, (bw - 2) if k > 1 else slot - 4, 12)    # 이웃 막대 라벨과 겹치지 않는 폭
    xs = fit([a for a, b in labels] + [b for a, b in labels], slot - 2, 11.5)
    ph = h - top - bot
    o = ['<svg viewBox="0 0 %d %d" role="img">' % (w, h)]
    for i, (l1, l2) in enumerate(labels):
        gx = pad + slot * i + (slot - bw * k) / 2
        for j, s in enumerate(series):
            v = s['values'][i] or 0
            bh = max(0.0, ph * v / vmax)
            x = gx + bw * j
            y = top + ph - bh
            op = '' if s.get('hi', {}).get(i, True) else ' fill-opacity=".45"'
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"%s/>' % (x, y, bw - 1, bh, s['color'], op))
            o.append('<text class="v" x="%.1f" y="%.1f" style="font-size:%.1fpx">%s</text>'
                     % (x + (bw - 1) / 2, y - 5, vs, fmt(v, nd)))
        cx = pad + slot * i + slot / 2
        o.append('<text class="x" x="%.1f" y="%d" style="font-size:%.1fpx">%s</text>' % (cx, top + ph + 16, xs, esc(l1)))
        if l2:
            o.append('<text class="x2" x="%.1f" y="%d" style="font-size:%.1fpx">%s</text>' % (cx, top + ph + 31, xs, esc(l2)))
    o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="base"/>' % (pad, w - pad, top + ph + .5, top + ph + .5))
    o.append('</svg>')
    return ''.join(o)


def hbars(labels, series, nd=0, w=360, row=None, lab_w=None):
    """가로 막대 (모바일 · 품목 비교용). labels=[문자열] 위→아래 순서 그대로"""
    n, k = len(labels), len(series)
    if not n:
        return ''
    bh = 14 if k == 1 else 11
    row = row or (bh * k + 12)
    lab_w = lab_w or int(max(tw(l, 12) for l in labels) + 10)
    vmax = max([v or 0 for s in series for v in s['values']] + [0]) or 1
    vw = max(tw(fmt(v, nd), 12) for s in series for v in s['values']) + 8
    room = w - lab_w - vw - 4
    h = n * row + 6
    o = ['<svg viewBox="0 0 %d %d" role="img">' % (w, h)]
    for i, l in enumerate(labels):
        y0 = 3 + i * row + (row - bh * k) / 2
        o.append('<text class="yl" x="%d" y="%.1f">%s</text>' % (lab_w - 8, y0 + bh * k / 2 + 4, esc(l)))
        for j, s in enumerate(series):
            v = s['values'][i] or 0
            bw = max(0.0, room * v / vmax)
            y = y0 + bh * j
            o.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" fill="%s"/>' % (lab_w, y, bw, bh - 1, s['color']))
            o.append('<text class="vh" x="%.1f" y="%.1f">%s</text>' % (lab_w + bw + 5, y + bh / 2 + 3.6, fmt(v, nd)))
    o.append('</svg>')
    return ''.join(o)


def dual(labels2, series, nd=0, w=580, h=230, mob_labels=None):
    """PC 세로 막대 + 모바일 가로 막대 한 벌"""
    ml = mob_labels or [(a + ' ' + b).strip() for a, b in labels2]
    return ('<div class="ch-d">%s</div><div class="ch-m">%s</div>'
            % (vbars(labels2, series, nd, w, h), hbars(ml, series, nd)))


def legend(series):
    return '<div class="lg">%s</div>' % ''.join(
        '<span><i style="background:%s"></i>%s</span>' % (s['color'], esc(s['name'])) for s in series)


def _nice(vmin, vmax, n=4):
    import math
    span = (vmax - vmin) or abs(vmax) or 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=raw)
    lo = math.floor(vmin / step) * step
    hi = math.ceil(vmax / step) * step
    ticks, t = [], lo
    while t <= hi + step * 1e-9:
        ticks.append(t); t += step
    return lo, hi, ticks


def lines(xs, series, nd=0, w=1180, h=260, tick_every=12, fs=11.5):
    """월별 꺾은선. xs=['YYYY-MM',…], series=[{'name','color','values'(None=결측)}]
    - 선 끝(최근 값)과 시작 값에 수치 라벨, 라벨끼리 겹치지 않게 세로로 밀어냄
    - 오른쪽에 옅은 눈금(천 단위 콤마), x축은 해마다 1월 위치에 연도"""
    vals = [v for s in series for v in s['values'] if v is not None]
    if not vals or len(xs) < 2:
        return ''
    lo, hi, ticks = _nice(min(vals), max(vals))
    lab_w = max(tw(fmt(v, nd), fs) for v in vals) + 14
    L, R, T, B = 8 + lab_w, 10 + max(tw(fmt(t, nd), fs - 1) for t in ticks) + 8 + lab_w, 14, 30
    pw, ph = w - L - R, h - T - B
    X = lambda i: L + pw * i / (len(xs) - 1)
    Y = lambda v: T + ph - ph * (v - lo) / ((hi - lo) or 1)
    o = ['<svg viewBox="0 0 %d %d" role="img">' % (w, h)]
    for t in ticks:
        o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" class="grid"/>' % (L, L + pw, Y(t), Y(t)))
        o.append('<text class="tk" x="%.1f" y="%.1f" style="font-size:%.1fpx">%s</text>' % (w - 4, Y(t) + 4, fs - 1, fmt(t, nd)))
    for i, ym in enumerate(xs):
        if ym.endswith('-01') or i == 0:
            o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" class="xt"/>' % (X(i), X(i), T + ph, T + ph + 4))
            o.append('<text class="x" x="%.1f" y="%.1f" style="font-size:%.1fpx">%s</text>' % (X(i), T + ph + 18, fs, ym[:4]))
    ends, starts = [], []
    for s in series:
        seg, pts = [], []
        for i, v in enumerate(s['values']):
            if v is None:
                if len(seg) > 1:
                    pts.append(seg)
                elif len(seg) == 1:
                    pts.append(seg)
                seg = []
            else:
                seg.append((X(i), Y(v)))
        if seg:
            pts.append(seg)
        for sg in pts:
            if len(sg) == 1:
                o.append('<circle cx="%.1f" cy="%.1f" r="2.2" fill="%s"/>' % (sg[0][0], sg[0][1], s['color']))
            else:
                o.append('<polyline fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round" points="%s"/>'
                         % (s['color'], ' '.join('%.1f,%.1f' % p for p in sg)))
        idx = [i for i, v in enumerate(s['values']) if v is not None]
        if idx:
            ends.append([Y(s['values'][idx[-1]]), X(idx[-1]), s['values'][idx[-1]], s['color']])
            starts.append([Y(s['values'][idx[0]]), X(idx[0]), s['values'][idx[0]], s['color']])
    for group, side in ((ends, 'end'), (starts, 'start')):
        group.sort(key=lambda e: e[0])
        for k in range(1, len(group)):                       # 라벨 겹침 방지 (세로 최소 간격)
            if group[k][0] - group[k - 1][0] < fs + 2:
                group[k][0] = group[k - 1][0] + fs + 2
        for y, x, v, col in group:
            o.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (x, Y(v), col))
            if side == 'end':
                o.append('<text class="ve" x="%.1f" y="%.1f" style="font-size:%.1fpx;fill:%s">%s</text>' % (x + 6, y + 4, fs, col, fmt(v, nd)))
            else:
                o.append('<text class="vs" x="%.1f" y="%.1f" style="font-size:%.1fpx;fill:%s">%s</text>' % (x - 6, y + 4, fs, col, fmt(v, nd)))
    o.append('</svg>')
    return ''.join(o)
