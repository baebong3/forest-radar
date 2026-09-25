# -*- coding: utf-8 -*-
"""품목 그림 · 숲 장식 (빌드 시점 인라인 SVG, 외부 파일 없음)

  - 품목 그림은 64×64 기준의 단순 평면 일러스트 : 밤 · 호두 · 대추 · 표고버섯 · 떫은감 · 종합(소나무)
  - ridge() : 겹친 능선과 소나무 실루엣 (종합 브리핑 · 품목 머리 장식)
"""

PAL = {                      # 품목 색 : 주색 · 옅은 바탕 · 짙은 색
    'all':       ('#1F3D2B', '#EEF3EC', '#142A1D'),
    'chestnut':  ('#8A5226', '#F7EFE7', '#5C3415'),
    'walnut':    ('#66743A', '#F1F3E7', '#414B22'),
    'jujube':    ('#A3302E', '#FAEDEB', '#6C1C1B'),
    'shiitake':  ('#5A4E45', '#F2EFEC', '#372F29'),
    'persimmon': ('#D0661E', '#FDF0E5', '#8C3F0E'),
}


def _svg(body, size, cls='ico'):
    return ('<svg class="%s" viewBox="0 0 64 64" width="%d" height="%d" style="width:%dpx;height:%dpx" aria-hidden="true">%s</svg>'
            % (cls, size, size, size, size, body))


