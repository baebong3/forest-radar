# -*- coding: utf-8 -*-
"""
data/radar.db + data/production.csv → docs/index.html (GitHub Pages 공개 페이지)

디자인 : 서던 하우스(딥그린 #1E4A4A · 오렌지 #F08900), Pretendard 서브셋 자체 호스팅
  - 탭 : 종합 · 밤 · 호두 · 대추 · 표고버섯 · 떫은감 (라디오 토글, 자바스크립트 없이 동작)
  - 품목 탭 : 헤드라인 → KPI → 최근 13개월 수입 · 수출량 → 연도별 같은 기간 누계 → 연간 생산량
             → 월별 상세표 → 최근 뉴스 → HS 코드 주석
  - 수입 = 딥그린, 수출 = 오렌지 (모든 차트 공통)
  - 산출 전 검증 게이트 : 빈 수치 라벨 · 콤마 누락 · 줄표 · None/nan 이 있으면 페이지를 쓰지 않고 실패

사용법
  python radar/build.py
  python radar/build.py --db 다른.db --out 다른.html
"""
import argparse, csv, html, json, os, re, sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, ROOT, DB, db, fmt, pct, fmt_pct, rnd
from items import ITEMS, POLICY, score
from charts import dual, hbars, legend, esc, lines

OUT = os.path.join(ROOT, 'docs', 'index.html')
PROD = os.path.join(ROOT, 'data', 'production.csv')
IMP, EXP = '#1F3D2B', '#B8742A'          # 수입 = 숲 초록, 수출 = 밤색 앰버
IMP_L, EXP_L = '#C3D1BE', '#EBD6BC'
PRD, PRD_L = '#5E7F4F', '#CFDBC8'
NEWS_DAYS = 30
SHOW_NEWS, SHOW_ROWS = 10, 12

CSS = """<style>
@font-face{font-family:'PretendardSub';font-weight:400;font-display:swap;src:url(assets/fonts/pretendard-sub-Regular.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:600;font-display:swap;src:url(assets/fonts/pretendard-sub-SemiBold.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:800;font-display:swap;src:url(assets/fonts/pretendard-sub-ExtraBold.woff2) format('woff2')}
:root{--green:#1F3D2B;--green-d:#142A1D;--moss:#5E7F4F;--sage:#A9BBA2;--org:#B8742A;--org-d:#8C5518;
  --ink:#17211B;--sub:#4B5A50;--muted:#8A968D;--rule:#E4E9E3;--rule2:#F0F3EE;--bg:#FFFFFF;--card:#fff;--tint:#EEF3EC;--otint:#F8EEE2}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.55;letter-spacing:-.1px;
  font-family:'PretendardSub','Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif}
a{color:inherit;text-decoration:none}
.mast{background:#fff;border-bottom:1px solid var(--rule)}
.mast .in{max-width:1240px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.logos{display:flex;align-items:center;gap:12px}
.lg-sp{height:24px;width:auto;display:block}
.lg-kf{height:32px;width:auto;display:block}
.logos .x{font-size:14px;color:var(--muted);font-weight:600}
.wm b{color:var(--org)}
.vr{width:1px;height:28px;background:var(--rule)}
.team{display:flex;flex-direction:column;line-height:1.25}
.team .t1{font-size:12px;font-weight:600;color:var(--muted)}
.team .t2{font-size:17px;font-weight:800;letter-spacing:-.4px}
.upd{margin-left:auto;text-align:right;font-size:12px;color:var(--muted);line-height:1.45}
.upd b{color:var(--ink);font-weight:600}
.ribbon{display:flex;height:4px}.ribbon i{flex:6;background:var(--green)}.ribbon i:nth-child(2){flex:2;background:var(--moss)}.ribbon i:nth-child(3){flex:1;background:var(--org)}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px}
.tg{position:absolute;opacity:0;pointer-events:none}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:22px 0 22px}
.tabs label{cursor:pointer;border:1px solid var(--rule);background:#fff;border-radius:999px;padding:8px 18px;font-weight:800;font-size:14px;color:var(--sub)}
.tabs label:hover{border-color:var(--green)}
.pane{display:none}
%(TOGGLE)s
.hero{padding:2px 0 18px 18px;border-left:5px solid var(--green);margin:0 0 22px}
.eyebrow{font-size:11.5px;font-weight:800;letter-spacing:1.4px;color:var(--moss)}
.hero h1{font-size:30px;line-height:1.3;font-weight:800;letter-spacing:-1px;margin:6px 0 10px;word-break:keep-all}
.dek{list-style:none;margin:0;padding:0;font-size:14px;color:var(--sub)}
.dek li{padding-left:14px;position:relative;margin:3px 0;word-break:keep-all}
.dek li:before{content:'';position:absolute;left:2px;top:.72em;width:5px;height:5px;background:var(--org);border-radius:50%%}
.dek a{color:var(--ink);font-weight:600;border-bottom:1px solid var(--rule)}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);background:#fff;border-top:3px solid var(--green);border-bottom:1px solid var(--rule);margin-bottom:22px}
.kpi{padding:14px 16px;border-left:1px solid var(--rule2);min-width:0}
.kpi:first-child{border-left:0}
.kv{font-size:27px;font-weight:800;letter-spacing:-.8px;line-height:1.15;font-variant-numeric:tabular-nums;white-space:nowrap}
.kv small{font-size:13px;font-weight:600;color:var(--muted);margin-left:2px;letter-spacing:0}
.kv.i{color:var(--green)}.kv.e{color:var(--org-d)}
.kl{font-size:12.5px;font-weight:700;margin-top:5px}
.ks{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.ks .up{color:#C0392B;font-weight:700}.ks .dn{color:#2E6DA4;font-weight:700}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start;margin-bottom:18px}
.grid>*{min-width:0}
.card{background:#fff;border:1px solid var(--rule);border-top:2px solid var(--green);padding:18px 22px 22px}
.span{grid-column:1/-1}
.sec{font-size:11px;font-weight:800;letter-spacing:1.6px;color:var(--moss)}
.sec:before{content:'◆';color:var(--org);font-size:8px;margin-right:6px;vertical-align:2px}
.h2{font-size:19px;font-weight:800;letter-spacing:-.6px;margin:4px 0 2px;word-break:keep-all;color:var(--ink)}
.cap{font-size:12px;color:var(--muted);margin-bottom:10px;word-break:keep-all}
.lg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--sub);margin:0 0 6px}
.lg span{white-space:nowrap}
.lg i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-right:6px;vertical-align:3px}
svg{width:100%%;height:auto;display:block;overflow:visible}
svg text{font-family:'PretendardSub','Pretendard','Malgun Gothic',sans-serif}
svg .v{fill:#5B6A60;font-weight:600;text-anchor:middle;font-variant-numeric:tabular-nums}
svg .v.hi{font-weight:800}
svg .x{fill:var(--sub);text-anchor:middle;font-weight:600}
svg .x2{fill:var(--muted);text-anchor:middle}
svg .yl{fill:var(--sub);font-size:12px;text-anchor:end;font-weight:600}
svg .vh{fill:#5B6A60;font-size:12px;font-weight:600;font-variant-numeric:tabular-nums}
svg .vh.hi{font-weight:800}
svg .trk{fill:#F2F5F0}
svg .base{stroke:#9FAEA3;stroke-width:1}
svg .tn{font-size:13px;font-weight:800}
svg .ts{font-size:11px;font-weight:700;text-anchor:end;font-variant-numeric:tabular-nums}
svg .tv{font-size:17px;font-weight:800;font-variant-numeric:tabular-nums}
svg .grid{stroke:#DCE3DA;stroke-width:1;stroke-dasharray:2 3}
svg .xt{stroke:#BFC7C4}
svg .tk{fill:var(--muted);text-anchor:end;font-variant-numeric:tabular-nums}
svg .ve{font-weight:800;text-anchor:start;font-variant-numeric:tabular-nums}
svg .vs{font-weight:700;text-anchor:end;font-variant-numeric:tabular-nums}
.ch-m{display:none}
.empty{background:var(--tint);color:var(--sub);font-size:13px;padding:14px 16px;border-radius:4px;word-break:keep-all}
.empty b{color:var(--ink)}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.t{width:100%%;border-collapse:collapse;font-size:13px}
.t th{font-size:12px;font-weight:800;text-align:center;padding:8px 6px;border-bottom:2px solid var(--ink);white-space:nowrap;vertical-align:bottom}
.t th.l,.t td.l{text-align:left}
.t td{padding:8px 6px;border-bottom:1px solid var(--rule2);white-space:nowrap}
.t td.n{text-align:center;font-variant-numeric:tabular-nums}
.t td.n span{display:inline-block;text-align:right}
.t td .up{color:#C0392B}.t td .dn{color:#2E6DA4}
.t tbody tr:last-child td{border-bottom:1px solid var(--ink)}
.t tr.ex{display:none}
.more{position:absolute;opacity:0;pointer-events:none}
.more:checked~.tw .t tr.ex,.more:checked~ul li.ex{display:flex}
.more:checked~.tw .t tr.ex{display:table-row}
.mbtn{display:block;margin-top:12px;text-align:center;font-size:13px;font-weight:700;color:var(--green);border:1px solid var(--green);border-radius:999px;padding:8px;cursor:pointer;background:#fff}
.mbtn .c{display:none}.more:checked~.mbtn .o{display:none}.more:checked~.mbtn .c{display:inline}
.nl{list-style:none;margin:0;padding:0}
.nl li{display:flex;gap:10px;align-items:baseline;padding:10px 0;border-bottom:1px solid var(--rule2)}
.nl li.ex{display:none}
.nl .d{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.nl .tt{font-size:14.5px;font-weight:700;line-height:1.45;word-break:keep-all}
.nl .tt a:hover{color:var(--green);text-decoration:underline}
.chip{display:inline-block;font-size:11px;font-weight:700;border-radius:3px;padding:1px 7px;background:var(--tint);color:var(--green);white-space:nowrap;margin-right:6px}
.chip.o{background:var(--otint);color:var(--org-d)}
.kgs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
.kh{font-size:12px;font-weight:800;color:var(--moss);letter-spacing:.6px;border-bottom:2px solid var(--green);padding-bottom:6px;margin-bottom:4px}
.kl2{list-style:none;margin:0;padding:0}
.kl2 li{padding:9px 0;border-bottom:1px solid var(--rule2);word-break:keep-all}
.kl2 li b{display:block;font-size:14px;line-height:1.45;color:var(--ink)}
.kl2 li span{display:block;font-size:12.5px;color:var(--sub);margin-top:3px;line-height:1.5}
.kc .cap a,.foot a{color:var(--green);font-weight:700;border-bottom:1px solid var(--rule)}
.t td.w{white-space:normal;word-break:keep-all;min-width:180px;line-height:1.45}
.t.kt td{vertical-align:top}
.hsn{font-size:12px;color:var(--muted);margin-top:10px;word-break:keep-all}
.foot{margin:30px 0 0;padding:18px 0 40px;border-top:1px solid var(--rule);font-size:12px;color:var(--muted);line-height:1.7}
.foot b{color:var(--sub)}
@media(max-width:980px){.grid{grid-template-columns:1fr}.kgs{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(3,1fr)}
  .kpi:nth-child(4){border-left:0}.kpi:nth-child(n+4){border-top:1px solid var(--rule2)}}
@media(max-width:640px){.hero h1{font-size:22px}.kv{font-size:23px}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .kpi{border-left:0!important;border-top:1px solid var(--rule2)}.kpi:nth-child(-n+2){border-top:0}
  .kpi:nth-child(even){border-left:1px solid var(--rule2)!important}
  .upd{margin-left:0;text-align:left;width:100%%}.vr{display:none}.lg-sp{height:20px}.lg-kf{height:27px}
  .card{padding:14px}.tabs label{padding:7px 13px;font-size:13.5px}
  .ch-d{display:none}.ch-m{display:block}
  table.t{font-size:12px}.t th{font-size:11px}.t th,.t td{padding-left:4px;padding-right:4px}}
@media print{.pane{display:block!important}.tabs,.mbtn{display:none}.t tr.ex{display:table-row}}
</style>"""


