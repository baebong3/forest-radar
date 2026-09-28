# -*- coding: utf-8 -*-
"""시군구 경계(vuski/admdongkor sgg_20241231.parquet, 통계청 경계 기반) → data/sgg_geo.json
   - 일반구는 시 단위로 합침(임산물생산조사 집계 단위와 같게) → 229개 기초지자체
   - 단순화 후 SVG 좌표(가로 600)로 변환, 울릉군은 오른쪽 위 삽입 상자로 옮김
사용법 : python tools/make_sgg_geo.py sgg_20241231.parquet   (pip install pandas pyarrow shapely)"""
import json, re, sys
import pandas as pd, shapely
from shapely.ops import unary_union
from shapely import affinity

SIDO = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전',
        '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기', '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남',
        '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주'}
d = pd.read_parquet(sys.argv[1])
d['g'] = shapely.from_wkb(d.geom)
d['name'] = d.sggnm.map(lambda n: (re.match(r'^(.+?시)(.+구)$', n) or [None, n])[1])
units = []
for (sd, nm), g in d.groupby(['sidonm', 'name']):
    geo = unary_union(list(g.g)).buffer(0)
    units.append({'code': min(g.sggcd)[:4] + '0' if len(g) > 1 else min(g.sggcd), 'sido': SIDO[sd], 'name': nm, 'geo': geo})
ull = next(u for u in units if u['name'] == '울릉군')
main = unary_union([u['geo'] for u in units if u is not ull])
mx0, my0, mx1, my1 = main.bounds
# 울릉군 : 본토 오른쪽 위 삽입 상자 안으로 이동
ull['geo'] = max(list(ull['geo'].geoms), key=lambda q: q.area) if ull['geo'].geom_type != 'Polygon' else ull['geo']   # 울릉도 본섬(독도 등 작은 섬 제외)
ub = ull['geo'].bounds
box_w = 44000
tx, ty = mx1 - box_w / 2 - (ub[0] + ub[2]) / 2 + 10000, (my1 - 60000) - (ub[1] + ub[3]) / 2
ull['geo'] = affinity.translate(ull['geo'], tx, ty)
bx = ((ub[0] + ub[2]) / 2 + tx - 20000, (ub[1] + ub[3]) / 2 + ty - 18000, (ub[0] + ub[2]) / 2 + tx + 20000, (ub[1] + ub[3]) / 2 + ty + 18000)
x0, y0, x1, y1 = mx0, my0, max(mx1, bx[2]), max(my1, bx[3])
W = 600.0
s = W / (x1 - x0)
H = (y1 - y0) * s
P = lambda x, y: (round((x - x0) * s, 1), round((y1 - y) * s, 1))


def path(geo):
    geo = geo.simplify(260, preserve_topology=True)
    polys = [geo] if geo.geom_type == 'Polygon' else list(geo.geoms)
    out = []
    for p in polys:
        if p.area < 2.5e5:                           # 아주 작은 섬은 생략
            continue
        for ring in [p.exterior] + list(p.interiors):
            pts = [P(x, y) for x, y in ring.coords]
            ded = [pts[0]] + [q for a, q in zip(pts, pts[1:]) if q != a]
            if len(ded) >= 4:
                out.append('M' + 'L'.join('%g,%g' % q for q in ded[:-1]) + 'Z')
    return ''.join(out)


res = []
for u in sorted(units, key=lambda u: u['code']):
    c = u['geo'].representative_point()
    if u['name'] in ('제주시', '서귀포시', '고성군', '울릉군', '옹진군', '신안군', '완도군', '진도군', '통영시', '거제시', '여수시'):
        c = max(([u['geo']] if u['geo'].geom_type == 'Polygon' else list(u['geo'].geoms)), key=lambda p: p.area).representative_point()
    res.append({'code': u['code'], 'sido': u['sido'], 'name': u['name'], 'd': path(u['geo']), 'c': P(c.x, c.y)})
sido = {}
for sd in SIDO.values():
    g = unary_union([u['geo'] for u in units if u['sido'] == sd and u is not ull])
    sido[sd] = path(g)
bxp = [P(bx[0], bx[3]), P(bx[2], bx[1])]
json.dump({'w': W, 'h': round(H, 1), 'units': res, 'sido': sido, 'inset': bxp}, open('data/sgg_geo.json', 'w'), ensure_ascii=False,
          separators=(',', ':'))
print(len(res), round(H), sum(len(r['d']) for r in res) // 1024, 'KB')