def chestnut(size=40):
    c, _, d = PAL['chestnut']
    return _svg(
        '<path d="M32 7c-1.5 3-3 4.5-6 7-7 5.5-13 13-13 23 0 11 8.5 19 19 19s19-8 19-19c0-10-6-17.5-13-23-3-2.5-4.5-4-6-7z" fill="%s"/>'
        '<path d="M13.6 42c2.6 8 9.8 14 18.4 14s15.8-6 18.4-14c-5 3-11.5 4.6-18.4 4.6S18.6 45 13.6 42z" fill="#EBD5B1"/>'
        '<circle cx="24" cy="51" r="1" fill="#CDAE82"/><circle cx="31" cy="53" r="1" fill="#CDAE82"/>'
        '<circle cx="38" cy="51.5" r="1" fill="#CDAE82"/><circle cx="44" cy="49" r="1" fill="#CDAE82"/><circle cx="19" cy="48" r="1" fill="#CDAE82"/>'
        '<path d="M23 21c-3.5 3.5-5.5 8-5.8 12.5" stroke="#fff" stroke-opacity=".38" stroke-width="3" stroke-linecap="round" fill="none"/>'
        '<path d="M30.4 9 32 3.2 33.6 9" stroke="%s" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        % (c, d), size)


def walnut(size=40):
    c, _, d = PAL['walnut']
    return _svg(
        '<ellipse cx="31" cy="37" rx="17" ry="20" fill="#C79D66"/>'
        '<path d="M31 17c-2.4 10 2.4 30 0 40" stroke="#8A6235" stroke-width="1.9" fill="none" stroke-linecap="round"/>'
        '<path d="M21 26c3 2 3 5 0 8M23 40c3 2 2 6-1 8M41 26c-3 2-3 5 0 8M39 40c-3 2-2 6 1 8M26 32c1.6 1 1.6 3 0 4M36 32c-1.6 1-1.6 3 0 4"'
        ' stroke="#9C7240" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
        '<path d="M19 33c0-5 2-9.5 5-12" stroke="#fff" stroke-opacity=".35" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
        '<path d="M33 15c5-8 15-10 22-6-4 7-13 10-22 6z" fill="%s"/>'
        '<path d="M35.5 14c5-3 11-4.5 17-5" stroke="#fff" stroke-opacity=".45" stroke-width="1.2" fill="none" stroke-linecap="round"/>'
        '<path d="M31 17.5 32.5 13" stroke="%s" stroke-width="2" stroke-linecap="round"/>' % (c, d), size)


def jujube(size=40):
    c, _, d = PAL['jujube']
    return _svg(
        '<ellipse cx="30" cy="39" rx="15" ry="19" transform="rotate(-16 30 39)" fill="%s"/>'
        '<path d="M42 30c3 6 3 14-1 20-3 4.5-8 7-13 7.5 8-3 13-10 14-17.5.4-3.4.3-6.8 0-10z" fill="%s" fill-opacity=".35"/>'
        '<ellipse cx="24" cy="31" rx="3.4" ry="7.5" transform="rotate(-16 24 31)" fill="#fff" fill-opacity=".32"/>'
        '<path d="M35 21c1-5 3-8.5 6.5-11" stroke="#6B4A2B" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
        '<path d="M41 10.5c5-6.5 13.5-7 17.5-3.5-4 6.5-12.5 8-17.5 3.5z" fill="#5E7F4F"/>'
        '<path d="M43.5 10c4-2 8.5-3 13-3.2" stroke="#fff" stroke-opacity=".45" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
        % (c, d), size)


def shiitake(size=40):
    c, _, d = PAL['shiitake']
    return _svg(
        '<path d="M26 37h12l-1.2 16.5c-.2 2.6-9.4 2.6-9.6 0z" fill="#EFE5D3"/>'
        '<path d="M28.5 40c.5 4 .5 9 0 13" stroke="#D6C7AE" stroke-width="1.3" fill="none" stroke-linecap="round"/>'
        '<path d="M7 33C7 18 18.5 9 32 9s25 9 25 24c0 3-2.5 5-6 5H13c-3.5 0-6-2-6-5z" fill="%s"/>'
        '<path d="M10 35.5c6 2.3 14 3 22 3s16-.7 22-3" stroke="%s" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        '<path d="M23 19.5l4.4-2.2 3 3.2-4.4 2.2zM36 16.2l5 1.2-1.2 4.2-4.6-1.3zM44.5 24l4.3 1.4-1.4 4-4.2-1.3zM15.8 27.2l4.3-1.1 1.2 4.1-4.2 1.1zM29.5 26.8h4.6l1 3.3-4.6 1.2zM38 29.5l3.6.5-.4 3-3.6-.4z"'
        ' fill="#E9DCC6" fill-opacity=".9"/>'
        '<path d="M15 21c3.5-5 8.5-8 14-9" stroke="#fff" stroke-opacity=".28" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
        % (c, d), size)


def persimmon(size=40):
    c, _, d = PAL['persimmon']
    return _svg(
        '<path d="M32 21c14.5 0 25 8 25 20.5C57 53 46 59 32 59S7 53 7 41.5C7 29 17.5 21 32 21z" fill="%s"/>'
        '<path d="M32 26c-2 9-2 21 0 32" stroke="%s" stroke-opacity=".22" stroke-width="2" fill="none" stroke-linecap="round"/>'
        '<ellipse cx="19" cy="36" rx="4" ry="7" transform="rotate(28 19 36)" fill="#fff" fill-opacity=".3"/>'
        '<ellipse cx="24.5" cy="23" rx="9" ry="3.6" transform="rotate(12 24.5 23)" fill="#5E7F4F"/>'
        '<ellipse cx="39.5" cy="23" rx="9" ry="3.6" transform="rotate(-12 39.5 23)" fill="#5E7F4F"/>'
        '<ellipse cx="32" cy="25.5" rx="3.6" ry="6.5" fill="#4E6B41"/>'
        '<ellipse cx="32" cy="19.5" rx="3.2" ry="5" fill="#6E8F5E"/>'
        '<rect x="30.6" y="12" width="2.8" height="8" rx="1.4" fill="#6B4A2B"/>' % (c, d), size)


def pine(size=40, c=None):
    c = c or PAL['all'][0]
    return _svg(
        '<rect x="29.5" y="46" width="5" height="12" rx="1.5" fill="#7A5A3A"/>'
        '<path d="M32 5 45 23H38.5L50 37H42l12 13H10l12-13h-8l11.5-14H19z" fill="%s"/>'
        '<path d="M32 5 45 23H38.5L50 37H42l12 13H32z" fill="#000" fill-opacity=".14"/>' % c, size)


ICON = {'chestnut': chestnut, 'walnut': walnut, 'jujube': jujube, 'shiitake': shiitake, 'persimmon': persimmon, 'all': pine}


def icon(key, size=40):
    return ICON.get(key, pine)(size)


def _tree(x, base, h, fill):
    w = h * .42
    return ('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="%s"/>'
            % (x, base - h, x + w * .55, base - h * .45, x + w * .3, base - h * .45, x + w * .75, base,
               x - w * .75, base, x - w * .3, base - h * .45, x - w * .55, base - h * .45, fill))


def ridge(w=560, h=150, tone=('#E6EDE2', '#CFDCC9', '#A9BBA2', '#5E7F4F', '#1F3D2B')):
    """겹친 능선 + 소나무 실루엣 (오른쪽이 높아지는 구도)"""
    a, b, c, t1, t2 = tone
    o = ['<svg class="ridge" viewBox="0 0 %d %d" preserveAspectRatio="xMaxYMax meet" aria-hidden="true">' % (w, h)]
    o.append('<path d="M0 %d C90 %d 150 %d 230 %d S380 %d 460 %d S540 %d %d %d V%d H0Z" fill="%s"/>'
             % (h * .72, h * .55, h * .5, h * .58, h * .2, h * .3, h * .12, w, h * .18, h, a))
    o.append('<path d="M0 %d C110 %d 190 %d 280 %d S430 %d %d %d V%d H0Z" fill="%s"/>'
             % (h * .86, h * .7, h * .66, h * .74, h * .45, w, h * .5, h, b))
    o.append('<path d="M0 %d C140 %d 260 %d 360 %d S480 %d %d %d V%d H0Z" fill="%s"/>'
             % (h * .96, h * .86, h * .9, h * .84, h * .7, w, h * .72, h, c))
    for x, base, th, col in ((300, h * .86, 30, t1), (322, h * .86, 42, t2), (344, h * .85, 26, t1),
                             (420, h * .78, 38, t1), (446, h * .77, 56, t2), (472, h * .76, 34, t1),
                             (500, h * .74, 46, t2), (528, h * .73, 30, t1), (548, h * .72, 40, t2)):
        o.append(_tree(x, base, th, col))
    o.append('</svg>')
    return ''.join(o)


def hill(c1, c2, w=600, h=70):
    """품목 머리 아래쪽의 낮은 두 겹 능선 (품목 색 옅은 톤)"""
    return ('<svg class="hill" viewBox="0 0 %d %d" preserveAspectRatio="none" aria-hidden="true">'
            '<path d="M0 %d C120 %d 220 %d 330 %d S520 %d %d %d V%d H0Z" fill="%s"/>'
            '<path d="M0 %d C150 %d 260 %d 380 %d S540 %d %d %d V%d H0Z" fill="%s"/></svg>'
            % (w, h, h * .55, h * .2, h * .35, h * .3, h * .05, w, h * .25, h, c1,
               h * .8, h * .55, h * .7, h * .6, h * .45, w, h * .55, h, c2))