# ── 자료 ───────────────────────────────────────────────────
def ym_add(ym, k):
    y, m = map(int, ym.split('-'))
    t = y * 12 + (m - 1) + k
    return '%04d-%02d' % (t // 12, t % 12 + 1)


def load_trade(con):
    T = defaultdict(lambda: defaultdict(lambda: {'exp_kg': 0.0, 'exp_usd': 0.0, 'imp_kg': 0.0, 'imp_usd': 0.0}))
    forms = defaultdict(dict)
    for item, hs, ym, sk, form, ek, eu, ik, iu in con.execute(
            'SELECT item,hs,ym,stat_kor,form,exp_kg,exp_usd,imp_kg,imp_usd FROM trade'):
        d = T[item][ym]
        d['exp_kg'] += ek or 0; d['exp_usd'] += eu or 0; d['imp_kg'] += ik or 0; d['imp_usd'] += iu or 0
        forms[item][hs] = (sk or '', form or '')
    return T, forms


def load_prod(path=PROD):
    P = defaultdict(dict)
    if os.path.exists(path):
        for r in csv.DictReader(open(path, encoding='utf-8-sig')):
            try:
                P[r['item'].strip()][int(r['year'])] = float(str(r['tonnes']).replace(',', ''))
            except (KeyError, ValueError, TypeError):
                continue
    return P


def load_news(con, key, today, days=NEWS_DAYS):
    since = (today - timedelta(days=days)).strftime('%Y-%m-%d')
    rows = con.execute('SELECT title,url,date,category,summary FROM news WHERE item=? AND date>=? '
                       'ORDER BY date DESC, collected_at DESC', (key, since)).fetchall()
    seen, out = set(), []
    for t, u, d, c, s in rows:
        k = re.sub(r'[^0-9A-Za-z가-힣]', '', t)[:40]
        if k in seen:
            continue
        seen.add(k)
        out.append({'title': t, 'url': u, 'date': d, 'cat': c or '기타', 'summary': s or '', 'item': key})
    return out


def load_krei(con):
    """품목별 최신 임업관측 월보 (소제목 · 근거 문장)"""
    out = {}
    try:
        rows = con.execute('SELECT item,ym,title,pdf,view,heads FROM krei ORDER BY ym DESC').fetchall()
    except Exception:
        return out
    for item, ym, title, pdf, view, heads in rows:
        hs = json.loads(heads or '[]')
        if item in out or not hs:
            continue
        out[item] = {'ym': ym, 'title': title, 'pdf': pdf, 'view': view, 'heads': hs}
    return out


KW = re.compile(r'가격|수입|수출|반입|출하|시세')


def ts_family(title, unit, sub):
    """월보 표 제목 → (묶음 키, 표시 제목, 단위, 하위구분) · 표가 아닌 문장이 잡힌 경우 None"""
    t = re.sub(r'[❙\uf06c\uf06e•■]', '', title or '').strip()
    t = re.sub(r'\s+', ' ', t)
    if (not KW.search(t) or len(t) > 40 or '%' in t or re.search(r'(다|음|함|됨|임)\s*\.?\s*$', t)
            or re.match(r'^(연도|구분|\d)', t) or re.search(r'\d{1,3},\d{3}', t) or '주1' in t or '일일' in t):
        return None
    sub = (sub or '').strip()
    if len(sub) > 8 or re.search(r'[\d,•.%]', sub) or sub.startswith('평년'):
        return None
    unit = (unit or '').strip()
    if ',' in unit:                                   # 가격 · 물량이 한 표에 섞인 경우
        if sub == '중량':
            unit, sub, t = '톤', '', t + ' (중량)'
        elif sub == '금액':
            unit, sub, t = '천 달러', '', t + ' (금액)'
        else:
            return None
    key = re.sub(r'\s+', '', t)
    key = re.sub(r'\((등급\s*:\s*)?상(품)?(기준)?\)', '', key)
    for w in ('월별', '동향', '현황', '추이', '월평균', '실적', '의'):
        key = key.replace(w, '')
    key = key.replace('소비자가격', '소비지가격')
    return key, re.sub(r'\s*(실적|동향)$', '', t.replace('월별 ', '')).strip(), unit, sub


def load_krei_ts(con):
    """item → [{title, unit, subs:{sub:{ym:v}}}] - 제목 표현이 달라도 같은 표는 한 시계열로 묶고,
    최근 18개월 안에 값이 있고 12개월 이상 쌓인 표만 사용"""
    out = defaultdict(dict)
    try:
        rows = con.execute('SELECT item,title,unit,sub,ym,value,src FROM krei_ts ORDER BY src').fetchall()
    except Exception:
        return {}
    for item, title, unit, sub, ym, v, src in rows:
        f = ts_family(title, unit, sub)
        if not f:
            continue
        key, disp, unit2, sub2 = f
        d = out[item].setdefault(key, {'title': disp, 'unit': unit2, 'src': src, 'subs': defaultdict(dict)})
        if src >= d['src']:
            d['title'], d['unit'], d['src'] = disp, unit2 or d['unit'], src
        d['subs'][sub2][ym] = v
    res = {}
    for item, tabs in out.items():
        allym = [ym for t in tabs.values() for sd in t['subs'].values() for ym in sd]
        if not allym:
            continue
        last = max(allym)
        keep = []
        for t in tabs.values():
            n = sum(len(sd) for sd in t['subs'].values())
            tl = max(ym for sd in t['subs'].values() for ym in sd)
            if tl >= ym_add(last, -18) and n >= 12:
                # 너무 드문 하위구분(3개월 미만)은 뺌
                # 3개월 미만이거나 1년 넘게 끊긴 하위구분(옛 서식의 잔재)은 뺌
                t['subs'] = {k: v for k, v in t['subs'].items() if len(v) >= 3 and max(v) >= ym_add(tl, -12)}
                if t['subs']:
                    keep.append(t)
        keep.sort(key=lambda t: (0 if '가격' in t['title'] else 1 if '수입' in t['title'] else 2 if '수출' in t['title'] else 3, t['title']))
        res[item] = keep
    return res


TS_COL = ['#1F3D2B', '#B8742A', '#6E8F5E', '#A9BBA2']
TS_COL5 = ['#1F3D2B', '#B8742A', '#6E8F5E', '#8C5518', '#A9BBA2']


def ts_cards(item_key, KT):
    tabs = KT.get(item_key) or []
    if not tabs:
        return ''
    o = []
    for t in tabs:
        subs = sorted(t['subs'].items(), key=lambda kv: -sum(kv[1].values()))[:4]
        allym = sorted({ym for _, sd in subs for ym in sd})
        last = allym[-1]
        first = max(allym[0], ym_add(last, -95))
        xs, cur = [], first
        while cur <= last:
            xs.append(cur); cur = ym_add(cur, 1)
        vals = [v for _, sd in subs for v in sd.values()]
        nd = 0 if all(float(v).is_integer() for v in vals) else 1
        series = [{'name': sub or t['title'], 'color': TS_COL[i], 'values': [sd.get(x) for x in xs]} for i, (sub, sd) in enumerate(subs)]
        lg = legend(series) if len(series) > 1 else ''
        chart = ('<div class="ch-d">%s</div><div class="ch-m">%s</div>'
                 % (lines(xs, series, nd), lines(xs, series, nd, w=360, h=230, fs=10.5)))
        # 최근 3개 연도 × 월 표
        yrs = sorted({int(x[:4]) for x in allym})[-3:][::-1]
        body = []
        cells = []
        for sub, sd in subs:
            for y in yrs:
                row = [sd.get('%04d-%02d' % (y, m)) for m in range(1, 13)]
                if not any(v is not None for v in row):
                    continue
                cells.append((sub, y, [fmt(v, nd) if v is not None else '-' for v in row]))
        ws = [span_w([c[2][m] for c in cells]) for m in range(12)]
        for sub, y, row in cells:
            body.append('<tr><td class="l">%s</td>%s</tr>' % (esc(('%s ' % sub if sub else '') + '%d년' % y),
                                                             ''.join(numtd(v, ws[m]) for m, v in enumerate(row))))
        tb = ('<div class="tw"><table class="t"><thead><tr><th class="l">구분</th>%s</tr></thead><tbody>%s</tbody></table></div>'
              % (''.join('<th>%d월</th>' % m for m in range(1, 13)), ''.join(body)))
        o.append('<div class="card span"><div class="sec">KREI MONTHLY</div><div class="h2">%s</div>'
                 '<div class="cap">단위 : %s · %s ~ %s · 농경연 임업관측 월보 표에서 추출(같은 달은 최신 호 값 사용, 평년 행 제외)</div>'
                 '%s%s%s</div>' % (esc(t['title']), esc(t['unit'] or '-'), xs[0].replace('-', '.'),
                                    last.replace('-', '.'), lg, chart, tb))
    return '<div class="grid">%s</div>' % ''.join(o)


def ko_ym(ym):
    return '%s년 %d월호' % (ym[:4], int(ym[5:]))


def krei_card(item_key, K):
    k = K.get(item_key)
    if not k:
        return ''
    groups = []
    for sec in ('생산·출하', '수출입', '가격'):
        hs = [h for h in k['heads'] if h['sec'] == sec]
        if not hs:
            continue
        li = ''.join('<li><b>%s</b>%s</li>' % (esc(h['head']), ('<span>%s</span>' % esc(h['detail'])) if h['detail'] else '')
                     for h in hs)
        groups.append('<div class="kg"><div class="kh">%s</div><ul class="kl2">%s</ul></div>' % (sec, li))
    return ('<div class="grid"><div class="card span kc"><div class="sec">KREI OUTLOOK</div>'
            '<div class="h2">농경연 임업관측 %s</div><div class="cap">한국농촌경제연구원 임업관측 월보의 소제목(판단)과 첫 문장(근거) · '
            '<a href="%s" target="_blank" rel="noopener">원문 PDF</a> · <a href="%s" target="_blank" rel="noopener">월보 페이지</a></div>'
            '<div class="kgs">%s</div></div></div>' % (ko_ym(k['ym']), esc(k['pdf']), esc(k['view']), ''.join(groups)))


def krei_overview(K):
    rows = []
    for it in ITEMS:
        k = K.get(it['key'])
        if not k:
            continue
        cells = []
        for sec in ('생산·출하', '수출입', '가격'):
            hs = [h['head'] for h in k['heads'] if h['sec'] == sec]
            fc = [h for h in hs if '전망' in h or '듯' in h]
            cells.append(esc((fc or hs or ['-'])[0]))
        rows.append('<tr><td class="l"><b>%s</b></td><td class="l"><a href="%s" target="_blank" rel="noopener">%s</a></td>%s</tr>'
                    % (it['label'], esc(k['pdf']), ko_ym(k['ym']), ''.join('<td class="l w">%s</td>' % c for c in cells)))
    if not rows:
        return ''
    return ('<div class="grid"><div class="card span"><div class="sec">KREI OUTLOOK</div><div class="h2">농경연 임업관측 최신 전망</div>'
            '<div class="cap">품목별 최신 월보에서 절마다 전망 문장 우선 1개</div><div class="tw"><table class="t kt"><thead><tr>'
            '<th class="l">품목</th><th class="l">월보</th><th class="l">생산 · 출하</th><th class="l">수출입</th><th class="l">가격</th>'
            '</tr></thead><tbody>%s</tbody></table></div></div></div>' % ''.join(rows))



# ── 임산물생산조사 (연도 · 시도 · 시군구) ─────────────────────────────
TILE = {'인천': (0, 0), '서울': (1, 0), '경기': (2, 0), '강원': (3, 0),
        '충남': (0, 1), '세종': (1, 1), '충북': (2, 1), '경북': (3, 1),
        '전북': (0, 2), '대전': (1, 2), '대구': (2, 2), '울산': (3, 2),
        '광주': (0, 3), '전남': (1, 3), '경남': (2, 3), '부산': (3, 3),
        '제주': (1, 4)}
SUBLAB = {'': '', '생표고': '생표고', '건표고': '건표고'}


def load_prod_db(con):
    """item → sub → {'nat':{y:톤}, 'sido':{y:{시도:톤}}, 'sgg':{y:{(시도,시군구):톤}}}"""
    out = defaultdict(lambda: defaultdict(lambda: {'nat': defaultdict(float), 'sido': defaultdict(dict), 'sgg': defaultdict(dict)}))
    try:
        rows = con.execute('SELECT year,item,sub,sido,sigungu,kg FROM prod').fetchall()
    except Exception:
        return {}
    for y, item, sub, sd, sgg, kg in rows:
        d = out[item][sub]
        t = (kg or 0) / 1000.0
        if sd == '기관':
            d['nat'][y] += t
        elif not sgg:
            d['nat'][y] += t
            d['sido'][y][sd] = t
        else:
            d['sgg'][y][(sd, sgg)] = t
    try:                                                # 보고서 본문 「최근 5년」 표로 옛 연도 전국값을 채움
        for y, item, sub, tn in con.execute('SELECT year,item,sub,tonnes FROM prod_nat'):
            d = out[item][sub]
            if not d['nat'].get(y):
                d['nat'][y] = tn
    except Exception:
        pass
    return out


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02X%02X%02X' % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def tile_map(vals, nd, total, TW=132, TH=74, G=6, fs=(13, 11, 17)):
    """시도 타일맵 - 생산량이 많을수록 진한 숲 초록 (명암 단계)"""
    mx = max(vals.values(), default=0) or 1
    o = ['<svg viewBox="0 0 %d %d" role="img">' % (4 * TW + 3 * G, 5 * TH + 4 * G)]
    for sd, (cx, cy) in TILE.items():
        v = vals.get(sd, 0) or 0
        x, y = cx * (TW + G), cy * (TH + G)
        if v > 0:
            t = (v / mx) ** 0.5
            fill = _mix('#E4ECE1', '#1F3D2B', t)
            fg = '#FFFFFF' if t > 0.45 else '#17211B'
            sh = '%s%%' % fmt(v / total * 100, 1) if total else ''
        else:
            fill, fg, sh = '#F4F6F3', '#A3ADA6', ''
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="%s"/>' % (x, y, TW, TH, fill))
        o.append('<text class="tn" x="%d" y="%d" fill="%s" style="font-size:%dpx">%s</text>' % (x + 8, y + fs[0] + 7, fg, fs[0], sd))
        if sh:
            o.append('<text class="ts" x="%d" y="%d" fill="%s" style="font-size:%dpx">%s</text>' % (x + TW - 7, y + fs[0] + 7, fg, fs[1], sh))
        o.append('<text class="tv" x="%d" y="%d" fill="%s" style="font-size:%dpx">%s</text>' % (x + 8, y + TH - 12, fg, fs[2], fmt(v, nd) if v > 0 else '-'))
    o.append('</svg>')
    return ''.join(o)


def prod_cards(item, lab, PD, CSV=None):
    subs = PD.get(item) or {}
    cards = []
    for sub in [k for k in ('', '생표고', '건표고') if k in subs]:
        d = subs[sub]
        nat = {y: v for y, v in d['nat'].items() if v > 0}
        if not nat:
            continue
        name = (sub or lab)
        trend = not (sub and subs.get('') and subs['']['nat'])     # 표고는 생 · 건 합계 추이 하나만, 지역은 생 · 건 따로
        yrs = sorted(nat)[-13:]
        ly = yrs[-1]
        nd = nd_for(nat.values())
        spp = [{'name': '생산량', 'color': PRD, 'light': PRD_L, 'values': [nat[y] for y in yrs]}]
        p1 = pct(nat[ly], nat.get(ly - 1))
        if trend: cards.append('<div class="card span"><div class="sec">PRODUCTION · 임산물생산조사</div><div class="h2">%s 연간 생산량 %d년 %s톤%s</div>'
                     '<div class="cap">단위 : 톤 · 산림청 임산물생산조사(연 1회, 다음 해 10월 공표) · %d~%d년</div>%s</div>'
                     % (esc(name), ly, fmt(nat[ly], nd), (', 전년 대비 %s' % fmt_pct(p1)) if p1 is not None else '', yrs[0], ly,
                        dual([('%d년' % y, '') for y in yrs], spp, nd, w=1180, h=240, mob_labels=['%d년' % y for y in yrs])))
        # 시도 타일맵
        sido = d['sido'].get(ly, {})
        if sido:
            top_sd = sorted(sido.items(), key=lambda kv: -kv[1])[:3]
            cards.append('<div class="card"><div class="sec">BY PROVINCE · %d</div><div class="h2">시도별 %s 생산량</div>'
                         '<div class="cap">단위 : 톤 · 색이 진할수록 생산량이 많음 · 오른쪽 위는 전국 대비 비중 · 상위 : %s</div>%s</div>'
                         % (ly, esc(name), ' · '.join('%s %s%%' % (k, fmt(v / nat[ly] * 100, 1)) for k, v in top_sd),
                            '<div class="ch-d">%s</div><div class="ch-m">%s</div>'
                            % (tile_map(sido, nd, nat[ly]), tile_map(sido, nd, nat[ly], TW=86, TH=62, G=4, fs=(13, 10, 15)))))
        # 주산지 시군구 TOP 10 (명암)
        sg = d['sgg'].get(ly, {})
        if sg:
            top = sorted(sg.items(), key=lambda kv: -kv[1])[:10]
            mx = top[0][1] or 1
            cols = [_mix('#CFDCCB', '#1F3D2B', (v / mx) ** 0.7) for _, v in top]
            labels = ['%s %s' % (k[0], k[1]) for k, _ in top]
            ser1 = [{'name': '생산량', 'color': PRD, 'colors': cols, 'hl': [0], 'values': [v for _, v in top]}]
            hb = '<div class="ch-d">%s</div><div class="ch-m">%s</div>' % (hbars(labels, ser1, nd, w=560), hbars(labels, ser1, nd, w=360))
            share = sum(v for _, v in top) / nat[ly] * 100
            cards.append('<div class="card"><div class="sec">MAIN PRODUCING AREAS · %d</div><div class="h2">%s 주산지 상위 10개 시군구</div>'
                         '<div class="cap">단위 : 톤 · 막대 색이 진할수록 생산량이 많음 · 10곳이 전국의 %s%%</div>%s</div>'
                         % (ly, esc(name), fmt(share, 1), hb))
            # 주산지 변동 : 상위 10곳 × 최근 5년 + 전년 대비
            ys5 = [y for y in sorted(d['sgg']) if y > ly - 5]
            rows, cells = [], []
            for i, ((sd_, sg_), v) in enumerate(top):
                vs = [d['sgg'][y].get((sd_, sg_)) for y in ys5]
                pv = d['sgg'].get(ly - 1, {}).get((sd_, sg_))
                cells.append([str(i + 1), '%s %s' % (sd_, sg_)] + [fmt(x, nd) if x is not None else '-' for x in vs]
                             + [fmt_pct(pct(v, pv)) if pv else '-', fmt(v / nat[ly] * 100, 1)])
            nc = len(ys5) + 2
            ws = [span_w([c[j + 2] for c in cells]) for j in range(nc)]
            for c in cells:
                rows.append('<tr><td class="l">%s</td><td class="l"><b>%s</b></td>%s</tr>'
                            % (c[0], esc(c[1]), ''.join(numtd(c[j + 2], ws[j]) for j in range(nc))))
            # 상위 5곳 추이
            top5 = top[:5]
            yall = sorted(d['sgg'])
            yall = [y for y in yall if y > ly - 12]
            ser = [{'name': '%s %s' % k, 'color': TS_COL5[i], 'values': [d['sgg'][y].get(k) for y in yall]}
                   for i, (k, _) in enumerate(top5)]
            xs = ['%d-01' % y for y in yall]
            ln = ('<div class="ch-d">%s</div><div class="ch-m">%s</div>' % (lines(xs, ser, nd, h=250), lines(xs, ser, nd, w=360, h=240, fs=10.5))
                  if len(xs) >= 2 else '')
            cards.append('<div class="card span"><div class="sec">AREA TREND</div><div class="h2">%s 주산지별 생산량 변동</div>'
                         '<div class="cap">단위 : 톤 · %d년 상위 10개 시군구의 최근 %d년 · 그래프는 상위 5곳 %d~%d년</div>%s%s'
                         '<div class="tw"><table class="t"><thead><tr><th class="l">순위</th><th class="l">시군구</th>%s'
                         '<th>전년<br>대비</th><th>비중<br>(%%)</th></tr></thead><tbody>%s</tbody></table></div></div>'
                         % (esc(name), ly, len(ys5), yall[0], ly, legend(ser), ln,
                            ''.join('<th>%d년</th>' % y for y in ys5), ''.join(rows)))
    return ''.join(cards)


def trade_cand(key, lab, T, ref):
    """수출입 후보 문구 : 주된 흐름(수입 또는 수출)의 올해 누계 전년 동기 대비"""
    S = T.get(key, {})
    if not ref or not S:
        return None
    y, m = int(ref[:4]), int(ref[5:])
    g = lambda ym, f: (S.get(ym) or {}).get(f, 0) / 1000.0
    last12 = [ym_add(ref, -k) for k in range(12)]
    imp12, exp12 = sum(g(x, 'imp_kg') for x in last12), sum(g(x, 'exp_kg') for x in last12)
    f, fl = ('imp_kg', '수입') if imp12 >= exp12 else ('exp_kg', '수출')
    cur = sum(g('%04d-%02d' % (y, k), f) for k in range(1, m + 1))
    prv = sum(g('%04d-%02d' % (y - 1, k), f) for k in range(1, m + 1))
    nd = nd_for([cur, prv])
    p = pct(cur, prv)
    rng = '1~%d월' % m if m > 1 else '1월'
    if p is None:
        return '%s %s %s %s톤' % (lab, rng, fl, fmt(cur, nd)), None, cur
    word = '증가' if rnd(p, 1) > 0 else ('감소' if rnd(p, 1) < 0 else '보합')
    return '%s %s %s %s톤, 전년 동기 대비 %s%% %s' % (lab, rng, fl, fmt(cur, nd), fmt(abs(p), 1), word), p, cur


def prod_latest(item, PD):
    subs = PD.get(item) or {}
    d = subs.get('') or subs.get('생표고')
    if not d:
        return None, None, None
    nat = {y: v for y, v in d['nat'].items() if v > 0}
    if not nat:
        return None, None, None
    ly = max(nat)
    return ly, nat[ly], pct(nat[ly], nat.get(ly - 1))


# ── 핵심 이슈 선정 (가격 · 수급 · 수출입 · 정책 뉴스 중 가장 중요한 것) ──────────
STRONG = re.compile(r'급등|급락|폭등|폭락|급증|급감|큰 폭|크게|최대|최저|역대|대폭')
KEYM = re.compile(r'생산량|가격|출하량|수입량|수출량|시세')
MOVE = re.compile(r'하락|상승|약세|강세|감소|증가')


def pick_headline(lab, trade=None, K=None, news=None, today=None):
    """후보마다 점수를 매겨 가장 큰 것을 제목으로 - (분류, 출처, 제목)"""
    cands = []
    if trade:                                          # (문구, 증감률)
        txt, p, vol = trade
        w = 1.0 if vol >= 500 else (0.6 if vol >= 100 else 0.3)          # 물량이 작은 품목의 큰 증감률은 덜 중요
        sc = 1.5 + (min(abs(p), 60) / 10 * w if p is not None else 0)
        cands.append((sc, 3, '수출입 동향', '관세청 수출입실적', txt))
    if K:
        age = 0
        try:
            age = (today.replace(tzinfo=None) - datetime.strptime(K['ym'] + '-04', '%Y-%m-%d')).days if today else 0
        except Exception:
            pass
        stale = -2 if age > 75 else 0
        for h in K['heads']:
            t = h['head']
            fc = ('전망' in t or '듯' in t)
            base = {'가격': 3.5, '생산·출하': 3.2, '수출입': 2.6}.get(h['sec'], 2.5)
            sc = (base + (0.8 if fc else 0) + (2 if STRONG.search(t) else 0) + (0.7 if MOVE.search(t) else 0)
                  + (1.2 if KEYM.search(t) else -0.6) + stale)
            cat = {'가격': '가격', '생산·출하': '수급', '수출입': '수출입 동향'}.get(h['sec'], '수급')
            pri = {'가격': 5, '수급': 4, '수출입 동향': 3}[cat]
            t2 = t if lab.replace('떫은감', '감') in t or lab in t else '%s %s' % (lab, t)
            cands.append((sc, pri, cat, '농경연 임업관측 %s' % ko_ym(K['ym']), t2))
    for n in (news or [])[:15]:
        try:
            if today and (today.replace(tzinfo=None) - datetime.strptime(n['date'], '%Y-%m-%d')).days > 10:
                continue
        except Exception:
            pass
        txt = n['title'] + ' ' + (n.get('summary') or '')
        sc = 1.0 + min(score(txt), 10) * 0.45 + (1.0 if re.search(r'정책|대책|지원|시행|발표|추진|개정', n['title']) else 0) \
            + (1.5 if STRONG.search(n['title']) else 0)
        cands.append((sc, 2, '정책 · 이슈 뉴스', '뉴스 %s' % n['date'][5:].replace('-', '.'), n['title']))
    if not cands:
        return None
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
    sc, _, cat, src, txt = cands[0]
    return cat, src, txt, sc


# ── 표기 도우미 ──────────────────────────────────────────────
def t_(kg):
    return (kg or 0) / 1000.0            # kg → 톤


def k_(usd):
    return (usd or 0) / 1000.0           # 달러 → 천 달러


def nd_for(vals):
    """작은 값 품목은 소수 1자리, 나머지는 정수 - 한 품목 안에서는 통일"""
    m = max([abs(v) for v in vals] + [0])
    return 1 if m < 100 else 0


def arrow(p):
    if p is None:
        return '<span>-</span>'
    r = rnd(p, 1)
    cls = 'up' if r > 0 else ('dn' if r < 0 else '')
    return '<span class="%s">%s</span>' % (cls, fmt_pct(p))


def mlabel(ym, first=False):
    y, m = ym.split('-')
    return ('%d월' % int(m), y if (first or m == '01') else '')


def span_w(texts):
    return max([len(x) for x in texts] + [1]) * 0.6 + 0.3


def numtd(txt, w):
    return '<td class="n"><span style="min-width:%.1fem">%s</span></td>' % (w, txt)


# ── 조각 ──────────────────────────────────────────────────
def kpi(label, val, unit, sub, cls=''):
    return ('<div class="kpi"><div class="kv %s">%s<small>%s</small></div><div class="kl">%s</div>'
            '<div class="ks">%s</div></div>' % (cls, val, unit, label, sub))


def news_list(key, items, show=SHOW_NEWS, item_chip=False):
    if not items:
        return '<div class="empty">최근 %d일 동안 수집된 기사가 없음</div>' % NEWS_DAYS
    lab = {it['key']: it['label'] for it in ITEMS}
    lab['policy'] = '정책'
    li = []
    for i, n in enumerate(items[:40]):
        chip = ('<span class="chip o">%s</span>' % esc(lab.get(n['item'], ''))) if item_chip else ''
        li.append('<li%s><span class="d">%s</span><span class="tt">%s<span class="chip">%s</span>'
                  '<a href="%s" target="_blank" rel="noopener">%s</a></span></li>'
                  % (' class="ex"' if i >= show else '', n['date'][5:].replace('-', '.'), chip, esc(n['cat']),
                     esc(n['url']), esc(n['title'])))
    more = ''
    if len(items[:40]) > show:
        more = ('<label class="mbtn" for="nm-%s"><span class="o">기사 더보기 (%d건)</span><span class="c">접기</span></label>'
                % (key, len(items[:40]) - show))
        return '<input class="more" type="checkbox" id="nm-%s"><ul class="nl">%s</ul>%s' % (key, ''.join(li), more)
    return '<ul class="nl">%s</ul>' % ''.join(li)


def wait_card():
    return ('<div class="empty"><b>수출입 통계 수집 대기</b> - 저장소 Settings › Secrets › Actions에 '
            '<b>DATA_GO_KR_KEY</b>(공공데이터포털 「관세청_품목별 수출입실적(GW)」 인증키)를 등록하면 '
            '다음 자동 실행 때 2016년 1월부터 채워짐</div>')


def item_pane(it, T, forms, P, ref, news, K, KT, PD, PICK):
    key, lab = it['key'], it['label']
    S = T.get(key, {})
    g = lambda ym: S.get(ym, {'exp_kg': 0, 'exp_usd': 0, 'imp_kg': 0, 'imp_usd': 0})
    o = ['<section class="pane p-%s">' % key]

    prod = P.get(it['prod'], {}) or P.get(lab, {})
    if not ref or not S:
        pk = PICK.get(key)
        eb, h1 = ('%s · 핵심 이슈 · %s · %s' % (lab, pk[0], pk[1]), pk[2]) if pk else ('%s 수급 레이더' % lab, '%s 수급 레이더' % lab)
        o.append('<div class="hero"><div class="eyebrow">%s</div><h1>%s</h1></div>' % (esc(eb), esc(h1)))
        o.append(krei_card(key, K))
        o.append(ts_cards(key, KT))
        o.append('<div class="grid">%s</div>' % prod_cards(key, lab, PD))
        o.append('<div class="grid"><div class="card span">%s</div></div>' % wait_card())
    else:
        y, m = int(ref[:4]), int(ref[5:])
        ms13 = [ym_add(ref, -k) for k in range(12, -1, -1)]
        last12 = ms13[1:]
        imp12 = sum(t_(g(x)['imp_kg']) for x in last12)
        exp12 = sum(t_(g(x)['exp_kg']) for x in last12)
        allv = [t_(g(x)['imp_kg']) for x in S] + [t_(g(x)['exp_kg']) for x in S]
        nd = nd_for(allv)
        ndk = nd_for([k_(g(x)['imp_usd']) for x in S] + [k_(g(x)['exp_usd']) for x in S])
        now, prev = g(ref), g(ym_add(ref, -12))
        ytd = ['%04d-%02d' % (y, k) for k in range(1, m + 1)]
        ytdp = ['%04d-%02d' % (y - 1, k) for k in range(1, m + 1)]
        yi, yip = sum(t_(g(x)['imp_kg']) for x in ytd), sum(t_(g(x)['imp_kg']) for x in ytdp)
        ye, yep = sum(t_(g(x)['exp_kg']) for x in ytd), sum(t_(g(x)['exp_kg']) for x in ytdp)
        up_ = lambda d: (d['imp_usd'] / d['imp_kg']) if d['imp_kg'] else None
        main_imp = imp12 >= exp12
        fl, cur, pv = ('수입', t_(now['imp_kg']), t_(prev['imp_kg'])) if main_imp else ('수출', t_(now['exp_kg']), t_(prev['exp_kg']))
        p = pct(cur, pv)
        if p is None:
            h1 = '%s %s %d월 %s톤' % (lab, fl, m, fmt(cur, nd))
        else:
            h1 = '%s %s %d월 %s톤, 전년 동월 대비 %s%% %s' % (lab, fl, m, fmt(cur, nd), fmt(abs(p), 1),
                                                     '증가' if rnd(p, 1) > 0 else ('감소' if rnd(p, 1) < 0 else '보합'))
        rng = '1~%d월' % m if m > 1 else '1월'
        dek = ['%s 누계 수입 %s톤(전년 동기 대비 %s) · 수출 %s톤(%s)' % (rng, fmt(yi, nd), fmt_pct(pct(yi, yip)),
                                                               fmt(ye, nd), fmt_pct(pct(ye, yep)))]
        if up_(now):
            dek.append('%d월 수입 단가 kg당 %s달러%s' % (m, fmt(up_(now), 2),
                                                  ('(전년 동월 %s달러)' % fmt(up_(prev), 2)) if up_(prev) else ''))
        if news:
            dek.append('최근 기사 : <a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(news[0]['url']), esc(news[0]['title'])))
        pk = PICK.get(key)
        if pk:
            eb, h1 = '%s · 핵심 이슈 · %s · %s' % (lab, pk[0], pk[1]), pk[2]
        else:
            eb = '%s · 관세청 수출입실적 %d년 %d월 기준' % (lab, y, m)
        o.append('<div class="hero"><div class="eyebrow">%s</div><h1>%s</h1></div>' % (esc(eb), esc(h1)))

        ply, plv, plp = prod_latest(key, PD)
        if not ply and prod:
            ply = max(prod); plv = prod[ply]; plp = pct(plv, prod.get(ply - 1))
        pi, pe = pct(t_(now['imp_kg']), t_(prev['imp_kg'])), pct(t_(now['exp_kg']), t_(prev['exp_kg']))
        o.append('<div class="kpis">%s%s%s%s%s%s</div>' % (
            kpi('%d월 수입량' % m, fmt(t_(now['imp_kg']), nd), '톤', '전년 동월 대비 %s' % arrow(pi), 'i'),
            kpi('%d월 수출량' % m, fmt(t_(now['exp_kg']), nd), '톤', '전년 동월 대비 %s' % arrow(pe), 'e'),
            kpi('%s 수입 누계' % rng, fmt(yi, nd), '톤', '전년 동기 대비 %s' % arrow(pct(yi, yip)), 'i'),
            kpi('%s 수출 누계' % rng, fmt(ye, nd), '톤', '전년 동기 대비 %s' % arrow(pct(ye, yep)), 'e'),
            kpi('%d월 수입 단가' % m, fmt(up_(now), 2) if up_(now) else '-', '달러/kg',
                ('전년 동월 %s달러' % fmt(up_(prev), 2)) if up_(prev) else '전년 동월 수입 없음'),
            kpi('연간 생산량' + (' (%d년)' % ply if ply else ''), fmt(plv, nd_for([plv])) if ply else '-', '톤' if ply else '',
                ('전년 대비 %s' % arrow(plp)) if ply else '임산물생산조사 수집 대기')))

        o.append(krei_card(key, K))
        o.append(ts_cards(key, KT))
        labs = [mlabel(x, i == 0) for i, x in enumerate(ms13)]
        mob = ['%s.%s' % (x[2:4], x[5:]) for x in ms13]
        si = [{'name': '수입량', 'color': IMP, 'light': IMP_L, 'values': [t_(g(x)['imp_kg']) for x in ms13]}]
        se = [{'name': '수출량', 'color': EXP, 'light': EXP_L, 'values': [t_(g(x)['exp_kg']) for x in ms13]}]
        o.append('<div class="grid">')
        o.append('<div class="card"><div class="sec">MONTHLY IMPORT</div><div class="h2">최근 13개월 수입량</div>'
                 '<div class="cap">단위 : 톤 · %s ~ %s</div>%s</div>' % (ms13[0].replace('-', '.'), ref.replace('-', '.'),
                                                                     dual(labs, si, nd, mob_labels=mob)))
        o.append('<div class="card"><div class="sec">MONTHLY EXPORT</div><div class="h2">최근 13개월 수출량</div>'
                 '<div class="cap">단위 : 톤 · %s ~ %s</div>%s</div>' % (ms13[0].replace('-', '.'), ref.replace('-', '.'),
                                                                     dual(labs, se, nd, mob_labels=mob)))
        # 연도별 같은 기간 누계 (최근 8년)
        first_year = int(min(S)[:4])
        yrs = [yy for yy in range(max(first_year, y - 7), y + 1)]
        sp = lambda yy, f: sum(t_(g('%04d-%02d' % (yy, k))[f]) for k in range(1, m + 1))
        sy = [{'name': '수입량', 'color': IMP, 'light': IMP_L, 'values': [sp(yy, 'imp_kg') for yy in yrs]},
              {'name': '수출량', 'color': EXP, 'light': EXP_L, 'values': [sp(yy, 'exp_kg') for yy in yrs]}]
        o.append('<div class="card span"><div class="sec">YEAR TO DATE</div><div class="h2">연도별 %s 누계 수출입량</div>'
                 '<div class="cap">단위 : 톤 · 해마다 같은 기간(%s)끼리 비교</div>%s%s</div>'
                 % (rng, rng, legend(sy), dual([('%d년' % yy, '') for yy in yrs], sy, nd, w=1180, h=250,
                                               mob_labels=['%d년' % yy for yy in yrs])))
        o.append(prod_cards(key, lab, PD))

        # 월별 상세표 (최근 24개월, 최신이 위)
        rows = [ym_add(ref, -k) for k in range(0, 24) if ym_add(ref, -k) >= min(S)]
        cols = []
        for x in rows:
            d = g(x)
            cols.append([x.replace('-', '.'), fmt(t_(d['imp_kg']), nd), fmt(k_(d['imp_usd']), ndk),
                         fmt(up_(d), 2) if up_(d) else '-', fmt(t_(d['exp_kg']), nd), fmt(k_(d['exp_usd']), ndk),
                         fmt(k_(d['exp_usd'] - d['imp_usd']), ndk)])
        ws = [span_w([c[j] for c in cols]) for j in range(7)]
        body = ''.join('<tr%s><td class="l">%s</td>%s</tr>' % (' class="ex"' if i >= SHOW_ROWS else '', c[0],
                                                              ''.join(numtd(c[j], ws[j]) for j in range(1, 7)))
                       for i, c in enumerate(cols))
        tb = ('<div class="tw"><table class="t"><thead><tr><th class="l">연월</th><th>수입량<br>(톤)</th>'
              '<th>수입액<br>(천 달러)</th><th>수입 단가<br>(달러/kg)</th><th>수출량<br>(톤)</th><th>수출액<br>(천 달러)</th>'
              '<th>무역수지<br>(천 달러)</th></tr></thead><tbody>%s</tbody></table></div>' % body)
        more = ''
        if len(cols) > SHOW_ROWS:
            more = ('<label class="mbtn" for="tm-%s"><span class="o">24개월 전체 보기</span><span class="c">접기</span></label>' % key)
            tb = '<input class="more" type="checkbox" id="tm-%s">' % key + tb
        hsn = ' · '.join('%s %s' % (hs, esc(sk or fm)) for hs, (sk, fm) in sorted(forms.get(key, {}).items()))
        o.append('<div class="card span"><div class="sec">MONTHLY TABLE</div><div class="h2">월별 수출입 상세</div>'
                 '<div class="cap">최근 24개월 · 최신 월이 위 · 무역수지 = 수출액 - 수입액</div>%s%s'
                 '<div class="hsn">HS 부호 · 관세청 품목명 : %s</div></div>' % (tb, more, hsn))
        o.append('</div>')

    o.append('<div class="grid"><div class="card span"><div class="sec">NEWS</div><div class="h2">%s 최근 뉴스</div>'
             '<div class="cap">최근 %d일 · 제목에 품목 핵심어가 있는 기사만 · 최신순</div>%s</div></div>'
             % (esc(lab), NEWS_DAYS, news_list(key, news)))
    o.append('</section>')
    return ''.join(o)


def summary_pane(T, P, ref, allnews, K, PICK=None):
    o = ['<section class="pane p-all">']
    if not ref:
        o.append('<div class="hero"><div class="eyebrow">임산물 수급 레이더 · 종합</div><h1>임산물 5개 품목 수출입 · 생산 · 뉴스 모니터링</h1>'
                 '<ul class="dek"><li>품목 탭에서 밤 · 호두 · 대추 · 표고버섯 · 떫은감을 각각 확인</li>'
                 '<li>뉴스는 매일, 관세청 수출입 통계는 매월 자동 갱신</li></ul></div>')
        o.append(krei_overview(K))
        o.append('<div class="grid"><div class="card span">%s</div></div>' % wait_card())
    else:
        y, m = int(ref[:4]), int(ref[5:])
        rng = '1~%d월' % m if m > 1 else '1월'
        last12 = [ym_add(ref, -k) for k in range(11, -1, -1)]
        rows, i12, e12, movers = [], [], [], []
        for it in ITEMS:
            S = T.get(it['key'], {})
            g = lambda ym: S.get(ym, {'exp_kg': 0, 'exp_usd': 0, 'imp_kg': 0, 'imp_usd': 0})
            nd = 1                                              # 요약표는 열마다 소수 1자리로 통일
            now, prev = g(ref), g(ym_add(ref, -12))
            yi = sum(t_(g('%04d-%02d' % (y, k))['imp_kg']) for k in range(1, m + 1))
            yip = sum(t_(g('%04d-%02d' % (y - 1, k))['imp_kg']) for k in range(1, m + 1))
            ye = sum(t_(g('%04d-%02d' % (y, k))['exp_kg']) for k in range(1, m + 1))
            yep = sum(t_(g('%04d-%02d' % (y - 1, k))['exp_kg']) for k in range(1, m + 1))
            rows.append([it['label'], fmt(t_(now['imp_kg']), nd), arrow(pct(t_(now['imp_kg']), t_(prev['imp_kg']))),
                         fmt(t_(now['exp_kg']), nd), arrow(pct(t_(now['exp_kg']), t_(prev['exp_kg']))),
                         fmt(yi, nd), arrow(pct(yi, yip)), fmt(ye, nd), arrow(pct(ye, yep))])
            i12.append((it['label'], sum(t_(g(x)['imp_kg']) for x in last12)))
            e12.append((it['label'], sum(t_(g(x)['exp_kg']) for x in last12)))
            pp = pct(yi, yip)
            if pp is not None and yip >= 1:
                movers.append((abs(pp), it['label'], pp))
        movers.sort(reverse=True)
        h1 = '임산물 5개 품목 수출입 동향 - %d년 %d월 기준' % (y, m)
        best = max((v for v in (PICK or {}).values() if v), key=lambda v: v[3], default=None)
        dek = ['%s 수입 누계 전년 동기 대비 변화가 가장 큰 품목 : %s' % (
            rng, ' · '.join('%s %s' % (lb, fmt_pct(pp)) for _, lb, pp in movers[:3]) or '-'),
            '품목 탭에서 월별 추이 · 연도별 누계 · 생산량 · 최근 뉴스를 확인']
        eb = '임산물 수급 레이더 · 종합'
        if best:
            eb, h1 = '임산물 수급 레이더 · 오늘의 핵심 이슈 · %s · %s' % (best[0], best[1]), best[2]
        o.append('<div class="hero"><div class="eyebrow">%s</div><h1>%s</h1></div>' % (esc(eb), esc(h1)))
        ws = [span_w([re.sub('<[^>]+>', '', r[j]) for r in rows]) for j in range(9)]
        body = ''.join('<tr><td class="l"><b>%s</b></td>%s</tr>' % (r[0], ''.join(numtd(r[j], ws[j]) for j in range(1, 9)))
                       for r in rows)
        o.append(krei_overview(K))
        o.append('<div class="grid"><div class="card span"><div class="sec">OVERVIEW</div><div class="h2">품목별 수출입 요약</div>'
                 '<div class="cap">단위 : 톤 · 증감률은 전년 같은 달 · 같은 기간 대비</div><div class="tw"><table class="t"><thead>'
                 '<tr><th class="l">품목</th><th>%d월<br>수입량</th><th>전년<br>동월 대비</th><th>%d월<br>수출량</th><th>전년<br>동월 대비</th>'
                 '<th>%s<br>수입 누계</th><th>전년<br>동기 대비</th><th>%s<br>수출 누계</th><th>전년<br>동기 대비</th></tr></thead>'
                 '<tbody>%s</tbody></table></div></div>' % (m, m, rng, rng, body))
        for title, arr, col, sec in (('최근 12개월 수입량', i12, IMP, 'IMPORT'), ('최근 12개월 수출량', e12, EXP, 'EXPORT')):
            arr = sorted(arr, key=lambda x: -x[1])              # 값이 큰 품목이 위
            nd = nd_for([v for _, v in arr])
            o.append('<div class="card"><div class="sec">%s · 12 MONTHS</div><div class="h2">%s</div>'
                     '<div class="cap">단위 : 톤 · %s ~ %s 합계</div>%s</div>'
                     % (sec, title, last12[0].replace('-', '.'), ref.replace('-', '.'),
                        hbars([a for a, _ in arr], [{'name': title, 'color': col, 'light': (IMP_L if col == IMP else EXP_L), 'hl': [0], 'values': [v for _, v in arr]}], nd, w=560)))
        o.append('</div>')
    o.append('<div class="grid"><div class="card span"><div class="sec">NEWS</div><div class="h2">임업 · 임산물 최근 뉴스</div>'
             '<div class="cap">최근 %d일 · 임업 정책과 5개 품목 기사 통합 · 최신순</div>%s</div></div>'
             % (NEWS_DAYS, news_list('all', allnews, 12, item_chip=True)))
    o.append('</section>')
    return ''.join(o)


# ── 검증 게이트 ─────────────────────────────────────────────
NUM = re.compile(r'^-?\d{1,3}(,\d{3})*(\.\d+)?$')


def verify(doc):
    errs = []
    for tag in re.findall(r'<text class="(?:v|vh|ve|vs|tk)"[^>]*>([^<]*)</text>', doc):
        if not tag.strip():
            errs.append('빈 수치 라벨')
        elif not NUM.match(tag):
            errs.append('수치 라벨 형식 오류 : %r' % tag)
    for bad in ('—', '–', '>None<', 'nan<', '>nan', 'NaN'):
        if bad in doc:
            errs.append('금지 문자열 %r' % bad)
    for v in re.findall(r'<div class="kv[^"]*">([^<]*)<small>', doc):
        if v != '-' and not NUM.match(v):
            errs.append('KPI 수치 형식 오류 : %r' % v)
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=DB)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--prod', default=PROD)
    a = ap.parse_args()
    con = db(a.db)
    today = datetime.now(KST)
    T, forms = load_trade(con)
    P = load_prod(a.prod)
    yms = [ym for S in T.values() for ym in S]
    ref = max(yms) if yms else None
    meta = dict(con.execute('SELECT k,v FROM meta').fetchall())

    news = {it['key']: load_news(con, it['key'], today) for it in ITEMS}
    allnews = load_news(con, 'policy', today) + [n for it in ITEMS for n in news[it['key']]]
    allnews.sort(key=lambda n: n['date'], reverse=True)

    keys = ['all'] + [it['key'] for it in ITEMS]
    tog = []
    for k in keys:
        tog.append('#t-%s:checked~.wrap .tabs label[for=t-%s]{background:var(--green);border-color:var(--green);color:#fff}' % (k, k))
        tog.append('#t-%s:checked~.wrap .p-%s{display:block}' % (k, k))
    css = CSS.replace('%%', '%').replace('%(TOGGLE)s', '\n'.join(tog))

    K = load_krei(con)
    KT = load_krei_ts(con)
    PD = load_prod_db(con)
    PICK = {}
    for it in ITEMS:
        PICK[it['key']] = pick_headline(it['label'], trade_cand(it['key'], it['label'], T, ref), K.get(it['key']),
                                        news[it['key']], today)
    body = [summary_pane(T, P, ref, allnews, K, PICK)]
    body += [item_pane(it, T, forms, P, ref, news[it['key']], K, KT, PD, PICK) for it in ITEMS]
    radios = ''.join('<input class="tg" type="radio" name="tg" id="t-%s"%s>' % (k, ' checked' if k == 'all' else '') for k in keys)
    tabs = '<nav class="tabs"><label for="t-all">종합</label>%s</nav>' % ''.join(
        '<label for="t-%s">%s</label>' % (it['key'], it['label']) for it in ITEMS)
    err = ('<br>수출입 수집 알림 : %s' % esc(meta['trade_err'])) if meta.get('trade_err') else ''
    doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>임산물 수급 레이더</title>'
           '<meta name="description" content="밤 · 호두 · 대추 · 표고버섯 · 떫은감 월별 수출입, 연간 생산량, 최근 뉴스">%s</head><body>'
           '<header class="mast"><div class="in"><div class="logos"><img class="lg-sp" src="assets/logo_southernpost.png" alt="서던포스트">'
           '<span class="x">×</span><img class="lg-kf" src="assets/logo_kofpi.png" alt="한국임업진흥원"></div><div class="vr"></div>'
           '<div class="team"><span class="t1">품목별 수출입 · 가격 · 전망 · 뉴스</span><span class="t2">임산물 수급 레이더</span></div>'
           '<div class="upd">페이지 갱신 <b>%s</b><br>수출입 기준월 <b>%s</b></div></div>'
           '<div class="ribbon"><i></i><i></i><i></i></div></header>%s<main class="wrap">%s%s'
           '<footer class="foot"><b>자료</b> 관세청 수출입무역통계(공공데이터포털 「품목별 수출입실적」 API, 중량 · 금액 월별) · '
           '한국농촌경제연구원 임업관측 월보(매월 4일) · 산림청 임산물생산조사(연간) · 네이버 뉴스 · Google 뉴스<br>'
           '<b>갱신</b> 뉴스 매일 07:00 · 수출입 매일 확인(최근 14개월 재수집으로 잠정치 수정 반영) · '
           '월별 수치는 HS 부호 합산(밤 · 표고버섯은 냉동 · 조제품 포함, 농경연 관측 월보와 같은 범위)%s<br>'
           '<b>(주)서던포스트</b> · 최근 뉴스 수집 %s · 최근 수출입 수집 %s</footer></main></body></html>'
           % (css, today.strftime('%Y.%m.%d %H:%M'), (ref.replace('-', '.') if ref else '수집 대기'), radios, tabs,
              ''.join(body), err, meta.get('news_run', '-'), meta.get('trade_run', '-')))
    doc = doc.replace('—', '-').replace('–', '-')
    doc = re.sub(r'<ul class="dek">.*?</ul>', '', doc, flags=re.S)   # 요약부는 헤드라인과 주요 수치만
    errs = verify(doc)
    if errs:
        print('검증 실패 - 페이지를 쓰지 않음')
        for e in sorted(set(errs))[:30]:
            print('  ', e)
        sys.exit(1)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write(doc)
    print('작성 %s · 기준월 %s · 뉴스 %d건 · 검증 통과' % (a.out, ref, len(allnews)))


if __name__ == '__main__':
    main()
