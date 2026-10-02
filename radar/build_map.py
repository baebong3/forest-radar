# -*- coding: utf-8 -*-
"""임산물 생산지도 : 산림청 임산물생산조사 전 품목 × 229개 시군구 → docs/map/index.html

  - 품목(120여 종)을 고르면 주 생산지 1~10위를 지도 · 순위표로 보여 줌 (몇 위까지 볼지 1~10 선택)
  - 지도나 순위의 지역을 누르면 그 지역의 3년 추이와 「그 지역이 10위 안에 드는 다른 품목」을 보여 줌
  - 경계 : data/sgg_geo.json (tools/make_sgg_geo.py, 2024년 말 시군구 경계, 일반구는 시로 합침)
  - 자료 : data/prod_txt/연도.txt.gz (radar/dump_prod_txt.py) → radar/prodmap_parse.py
  - 검증 게이트 : 전국 합계가 시도 + 국유림 합계와 맞지 않거나, 밤 전국값이 기존 5년 표와 다르면 페이지를 쓰지 않음

사용법 : python radar/build_map.py
"""
import json, os, re, sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, ROOT, db
from prodmap_parse import CATS, CAT_OF, parse_year, years

OUT = os.path.join(ROOT, 'docs', 'map', 'index.html')
GEO = os.path.join(ROOT, 'data', 'sgg_geo.json')

CAT_COL = {'수실류': '#8A5226', '버섯': '#5A4E45', '산나물': '#4F7A3E', '약용식물': '#8A6A1E', '수액': '#2F7280',
           '수목부산물': '#7A5C3E', '연료 · 농용자재': '#5C5347', '용재 · 순임목': '#1F3D2B', '조경수': '#2E6B4A',
           '분재 · 잔디 · 화훼': '#9A4257'}
CAT_ICON = {'수실류': '●', '버섯': '♠', '산나물': '❦', '약용식물': '✚', '수액': '◆', '수목부산물': '▲', '연료 · 농용자재': '■',
            '용재 · 순임목': '▮', '조경수': '♣', '분재 · 잔디 · 화훼': '✿'}


def build_data():
    geo = json.load(open(GEO, encoding='utf-8'))
    idx = {(u['sido'], u['name']): i for i, u in enumerate(geo['units'])}
    ys = [y for y in years()]
    per = {}
    for y in ys:
        r = parse_year(y)
        if len(r['sgg']) < 150:                        # 옛 보고서(글꼴 깨짐)
            continue
        if '세종' in r['sido'] and ('세종', '세종시') not in r['sgg']:
            r['sgg'][('세종', '세종시')] = r['sido']['세종']
        per[y] = r
    ys = sorted(per)
    order = [n for _, names in CATS for n in names.split()]
    ids = []
    for y in ys:
        for grp in ('sido', 'inst', 'sgg'):
            for e in per[y][grp].values():
                for k in e:
                    if k not in ids:
                        ids.append(k)
    base = lambda k: k.split('(')[0] if re.search(r'\((조경수|분재소재|분재완재)\)$', k) else k
    ids.sort(key=lambda k: (order.index(base(k)) if base(k) in order else 999, k))
    items, errs = [], []
    for k in ids:
        unit = None
        nat, natw, inst, vals = [], [], [], {}
        for y in ys:
            r = per[y]
            n = w = ins = 0.0
            for e in r['sido'].values():
                if k in e:
                    unit = e[k][0]; n += e[k][1]; w += e[k][2]
            for e in r['inst'].values():
                if k in e:
                    unit = e[k][0]; n += e[k][1]; w += e[k][2]; ins += e[k][1]
            sg = []
            ssum = 0.0
            for key, e in r['sgg'].items():
                if k in e and e[k][1] > 0 and key in idx:
                    sg.append([idx[key], e[k][1], round(e[k][2] / 1e6, 1)])
                    ssum += e[k][1]
            sg.sort(key=lambda a: -a[1])
            nat.append(n); natw.append(round(w / 1e6, 1)); inst.append(ins)
            vals[str(y)] = sg
            if n and ssum > n * 1.02:
                errs.append('%s %d : 시군구 합 %s > 전국 %s' % (k, y, ssum, n))
        if not any(nat):
            continue
        cat = CAT_OF.get(base(k), '기타')
        if re.search(r'\((분재소재|분재완재)\)$', k) or base(k) in ('한지형잔디', '난지형잔디', '야생화', '자생란'):
            cat = '분재 · 잔디 · 화훼'
        du, div = unit, 1
        if unit == 'kg' and max(nat) >= 100000:
            du, div = '톤', 1000
        items.append({'id': k, 'cat': cat, 'unit': unit, 'du': du, 'div': div, 'nat': nat, 'natw': natw, 'inst': inst, 'vals': vals})
    return geo, ys, items, errs


def verify(items, ys):
    errs = []
    chk = {'밤': {2022: 43220, 2023: 39797, 2024: 37010}, '떫은감': {2022: 185592, 2023: 150652, 2024: 166088}}
    by = {it['id']: it for it in items}
    for k, d in chk.items():
        for y, v in d.items():
            if y in ys and k in by:
                got = by[k]['nat'][ys.index(y)] / 1000
                if abs(got - v) > 1:
                    errs.append('%s %d 전국 %s톤 ≠ 보고서 %s톤' % (k, y, round(got), v))
    if len(items) < 100:
        errs.append('품목 수 %d개 (100개 미만)' % len(items))
    return errs


HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>임산물 생산지도</title>
<meta name="description" content="산림청 임산물생산조사 120여 개 품목의 시군구별 주 생산지 순위 지도">
<style>
@font-face{font-family:'PretendardSub';font-weight:400;font-display:swap;src:url(../assets/fonts/pretendard-sub-Regular.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:600;font-display:swap;src:url(../assets/fonts/pretendard-sub-SemiBold.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:800;font-display:swap;src:url(../assets/fonts/pretendard-sub-ExtraBold.woff2) format('woff2')}
:root{color-scheme:light;--green:#1F3D2B;--moss:#5E7F4F;--ink:#17211B;--sub:#4B5A50;--muted:#86928A;--rule:#E3E8E1;--rule2:#EFF2ED;
  --tint:#EEF3EC;--amber:#C7771F;--c:#1F3D2B}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:var(--ink);font-size:14px;line-height:1.5;letter-spacing:-.1px;
  font-family:'PretendardSub','Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif}
a{color:inherit;text-decoration:none}
button{font:inherit;color:inherit}
.mast .in{max-width:1400px;margin:0 auto;padding:14px 16px 12px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.logos{display:flex;align-items:center;gap:12px}
.lg-sp{height:24px;width:auto;display:block}.lg-kf{height:32px;width:auto;display:block}
.logos .x{font-size:14px;color:var(--muted);font-weight:600}
.vr{width:1px;height:30px;background:var(--rule)}
.team{display:flex;flex-direction:column;line-height:1.25}
.team .t1{font-size:12px;font-weight:600;color:var(--muted)}
.team .t2{font-size:18px;font-weight:800;letter-spacing:-.5px;color:var(--green)}
.nav{margin-left:auto;display:flex;gap:6px}
.nav a{border:1px solid var(--rule);border-radius:999px;padding:6px 14px;font-size:13px;font-weight:800;color:var(--sub)}
.nav a.on{background:var(--green);border-color:var(--green);color:#fff}
.ribbon{height:5px;background:linear-gradient(90deg,#1F3D2B 0 40%,#5E7F4F 40% 70%,#8A5226 70% 88%,#C7771F 88%)}
.wrap{max-width:1400px;margin:0 auto;padding:18px 16px 40px}
.lay{display:grid;grid-template-columns:260px minmax(0,1fr) 360px;gap:16px;align-items:start}
.card{border:1px solid var(--rule);border-radius:14px;background:#fff;min-width:0}
/* 품목 고르기 */
.pick{position:sticky;top:12px;display:flex;flex-direction:column;max-height:calc(100vh - 24px)}
.pick .hd{padding:14px 14px 10px;border-bottom:1px solid var(--rule2)}
.pick .ttl{font-size:12px;font-weight:800;letter-spacing:1.2px;color:var(--moss)}
.srch{width:100%;margin-top:8px;border:1px solid var(--rule);border-radius:10px;padding:8px 10px;font:inherit;font-size:13.5px;outline:none}
.srch:focus{border-color:var(--green)}
.cats{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.cats button{border:1px solid var(--rule);background:#fff;border-radius:999px;padding:2px 9px;font-size:11.5px;font-weight:700;color:var(--sub);cursor:pointer}
.cats button.on{background:var(--c);border-color:var(--c);color:#fff}
.list{overflow-y:auto;padding:4px 6px 10px;flex:1}
.grp{font-size:11.5px;font-weight:800;color:var(--c);padding:10px 8px 4px;display:flex;align-items:center;gap:6px}
.grp i{font-style:normal}
.it{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 8px;width:100%;text-align:left;border:0;background:none;border-radius:8px;padding:6px 8px;cursor:pointer}
.it:hover{background:#F5F7F4}
.it.on{background:var(--c);color:#fff}
.it b{font-size:13.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:clip}
.it span{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;align-self:center}
.it.on span{color:rgba(255,255,255,.8)}
.it i{grid-column:1/-1;height:3px;border-radius:2px;background:var(--rule2);position:relative;overflow:hidden}
.it i:after{content:'';position:absolute;left:0;top:0;bottom:0;width:var(--w);background:var(--c);opacity:.55}
.it.on i{background:rgba(255,255,255,.25)}.it.on i:after{background:#fff;opacity:.9}
.msel{display:none}
/* 가운데 */
.head{display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap;padding:16px 20px 8px}
.head .cat{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:800;color:#fff;background:var(--c);border-radius:999px;padding:2px 10px}
.head h1{margin:6px 0 0;font-size:28px;font-weight:800;letter-spacing:-1px;line-height:1.2}
.head h1 small{font-size:14px;font-weight:600;color:var(--muted);margin-left:8px;letter-spacing:0}
.ctl{margin-left:auto;display:flex;flex-direction:column;gap:6px;align-items:flex-end}
.seg{display:inline-flex;border:1px solid var(--rule);border-radius:10px;overflow:hidden}
.seg button{border:0;background:#fff;padding:5px 11px;font-size:12.5px;font-weight:800;color:var(--sub);cursor:pointer;font-variant-numeric:tabular-nums}
.seg button+button{border-left:1px solid var(--rule)}
.seg button.on{background:var(--c);color:#fff}
.seg.n button{padding:5px 8px;min-width:28px}
.ctl label{font-size:11.5px;color:var(--muted);font-weight:700;margin-right:6px}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:8px 20px 4px}
.kpi{border:1px solid var(--rule2);border-radius:12px;padding:10px 12px;background:#FAFBF9;min-width:0}
.kpi .l{font-size:12px;font-weight:800;color:var(--sub)}
.kpi .v{font-size:21px;font-weight:800;letter-spacing:-.6px;font-variant-numeric:tabular-nums;white-space:nowrap;line-height:1.3}
.kpi .v small{font-size:12px;color:var(--muted);font-weight:600;margin-left:2px;letter-spacing:0}
.kpi .s{font-size:11.5px;color:var(--muted);white-space:nowrap;overflow:hidden}
.up{color:#B23A2A;font-weight:800}.dn{color:#2E6DA4;font-weight:800}
.mapw{position:relative;padding:6px 12px 12px}
#map{width:100%;height:auto;display:block;max-height:78vh}
#map .u{fill:#F4F6F3;stroke:#fff;stroke-width:.5;cursor:pointer;transition:fill .2s}
#map .u.o{fill:var(--o)}
#map .u.t{stroke:#fff;stroke-width:.7}
#map .u:hover{stroke:var(--ink);stroke-width:1.2}
#map .u.sel{stroke:var(--amber);stroke-width:2.4}
#map .sd{fill:none;stroke:#A7B3AA;stroke-width:.9;pointer-events:none}
#map .ins{fill:none;stroke:#C9D1C9;stroke-dasharray:3 3}
#map .mk circle{stroke:#fff;stroke-width:1.6}
#map .mk text{fill:#fff;font-size:10.5px;font-weight:800;text-anchor:middle;dominant-baseline:central;pointer-events:none;font-variant-numeric:tabular-nums}
#map .mk line{stroke:#6F7B72;stroke-width:.8}
#map .mk{cursor:pointer}
#map .sel-mk circle{stroke:var(--amber);stroke-width:2.6}
.leg{position:absolute;left:24px;bottom:22px;background:rgba(255,255,255,.92);border:1px solid var(--rule2);border-radius:10px;padding:8px 10px;font-size:11.5px;color:var(--sub)}
.leg .r{display:flex;gap:2px;margin-top:4px}
.leg .r i{width:22px;height:10px;border-radius:2px;display:block}
.leg .r2{display:flex;justify-content:space-between;font-size:10.5px;color:var(--muted);margin-top:2px}
.leg label{display:flex;align-items:center;gap:5px;margin-top:6px;cursor:pointer}
.tip{position:fixed;pointer-events:none;background:#17211B;color:#fff;border-radius:8px;padding:7px 10px;font-size:12.5px;line-height:1.45;z-index:50;display:none;white-space:nowrap}
.tip b{font-weight:800}
.note{font-size:11.5px;color:var(--muted);padding:0 20px 14px;word-break:keep-all}
/* 오른쪽 */
.side{display:flex;flex-direction:column;gap:16px}
.box{padding:16px 18px}
.sec{display:flex;align-items:center;gap:7px;font-size:11px;font-weight:800;letter-spacing:1.4px;color:var(--c)}
.sec:before{content:'';width:10px;height:10px;background:var(--c);border-radius:0 70% 0 70%;flex:none}
.h2{font-size:18px;font-weight:800;letter-spacing:-.5px;margin:4px 0 2px;word-break:keep-all}
.cap{font-size:12px;color:var(--muted);margin-bottom:8px}
.rk{list-style:none;margin:0;padding:0}
.rk li{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:2px 8px;align-items:center;padding:7px 6px;border-bottom:1px solid var(--rule2);cursor:pointer;border-radius:8px}
.rk li:hover{background:#F6F8F5}
.rk li.sel{background:#FBF3E8}
.rk .no{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;color:#fff;font-size:12px;font-weight:800;grid-row:span 2}
.rk .nm{font-size:14px;font-weight:800;white-space:nowrap}
.rk .nm small{font-size:11.5px;color:var(--muted);font-weight:600;margin-left:4px}
.rk .v{font-size:13.5px;font-weight:800;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.rk .bar{height:5px;border-radius:3px;background:var(--rule2);position:relative;overflow:hidden}
.rk .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:3px}
.rk .sh{font-size:11.5px;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.rk li.rest{cursor:default;color:var(--muted)}
.rk li.rest:hover{background:none}
.det .emp{font-size:13px;color:var(--muted);background:#F6F8F5;border-radius:10px;padding:14px;word-break:keep-all}
.det .rg{font-size:20px;font-weight:800;letter-spacing:-.6px}
.det .rg small{font-size:12.5px;color:var(--muted);font-weight:600;margin-left:6px}
.det dl{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0 0;font-size:13px}
.det dt{color:var(--sub);font-weight:600}
.det dd{margin:0;text-align:right;font-weight:800;font-variant-numeric:tabular-nums}
.det .yb{display:grid;grid-template-columns:repeat(var(--n),1fr);gap:8px;align-items:end;height:92px;margin:14px 0 4px}
.det .yb div{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%}
.det .yb i{display:block;width:70%;border-radius:4px 4px 0 0;background:var(--c);opacity:.35}
.det .yb div.last i{opacity:1}
.det .yb em{font-style:normal;font-size:11.5px;font-weight:800;font-variant-numeric:tabular-nums;margin-bottom:3px;white-space:nowrap}
.det .yl{display:grid;grid-template-columns:repeat(var(--n),1fr);gap:8px;font-size:11.5px;color:var(--muted);text-align:center}
.det h4{font-size:12.5px;font-weight:800;margin:16px 0 6px;color:var(--sub)}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chips button{border:1px solid var(--rule);background:#fff;border-radius:999px;padding:3px 10px 3px 4px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.chips button b{display:inline-grid;place-items:center;min-width:18px;height:18px;border-radius:50%;color:#fff;font-size:10.5px;padding:0 3px}
.chips button:hover{border-color:var(--ink)}
.rk li.hd2{cursor:default;padding:10px 6px 2px;border-bottom:0}.rk li.hd2 .nm{font-size:12.5px;color:var(--sub)}
.csv{display:block;width:100%;margin-top:12px;border:1px solid var(--c);color:var(--c);background:#fff;border-radius:999px;padding:7px;font-size:12.5px;font-weight:800;cursor:pointer}
.csv:hover{background:var(--c);color:#fff}
.rsel{width:100%;border:1px solid var(--rule);border-radius:10px;padding:7px 9px;font:inherit;font-size:13px;margin:6px 0 12px;background:#fff}
.rt{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}
.rt th{font-size:11.5px;color:var(--sub);font-weight:800;text-align:center;border-bottom:1.5px solid var(--ink);padding:5px 4px;line-height:1.3}
.rt th:first-child{text-align:left}
.rt td{padding:6px 4px;border-bottom:1px solid var(--rule2);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.rt td:first-child{text-align:left;font-weight:700;white-space:normal}
.rt td:first-child i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px}
.rt td:last-child{text-align:center}
.rt b.t10{display:inline-block;min-width:22px;border-radius:999px;background:var(--c);color:#fff;font-size:11px;padding:0 5px}
.rt tr{cursor:pointer}.rt tr:hover td{background:#F6F8F5}.rt tr.cur td{background:#FBF3E8}
.rt tr.ex{display:none}.det.all .rt tr.ex{display:table-row}
.mbtn2{display:block;width:100%;margin-top:8px;border:0;background:#F3F6F2;border-radius:8px;padding:6px;font-size:12px;font-weight:800;color:var(--sub);cursor:pointer}
.foot{margin:26px 0 0;padding:16px 0 0;border-top:1px solid var(--rule);font-size:12px;color:var(--muted);line-height:1.7}
.foot b{color:var(--sub)}
@media(max-width:1180px){.lay{grid-template-columns:230px minmax(0,1fr)}.side{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr}}
@media(max-width:820px){
  .lay{grid-template-columns:1fr}.side{grid-template-columns:1fr}
  .pick{position:static;max-height:none}.pick .list{display:none}.msel{display:block;width:100%;margin-top:8px;border:1px solid var(--rule);border-radius:10px;padding:9px 10px;font:inherit;font-size:14.5px;font-weight:700;background:#fff}
  .head{padding:14px 14px 6px}.head h1{font-size:23px}.ctl{margin-left:0;align-items:flex-start}
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr));padding:6px 14px}.kpi .v{font-size:18px}
  .mapw{padding:4px 4px 8px}.leg{position:static;margin:6px 10px 0}.note{padding:0 14px 12px}
  .vr{display:none}.lg-sp{height:20px}.lg-kf{height:27px}.nav{margin-left:0}
}
</style></head><body>
<header class="mast"><div class="in"><div class="logos"><img class="lg-sp" src="../assets/logo_southernpost.png" alt="서던포스트">
<span class="x">×</span><img class="lg-kf" src="../assets/logo_kofpi.png" alt="한국임업진흥원"></div><div class="vr"></div>
<div class="team"><span class="t1">산림청 임산물생산조사 · 시군구 주 생산지 순위</span><span class="t2">임산물 생산지도</span></div>
<nav class="nav"><a href="../">수급 레이더</a><a class="on" href="./">생산지도</a></nav></div><div class="ribbon"></div></header>
<main class="wrap"><div class="lay">
<aside class="card pick"><div class="hd"><div class="ttl">품목 고르기 · __NITEMS__종</div>
<input class="srch" id="q" type="search" placeholder="품목 이름 찾기 (예 : 오미자)" autocomplete="off">
<div class="cats" id="cats"></div><select class="msel" id="msel" aria-label="품목"></select></div><div class="list" id="list"></div></aside>
<section class="card"><div class="head"><div><span class="cat" id="hcat"></span><h1 id="htitle"></h1></div>
<div class="ctl"><div><label>조사 연도</label><span class="seg" id="yseg"></span></div><div><label>주 생산지</label><span class="seg n" id="nseg"></span></div>
<div><label>기준</label><span class="seg" id="mseg"></span><label style="margin-left:10px">보기</label><span class="seg" id="vseg"></span></div></div></div>
<div class="kpis" id="kpis"></div>
<div class="mapw"><svg id="map" role="img" aria-label="시군구 생산지도"></svg>
<div class="leg" id="leg"></div></div>
<div class="note" id="note"></div></section>
<aside class="side"><div class="card box"><div class="sec">RANKING</div><div class="h2" id="rtitle"></div><div class="cap" id="rcap"></div><ul class="rk" id="rank"></ul><button class="csv" id="csv1">전체 시군구 표 내려받기 (CSV)</button></div>
<div class="card box det" id="detc"><div class="sec">REGION</div><div class="h2">지역 상세</div><div id="det"></div></div></aside>
</div>
<footer class="foot"><b>자료</b> 산림청 「임산물생산조사」 연도별 보고서 부록 시군구 통계표(__YEARS__년) · 경계는 2024년 말 시군구(일반구는 시로 합침, 229개)<br>
<b>읽는 법</b> 순위 · 비중은 고른 기준(생산량 또는 생산액)의 시군구 값 · 변동 보기는 첫 조사 연도와 고른 연도의 차이 · 전국 합계에는 지방산림청 · 국립기관(국유림) 생산분이 포함되어 시군구 합보다 클 수 있음 · 군위군은 2023년 대구 편입에 맞춰 대구로 표기 · 생산액은 백만 원<br>
<b>갱신</b> 새 연도 보고서가 공표되면 매일 07:00 자동 실행 때 반영 · 페이지 작성 __BUILT__ · <b>(주)서던포스트</b></footer></main>
<div class="tip" id="tip"></div>
<script>
const G=__GEO__, D=__DATA__, CC=__CATCOL__, CI=__CATICON__;
const $=s=>document.querySelector(s);
const Y=D.years, U=G.units;
let S={item:'밤', y:Y[Y.length-1], n:10, sel:null, cat:'전체', rest:false, m:'q', v:'rank', rall:false};
try{const h=new URLSearchParams(location.hash.slice(1));if(h.get('i'))S.item=h.get('i');if(h.get('y'))S.y=+h.get('y');if(h.get('n'))S.n=Math.max(1,Math.min(10,+h.get('n')));if(h.get('r'))S.sel=+h.get('r');if(h.get('m')=='w')S.m='w';if(h.get('v')=='chg')S.v='chg';}catch(e){}
const IT={};D.items.forEach(it=>IT[it.id]=it);
if(!IT[S.item])S.item=D.items[0].id; if(Y.indexOf(S.y)<0)S.y=Y[Y.length-1];
function fmt(v,nd){if(v==null||isNaN(v))return '-';const p=Math.pow(10,nd||0);const r=Math.round(Math.abs(v)*p+1e-9)/p*(v<0?-1:1);
  return r.toLocaleString('en-US',{minimumFractionDigits:nd||0,maximumFractionDigits:nd||0});}
function nd(it){return it.div>1?1:0}
function dv(it,q){return q/it.div}
function pctx(a,b){if(!b)return null;return (a-b)/b*100}
function ptxt(p){if(p==null)return '<span>-</span>';const r=Math.round(p*10)/10;return '<span class="'+(r>0?'up':r<0?'dn':'')+'">'+(r>0?'+':'')+fmt(r,1)+'%</span>'}
function mix(a,b,t){const h=x=>[1,3,5].map(i=>parseInt(x.substr(i,2),16));const A=h(a),B=h(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('')}
function col(it){return CC[it.cat]||'#1F3D2B'}
function rankCol(it,r,n){const c=col(it);return mix(mix(c,'#FFFFFF',.72),mix(c,'#000000',.18),n<=1?1:1-(r)/(n-1)*.9)}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function label(u){return U[u].sido+' '+U[u].name}
// ── 지도 틀 ──
const svg=$('#map');svg.setAttribute('viewBox','-4 -4 '+(G.w+8)+' '+(G.h+8));
let g='';U.forEach((u,i)=>{g+='<path class="u" data-i="'+i+'" d="'+u.d+'"/>'});
let sd='';for(const k in G.sido)sd+='<path class="sd" d="'+G.sido[k]+'"/>';
const ib=G.inset;
svg.innerHTML='<g id="gu">'+g+'</g><g>'+sd+'</g><rect class="ins" x="'+ib[0][0]+'" y="'+ib[0][1]+'" width="'+(ib[1][0]-ib[0][0])+'" height="'+(ib[1][1]-ib[0][1])+'" rx="6"/><text x="'+(ib[0][0]+4)+'" y="'+(ib[0][1]-4)+'" style="font-size:9px;fill:#86928A">울릉군</text><g id="mk"></g>';
const P=[...svg.querySelectorAll('.u')];
// ── 품목 목록 ──
const cats=['전체'].concat(Object.keys(CC).filter(c=>D.items.some(i=>i.cat==c)));
function drawCats(){$('#cats').innerHTML=cats.map(c=>'<button data-c="'+c+'" class="'+(S.cat==c?'on':'')+'" style="--c:'+(CC[c]||'#1F3D2B')+'">'+(CI[c]?CI[c]+' ':'')+c+'</button>').join('')}
function drawList(){
  const q=$('#q').value.trim();const yi=Y.indexOf(S.y);let h='';
  cats.slice(1).forEach(c=>{
    if(S.cat!='전체'&&S.cat!=c)return;
    const its=D.items.filter(i=>i.cat==c&&(!q||i.id.indexOf(q)>=0));if(!its.length)return;
    const mx=Math.max(...its.map(i=>i.nat[yi]||0))||1;
    h+='<div class="grp" style="--c:'+CC[c]+'"><i>'+CI[c]+'</i>'+c+'</div>';
    its.forEach(i=>{const v=i.nat[yi]||0;h+='<button class="it'+(i.id==S.item?' on':'')+'" data-i="'+esc(i.id)+'" style="--c:'+CC[c]+';--w:'+Math.max(2,v/mx*100)+'%"><b>'+esc(i.id)+'</b><span>'+(v?fmt(dv(i,v),nd(i))+' '+i.du:'생산 없음')+'</span><i></i></button>'});
  });
  $('#list').innerHTML=h||'<div class="grp">찾는 품목이 없음</div>';
  $('#msel').innerHTML=cats.slice(1).map(c=>'<optgroup label="'+c+'">'+D.items.filter(i=>i.cat==c).map(i=>'<option'+(i.id==S.item?' selected':'')+'>'+esc(i.id)+'</option>').join('')+'</optgroup>').join('');
  const on=$('#list .it.on');if(on&&on.scrollIntoViewIfNeeded)on.scrollIntoViewIfNeeded(false);
}
// ── 본문 ──
const MN={q:'생산량',w:'생산액'};
function rk(it,y){                                   // [{i,q,w,v}] : v = 고른 기준(생산량 · 생산액)으로 내림차순
  return (it.vals[String(y)]||[]).map(r=>({i:r[0],q:r[1],w:r[2],v:S.m=='w'?r[2]:r[1]})).filter(r=>r.v>0).sort((a,b)=>b.v-a.v)}
function natv(it,yi){return S.m=='w'?it.natw[yi]:it.nat[yi]}
function vu(it){return S.m=='w'?'백만 원':it.du}
function vf(it,v){return S.m=='w'?fmt(v,v<100?1:0):fmt(dv(it,v),nd(it))}
function seg(id,arr,cur,attr){$(id).innerHTML=arr.map(([k,l])=>'<button '+attr+'="'+k+'" class="'+(k==cur?'on':'')+'">'+l+'</button>').join('')}
function draw(){
  const it=IT[S.item],yi=Y.indexOf(S.y),c=col(it),R=rk(it,S.y),top=R.slice(0,S.n),n=top.length;
  document.documentElement.style.setProperty('--c',c);
  $('#hcat').innerHTML=(CI[it.cat]||'')+' '+it.cat;
  $('#htitle').innerHTML=esc(it.id)+'<small>'+S.y+'년 · 단위 '+vu(it)+'</small>';
  seg('#yseg',Y.map(y=>[y,y]),S.y,'data-y');
  seg('#nseg',[1,2,3,4,5,6,7,8,9,10].map(k=>[k,k]),S.n,'data-n');
  seg('#mseg',[['q','생산량'],['w','생산액']],S.m,'data-m');
  seg('#vseg',[['rank','순위'],['chg',Y[0]+'→'+S.y+' 변동']],S.v,'data-v');
  const nat=natv(it,yi),pn=yi>0?natv(it,yi-1):null,tsum=top.reduce((a,b)=>a+b.v,0);
  const k=(l,v,u,s)=>'<div class="kpi"><div class="l">'+l+'</div><div class="v">'+v+'<small>'+u+'</small></div><div class="s">'+s+'</div></div>';
  $('#kpis').innerHTML=k('전국 '+MN[S.m],vf(it,nat),vu(it),yi>0?'전년 대비 '+ptxt(pctx(nat,pn)):(S.m=='q'?'생산액 '+fmt(it.natw[yi],0)+'백만 원':''))
    +k('상위 '+S.n+'곳 비중',nat?fmt(tsum/nat*100,1):'-','%','전국 '+MN[S.m]+' 대비')
    +k('1위 생산지',R.length?esc(U[R[0].i].name):'-','',R.length?esc(U[R[0].i].sido)+' · 전국의 '+fmt(R[0].v/nat*100,1)+'%':'시군구 생산 없음')
    +k('생산 시군구',fmt(R.length,0),'곳',(it.inst[yi]&&it.nat[yi])?'국유림 생산분 '+fmt(it.inst[yi]/it.nat[yi]*100,1)+'% 별도':'229개 시군구 중');
  if(S.v=='chg'){drawChg(it,c);drawDet();saveHash();return}
  // 지도 : 순위
  const ri={};R.forEach((r,x)=>ri[r.i]=x);
  P.forEach(p=>{const i=+p.dataset.i;p.classList.remove('o','t','sel');p.style.removeProperty('--o');
    if(i in ri&&ri[i]<S.n){p.classList.add('o','t');p.style.setProperty('--o',rankCol(it,ri[i],S.n))}
    else if(S.rest&&i in ri){p.classList.add('o');p.style.setProperty('--o',mix(c,'#FFFFFF',.88))}
    if(S.sel===i)p.classList.add('sel');});
  const K=Math.min(1.7,Math.max(1,600/(svg.clientWidth||600)*.85)),RR=9.5*K,DD=21*K;
  const pts=top.map((r,x)=>({i:r.i,r:x,x:U[r.i].c[0],y:U[r.i].c[1],x0:U[r.i].c[0],y0:U[r.i].c[1]}));
  for(let t=0;t<60;t++){let mv=false;for(let a=0;a<pts.length;a++)for(let b=a+1;b<pts.length;b++){const A=pts[a],B=pts[b];let dx=B.x-A.x,dy=B.y-A.y,d=Math.hypot(dx,dy)||.01;
    if(d<DD){const m=(DD-d)/2;dx/=d;dy/=d;A.x-=dx*m;A.y-=dy*m;B.x+=dx*m;B.y+=dy*m;mv=true}}if(!mv)break}
  $('#mk').innerHTML=pts.map(p=>(Math.hypot(p.x-p.x0,p.y-p.y0)>3?'<line x1="'+p.x0+'" y1="'+p.y0+'" x2="'+p.x+'" y2="'+p.y+'"/>':'')
    +'<g class="mk'+(S.sel===p.i?' sel-mk':'')+'" data-i="'+p.i+'"><circle cx="'+p.x+'" cy="'+p.y+'" r="'+RR+'" fill="'+mix(c,'#000000',.12)+'"/><text x="'+p.x+'" y="'+(p.y+.5)+'" style="font-size:'+(10.5*K)+'px">'+(p.r+1)+'</text></g>').join('');
  const sw=[];for(let r=0;r<Math.max(n,1);r++)sw.push('<i style="background:'+rankCol(it,r,Math.max(n,1))+'"></i>');
  $('#leg').innerHTML='<b>주 생산지 순위 · '+MN[S.m]+' 기준</b><div class="r">'+sw.join('')+'</div><div class="r2"><span>1위</span><span>'+Math.max(n,1)+'위</span></div>'
    +'<label><input type="checkbox" id="rest"'+(S.rest?' checked':'')+'> '+(S.n)+'위 밖 생산지도 옅게 표시</label>';
  $('#note').innerHTML='지도와 순위의 지역을 누르면 오른쪽에 지역 상세가 나옴 · 원 안 숫자는 순위, 겹치는 원은 옆으로 비켜 선으로 이음';
  $('#rtitle').innerHTML=esc(it.id)+' 주 생산지 상위 '+S.n+'곳';
  $('#rcap').innerHTML='단위 : '+vu(it)+' · '+S.y+'년 '+MN[S.m]+' 기준 · 막대는 1위 대비 · 오른쪽 아래는 전국 대비 비중과 전년 대비';
  const prev=yi>0?Object.fromEntries(rk(it,Y[yi-1]).map(r=>[r.i,r.v])):{};
  const mx=top.length?top[0].v:1;
  let li=top.map((r,x)=>'<li data-i="'+r.i+'" class="'+(S.sel===r.i?'sel':'')+'"><span class="no" style="background:'+rankCol(it,x,S.n)+';'+(x>=S.n*.5&&S.n>2?'color:#17211B':'')+'">'+(x+1)+'</span>'
    +'<span class="nm">'+esc(U[r.i].name)+'<small>'+esc(U[r.i].sido)+'</small></span><span class="v">'+vf(it,r.v)+'</span>'
    +'<span class="bar"><i style="width:'+(r.v/mx*100)+'%;background:'+rankCol(it,x,S.n)+'"></i></span><span class="sh">'+fmt(r.v/nat*100,1)+'% · '+(yi>0?ptxt(pctx(r.v,prev[r.i])):'-')+'</span></li>').join('');
  if(R.length>S.n){const rs=R.slice(S.n).reduce((a,b)=>a+b.v,0);li+='<li class="rest"><span></span><span class="nm">그 밖 '+fmt(R.length-S.n,0)+'곳</span><span class="v">'+vf(it,rs)+'</span><span></span><span class="sh">'+fmt(rs/nat*100,1)+'%</span></li>'}
  if(!R.length)li='<li class="rest"><span></span><span class="nm">'+S.y+'년 시군구 생산 기록 없음</span></li>';
  $('#rank').innerHTML=li;
  drawDet();saveHash();
}
// 변동 보기 : 첫 조사 연도 → 고른 연도, 늘어난 곳은 품목색 · 줄어든 곳은 청색
function chgRows(it){
  const a=Object.fromEntries(rk(it,Y[0]).map(r=>[r.i,r.v])),b=Object.fromEntries(rk(it,S.y).map(r=>[r.i,r.v]));
  const ids=new Set([...Object.keys(a),...Object.keys(b)].map(Number));
  return [...ids].map(i=>({i,a:a[i]||0,b:b[i]||0,d:(b[i]||0)-(a[i]||0)})).filter(r=>r.d!=0)}
function drawChg(it,c){
  const rows=chgRows(it),mx=Math.max(1,...rows.map(r=>Math.abs(r.d))),D_={};rows.forEach(r=>D_[r.i]=r);
  P.forEach(p=>{const i=+p.dataset.i;p.classList.remove('o','t','sel');p.style.removeProperty('--o');
    const r=D_[i];if(r){const t=Math.pow(Math.abs(r.d)/mx,.5);p.classList.add('o');
      p.style.setProperty('--o',r.d>0?mix(mix(c,'#FFFFFF',.85),mix(c,'#000000',.1),t):mix('#E3ECF5','#1F5C99',t));if(t>.25)p.classList.add('t')}
    if(S.sel===i)p.classList.add('sel');});
  $('#mk').innerHTML='';
  const st=[.15,.4,.7,1];
  $('#leg').innerHTML='<b>'+Y[0]+'→'+S.y+' '+MN[S.m]+' 변동</b><div class="r">'+st.slice().reverse().map(t=>'<i style="background:'+mix('#E3ECF5','#1F5C99',Math.sqrt(t))+'"></i>').join('')
    +st.map(t=>'<i style="background:'+mix(mix(c,'#FFFFFF',.85),mix(c,'#000000',.1),Math.sqrt(t))+'"></i>').join('')+'</div><div class="r2"><span>감소</span><span>증가</span></div>';
  $('#note').innerHTML=S.y==Y[0]?'조사 연도를 '+Y[Y.length-1]+'년으로 바꾸면 '+Y[0]+'년 대비 변동이 나옴':'색이 진할수록 변동량이 큼 · 생산이 새로 생기거나 없어진 곳도 포함';
  const up=rows.filter(r=>r.d>0).sort((x,y)=>y.d-x.d).slice(0,S.n),dn=rows.filter(r=>r.d<0).sort((x,y)=>x.d-y.d).slice(0,S.n);
  $('#rtitle').innerHTML=esc(it.id)+' 생산지 변동 상위 '+S.n+'곳';
  $('#rcap').innerHTML='단위 : '+vu(it)+' · '+Y[0]+'년 → '+S.y+'년 '+MN[S.m]+' 증감 · 오른쪽 아래는 '+Y[0]+'년 값과 증감률';
  const row=(r,x,cl)=>'<li data-i="'+r.i+'" class="'+(S.sel===r.i?'sel':'')+'"><span class="no" style="background:'+cl+'">'+(x+1)+'</span><span class="nm">'+esc(U[r.i].name)+'<small>'+esc(U[r.i].sido)+'</small></span>'
    +'<span class="v">'+(r.d>0?'+':'-')+vf(it,Math.abs(r.d))+'</span><span class="bar"><i style="width:'+(Math.abs(r.d)/mx*100)+'%;background:'+cl+'"></i></span><span class="sh">'+vf(it,r.a)+' → '+vf(it,r.b)+' · '+(r.a?ptxt(pctx(r.b,r.a)):'새로 생산')+'</span></li>';
  $('#rank').innerHTML=(S.y==Y[0]?'<li class="rest"><span></span><span class="nm">비교할 연도를 고르면 나옴</span></li>':
    '<li class="rest hd2"><span></span><span class="nm">늘어난 곳</span></li>'+(up.map((r,x)=>row(r,x,mix(c,'#000000',.1))).join('')||'<li class="rest"><span></span><span class="nm">없음</span></li>')
    +'<li class="rest hd2"><span></span><span class="nm">줄어든 곳</span></li>'+(dn.map((r,x)=>row(r,x,'#1F5C99')).join('')||'<li class="rest"><span></span><span class="nm">없음</span></li>'));
}
function saveHash(){try{history.replaceState(null,'','#i='+encodeURIComponent(S.item)+'&y='+S.y+'&n='+S.n+'&m='+S.m+'&v='+S.v+(S.sel!=null?'&r='+S.sel:''))}catch(e){}}
// 지역 상세 : 이 품목 3년 추이 + 지역 전체 품목(생산액 순)
function regionItems(i,y){const out=[];D.items.forEach(o=>{const rr=(o.vals[String(y)]||[]);const r=rr.find(r=>r[0]==i);if(r&&(r[1]>0||r[2]>0)){
  const R=rk(o,y);out.push({o,q:r[1],w:r[2],rank:R.findIndex(x=>x.i==i)+1,of:R.length})}});out.sort((a,b)=>b.w-a.w||b.q-a.q);return out}
function drawDet(){
  const it=IT[S.item],c=col(it);
  const opts='<select class="rsel" id="rsel" aria-label="지역 고르기"><option value="">지역 고르기 (229개 시군구)</option>'
    +[...U.keys()].sort((a,b)=>(U[a].sido+U[a].name).localeCompare(U[b].sido+U[b].name,'ko')).map(i=>'<option value="'+i+'"'+(S.sel===i?' selected':'')+'>'+esc(U[i].sido+' '+U[i].name)+'</option>').join('')+'</select>';
  if(S.sel==null){$('#det').innerHTML=opts+'<div class="emp">지도 · 순위표에서 지역을 누르거나 위에서 지역을 고르면 이 품목의 연도별 생산량과 그 지역의 전체 임산물 생산이 나옴</div>';return}
  const i=S.sel,yi=Y.indexOf(S.y),R=rk(it,S.y),pos=R.findIndex(r=>r.i==i),me=pos>=0?R[pos]:null;
  const ys=Y.map(y=>{const r=rk(it,y).find(r=>r.i==i);return r?r.v:0}),mx=Math.max(...ys)||1;
  let h=opts+'<div class="rg">'+esc(U[i].name)+'<small>'+esc(U[i].sido)+'</small></div>'
    +'<dl><dt>'+S.y+'년 '+esc(it.id)+' 생산량</dt><dd>'+(me?fmt(dv(it,me.q),nd(it))+' '+it.du:'생산 없음')+'</dd>'
    +'<dt>생산액</dt><dd>'+(me&&me.w?fmt(me.w,me.w<10?1:0)+'백만 원':'-')+'</dd>'
    +'<dt>전국 순위 ('+MN[S.m]+')</dt><dd>'+(pos>=0?(pos+1)+'위 / '+R.length+'곳':'-')+'</dd>'
    +'<dt>전국 대비 비중</dt><dd>'+(me&&natv(it,yi)?fmt(me.v/natv(it,yi)*100,1)+'%':'-')+'</dd></dl>'
    +'<div class="yb" style="--n:'+Y.length+'">'+ys.map((q,k)=>'<div class="'+(Y[k]==S.y?'last':'')+'"><em>'+(q?vf(it,q):'-')+'</em><i style="height:'+Math.max(2,q/mx*62)+'px"></i></div>').join('')+'</div>'
    +'<div class="yl" style="--n:'+Y.length+'">'+Y.map(y=>'<span>'+y+'년</span>').join('')+'</div>';
  const all=regionItems(i,S.y),wsum=all.reduce((a,b)=>a+b.w,0),SH=8;
  h+='<h4>'+S.y+'년 '+esc(U[i].name)+' 임산물 생산 · '+all.length+'개 품목 · 생산액 '+fmt(wsum,0)+'백만 원</h4>'
    +'<table class="rt"><thead><tr><th>품목</th><th>생산액<br>(백만 원)</th><th>비중<br>(%)</th><th>전국<br>순위</th></tr></thead><tbody>'
    +all.map((x,k)=>'<tr class="'+(k>=SH?'ex':'')+(x.o.id==S.item?' cur':'')+'" data-i="'+esc(x.o.id)+'"><td><i style="background:'+col(x.o)+'"></i>'+esc(x.o.id)+'</td><td>'+fmt(x.w,x.w<10?1:0)+'</td><td>'+(wsum?fmt(x.w/wsum*100,1):'-')+'</td><td>'
      +(x.rank?'<b class="'+(x.rank<=10?'t10':'')+'">'+x.rank+'</b>':'-')+'</td></tr>').join('')+'</tbody></table>'
    +(all.length>SH?'<button class="mbtn2" id="rmore">'+(S.rall?'접기':'전체 '+all.length+'개 품목 보기')+'</button>':'')
    +'<button class="csv" id="csv2">이 지역 표 내려받기 (CSV)</button>';
  $('#det').innerHTML=h;
  $('#detc').classList.toggle('all',!!S.rall);
}
// CSV 내려받기 (엑셀에서 한글이 깨지지 않게 BOM 포함)
function dl(name,rows){const t='﻿'+rows.map(r=>r.map(v=>{v=String(v==null?'':v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}).join(',')).join('\r\n');
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([t],{type:'text/csv;charset=utf-8'}));a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500)}
function csvItem(){const it=IT[S.item],yi=Y.indexOf(S.y),R=rk(it,S.y),prev=yi>0?Object.fromEntries(rk(it,Y[yi-1]).map(r=>[r.i,r])):{};
  const rows=[['순위('+MN[S.m]+' 기준)','시도','시군구','생산량('+it.unit+')','생산액(백만 원)','전국 대비 비중(%)',(yi>0?Y[yi-1]+'년 생산량('+it.unit+')':'전년 생산량'),'전년 대비(%)']];
  R.forEach((r,x)=>{const p=prev[r.i];rows.push([x+1,U[r.i].sido,U[r.i].name,r.q,r.w,(r.v/natv(it,yi)*100).toFixed(1),p?p.q:'',p&&p.q?((r.q-p.q)/p.q*100).toFixed(1):''])});
  rows.push([]);rows.push(['전국 합계(국유림 포함)','','',it.nat[yi],it.natw[yi]]);rows.push(['자료 : 산림청 임산물생산조사 '+S.y+'년']);
  dl('임산물생산지도_'+it.id+'_'+S.y+'.csv',rows)}
function csvRegion(){const i=S.sel;if(i==null)return;const all=regionItems(i,S.y);
  const rows=[['품목','분류','생산량','단위','생산액(백만 원)','전국 순위','생산 시군구 수']];
  all.forEach(x=>rows.push([x.o.id,x.o.cat,x.q,x.o.unit,x.w,x.rank||'',x.of]));
  rows.push([]);rows.push(['자료 : 산림청 임산물생산조사 '+S.y+'년 · '+U[i].sido+' '+U[i].name]);
  dl('임산물생산지도_'+U[i].sido+U[i].name+'_'+S.y+'.csv',rows)}
// ── 조작 ──
function setItem(id){if(!IT[id])return;S.item=id;drawList();draw()}
document.addEventListener('click',e=>{
  if(e.target.closest('#csv1')){csvItem();return}
  if(e.target.closest('#csv2')){csvRegion();return}
  if(e.target.closest('#rmore')){S.rall=!S.rall;drawDet();return}
  const t=e.target.closest('[data-c],[data-y],[data-n],[data-m],[data-v],.it,.chips button,.rt tr[data-i],.rk li[data-i],#map .u,#map .mk');if(!t)return;
  if(t.dataset.c){S.cat=t.dataset.c;drawCats();drawList();return}
  if(t.dataset.y){S.y=+t.dataset.y;drawList();draw();return}
  if(t.dataset.n){S.n=+t.dataset.n;draw();return}
  if(t.dataset.m){S.m=t.dataset.m;draw();return}
  if(t.dataset.v){S.v=t.dataset.v;draw();return}
  if(t.classList.contains('it')||t.closest('.chips')||t.closest('.rt')){setItem(t.dataset.i);return}
  const i=+t.dataset.i;S.sel=(S.sel===i?null:i);draw();
});
document.addEventListener('change',e=>{if(e.target.id=='rest'){S.rest=e.target.checked;draw()}if(e.target.id=='msel')setItem(e.target.value)
  if(e.target.id=='rsel'){S.sel=e.target.value===''?null:+e.target.value;draw()}});
$('#q').addEventListener('input',drawList);
const tip=$('#tip');
svg.addEventListener('mousemove',e=>{const p=e.target.closest('.u,.mk');if(!p){tip.style.display='none';return}
  const i=+p.dataset.i,it=IT[S.item],R=rk(it,S.y),pos=R.findIndex(r=>r.i==i);
  let tx='<b>'+esc(label(i))+'</b><br>';
  if(S.v=='chg'){const r=chgRows(it).find(r=>r.i==i);tx+=r?esc(it.id)+' '+Y[0]+'년 '+vf(it,r.a)+' → '+S.y+'년 '+vf(it,r.b)+' '+vu(it):esc(it.id)+' 변동 없음'}
  else tx+=pos>=0?esc(it.id)+' '+vf(it,R[pos].v)+' '+vu(it)+' · '+(pos+1)+'위':esc(it.id)+' 생산 없음';
  tip.innerHTML=tx;tip.style.display='block';tip.style.left=Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8)+'px';tip.style.top=(e.clientY+14)+'px'});
svg.addEventListener('mouseleave',()=>tip.style.display='none');
drawCats();drawList();draw();addEventListener('resize',()=>{clearTimeout(window._rt);window._rt=setTimeout(draw,200)});
</script></body></html>"""


def main():
    geo, ys, items, errs = build_data()
    errs += verify(items, ys)
    if errs:
        print('검증 실패 - 생산지도를 쓰지 않음')
        for e in errs[:30]:
            print('  ', e)
        sys.exit(1)
    data = {'years': ys, 'items': items}
    doc = (HTML.replace('__GEO__', json.dumps(geo, ensure_ascii=False, separators=(',', ':')))
           .replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
           .replace('__CATCOL__', json.dumps(CAT_COL, ensure_ascii=False))
           .replace('__CATICON__', json.dumps(CAT_ICON, ensure_ascii=False))
           .replace('__NITEMS__', str(len(items)))
           .replace('__YEARS__', '%d~%d' % (ys[0], ys[-1]))
           .replace('__BUILT__', datetime.now(KST).strftime('%Y.%m.%d %H:%M')))
    doc = doc.replace('—', '-').replace('–', '-')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(doc)
    print('작성 %s · 품목 %d · 연도 %s · %d KB' % (OUT, len(items), ys, len(doc.encode()) // 1024))


if __name__ == '__main__':
    main()
