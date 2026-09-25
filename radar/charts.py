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
