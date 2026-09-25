# -*- coding: utf-8 -*-
"""
data/radar.db + data/production.csv → docs/index.html (GitHub Pages 공개 페이지)

디자인 : 서던 하우스(딥그린 #1E4A4A · 오렌지 #F08900), Pretendard 서브셋 자체 호스팅
  - 탭 : 종합 · 밤 · 호두 · 대추 · 잣 · 표고버섯 · 떫은감 (라디오 토글, 자바스크립트 없이 동작)
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
from items import ITEMS, POLICY
from charts import dual, hbars, legend, esc, lines

OUT = os.path.join(ROOT, 'docs', 'index.html')
PROD = os.path.join(ROOT, 'data', 'production.csv')
IMP, EXP = '#1E4A4A', '#F08900'
NEWS_DAYS = 30
SHOW_NEWS, SHOW_ROWS = 10, 12

CSS = """<style>
@font-face{font-family:'PretendardSub';font-weight:400;font-display:swap;src:url(assets/fonts/pretendard-sub-Regular.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:600;font-display:swap;src:url(assets/fonts/pretendard-sub-SemiBold.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:800;font-display:swap;src:url(assets/fonts/pretendard-sub-ExtraBold.woff2) format('woff2')}
:root{--green:#1E4A4A;--green-d:#123232;--org:#F08900;--org-d:#B86700;--ink:#182222;--sub:#475353;--muted:#859090;
  --rule:#E2E6E4;--rule2:#EFF2F0;--bg:#F7F8F6;--card:#fff;--tint:#EAF1EF;--otint:#FDF1E1}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.55;letter-spacing:-.1px;
  font-family:'PretendardSub','Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif}
a{color:inherit;text-decoration:none}
.mast{background:#fff;border-bottom:1px solid var(--rule)}
.mast .in{max-width:1240px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.wm{font-size:19px;font-weight:800;letter-spacing:-.6px;color:var(--green)}
.wm b{color:var(--org)}
.vr{width:1px;height:28px;background:var(--rule)}
.team{display:flex;flex-direction:column;line-height:1.25}
.team .t1{font-size:12px;font-weight:600;color:var(--muted)}
.team .t2{font-size:17px;font-weight:800;letter-spacing:-.4px}
.upd{margin-left:auto;text-align:right;font-size:12px;color:var(--muted);line-height:1.45}
.upd b{color:var(--ink);font-weight:600}
.ribbon{display:flex;height:4px}.ribbon i{flex:3;background:var(--green)}.ribbon i+i{flex:1;background:var(--org)}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px}
.tg{position:absolute;opacity:0;pointer-events:none}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:22px 0 22px}
.tabs label{cursor:pointer;border:1px solid var(--rule);background:#fff;border-radius:999px;padding:8px 18px;font-weight:800;font-size:14px;color:var(--sub)}
.tabs label:hover{border-color:var(--green)}
.pane{display:none}
%(TOGGLE)s
.hero{padding:2px 0 20px 18px;border-left:5px solid var(--green);margin:0 0 20px}
.eyebrow{font-size:11.5px;font-weight:800;letter-spacing:1px;color:var(--green)}
.hero h1{font-size:30px;line-height:1.3;font-weight:800;letter-spacing:-1px;margin:6px 0 10px;word-break:keep-all}
.dek{list-style:none;margin:0;padding:0;font-size:14px;color:var(--sub)}
.dek li{padding-left:14px;position:relative;margin:3px 0;word-break:keep-all}
.dek li:before{content:'';position:absolute;left:2px;top:.72em;width:5px;height:5px;background:var(--org);border-radius:50%%}
.dek a{color:var(--ink);font-weight:600;border-bottom:1px solid var(--rule)}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);background:#fff;border:1px solid var(--rule);border-top:3px solid var(--green);margin-bottom:20px}
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
.card{background:#fff;border:1px solid var(--rule);padding:18px 20px 20px}
.span{grid-column:1/-1}
.sec{font-size:11.5px;font-weight:800;letter-spacing:1px;color:var(--org-d)}
.h2{font-size:18px;font-weight:800;letter-spacing:-.5px;margin:3px 0 2px;word-break:keep-all}
.cap{font-size:12px;color:var(--muted);margin-bottom:10px;word-break:keep-all}
.lg{display:flex;gap:14px;font-size:12px;color:var(--sub);margin:0 0 6px}
.lg i{display:inline-block;width:10px;height:10px;margin-right:5px;vertical-align:-1px}
svg{width:100%%;height:auto;display:block;overflow:visible}
svg text{font-family:'PretendardSub','Pretendard','Malgun Gothic',sans-serif}
svg .v{fill:var(--ink);font-weight:800;text-anchor:middle;font-variant-numeric:tabular-nums}
svg .x{fill:var(--sub);text-anchor:middle;font-weight:600}
svg .x2{fill:var(--muted);text-anchor:middle}
svg .yl{fill:var(--sub);font-size:12px;text-anchor:end;font-weight:600}
svg .vh{fill:var(--ink);font-size:12px;font-weight:800;font-variant-numeric:tabular-nums}
svg .base{stroke:#BFC7C4;stroke-width:1}
svg .grid{stroke:#EEF1EF;stroke-width:1}
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
.kh{font-size:12px;font-weight:800;color:var(--org-d);border-bottom:2px solid var(--ink);padding-bottom:6px;margin-bottom:4px}
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
  .upd{margin-left:0;text-align:left;width:100%%}.vr{display:none}
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


def load_krei_ts(con):
    """item → [{tkey, title, unit, subs:{sub:{ym:v}}}] (최근 18개월 안에 값이 있는 표만)"""
    out = defaultdict(dict)
    try:
        rows = con.execute('SELECT item,tkey,title,unit,sub,ym,value,src FROM krei_ts').fetchall()
    except Exception:
        return {}
    for item, k, title, unit, sub, ym, v, src in rows:
        d = out[item].setdefault(k, {'tkey': k, 'title': title, 'unit': unit, 'src': src, 'subs': defaultdict(dict)})
        if src >= d['src']:
            d['title'], d['unit'], d['src'] = title, unit or d['unit'], src
        d['subs'][sub][ym] = v
    res = {}
    for item, tabs in out.items():
        last = max(ym for t in tabs.values() for sd in t['subs'].values() for ym in sd)
        keep = [t for t in tabs.values() if max(ym for sd in t['subs'].values() for ym in sd) >= ym_add(last, -18)]
        keep.sort(key=lambda t: (0 if '가격' in t['title'] else 1 if '수입' in t['title'] else 2 if '수출' in t['title'] else 3, t['title']))
        res[item] = keep
    return res


TS_COL = ['#1E4A4A', '#F08900', '#6F8F7F', '#9AA5A2']


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
                 '%s%s%s</div>' % (esc(t['title'].lstrip('\uf06c ').strip()), esc(t['unit'] or '-'), xs[0].replace('-', '.'),
                                    last.replace('-', '.'), lg, chart, tb))
    return '<div class="grid">%s</div>' % ''.join(o)


def ko_ym(ym):
    return '%s년 %d월호' % (ym[:4], int(ym[5:]))


def krei_card(item_key, K):
    k = K.get(item_key)
    if item_key == 'pinenut':
        return ('<div class="grid"><div class="card span"><div class="sec">KREI OUTLOOK</div><div class="h2">농경연 임업관측</div>'
                '<div class="empty">잣은 한국농촌경제연구원 임업관측(밤 · 표고버섯 · 대추 · 감 · 호두 · 산채 · 오미자 · 조경수) 대상 품목이 아님</div></div></div>')
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
            '<div class="cap">품목별 최신 월보에서 절마다 전망 문장 우선 1개 · 잣은 관측 대상 아님</div><div class="tw"><table class="t kt"><thead><tr>'
            '<th class="l">품목</th><th class="l">월보</th><th class="l">생산 · 출하</th><th class="l">수출입</th><th class="l">가격</th>'
            '</tr></thead><tbody>%s</tbody></table></div></div></div>' % ''.join(rows))


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


def item_pane(it, T, forms, P, ref, news, K, KT):
    key, lab = it['key'], it['label']
    S = T.get(key, {})
    g = lambda ym: S.get(ym, {'exp_kg': 0, 'exp_usd': 0, 'imp_kg': 0, 'imp_usd': 0})
    o = ['<section class="pane p-%s">' % key]

    prod = P.get(it['prod'], {}) or P.get(lab, {})
    if not ref or not S:
        k = K.get(key)
        fc = [h for h in (k['heads'] if k else []) if '전망' in h['head'] or '듯' in h['head']]
        if fc:
            eb = '%s · 농경연 임업관측 %s' % (lab, ko_ym(k['ym']))
            h1 = fc[0]['head']
            dek = ['%s' % esc(h['head']) for h in fc[1:3]]
        else:
            eb, h1 = '%s · 수출입 · 생산 · 뉴스' % lab, '%s 수급 레이더' % lab
            dek = ['관세청 월별 수출입 통계가 들어오면 지표 · 차트가 자동으로 채워짐']
        if news:
            dek.append('최근 기사 : <a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(news[0]['url']), esc(news[0]['title'])))
        o.append('<div class="hero"><div class="eyebrow">%s</div><h1>%s</h1><ul class="dek">%s</ul></div>'
                 % (esc(eb), esc(h1), ''.join('<li>%s</li>' % d for d in dek)))
        o.append(krei_card(key, K))
        o.append(ts_cards(key, KT))
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
        o.append('<div class="hero"><div class="eyebrow">%s · 관세청 수출입실적 %d년 %d월 기준</div><h1>%s</h1>'
                 '<ul class="dek">%s</ul></div>' % (esc(lab), y, m, esc(h1), ''.join('<li>%s</li>' % d for d in dek)))

        py = max(prod) if prod else None
        pi, pe = pct(t_(now['imp_kg']), t_(prev['imp_kg'])), pct(t_(now['exp_kg']), t_(prev['exp_kg']))
        o.append('<div class="kpis">%s%s%s%s%s%s</div>' % (
            kpi('%d월 수입량' % m, fmt(t_(now['imp_kg']), nd), '톤', '전년 동월 대비 %s' % arrow(pi), 'i'),
            kpi('%d월 수출량' % m, fmt(t_(now['exp_kg']), nd), '톤', '전년 동월 대비 %s' % arrow(pe), 'e'),
            kpi('%s 수입 누계' % rng, fmt(yi, nd), '톤', '전년 동기 대비 %s' % arrow(pct(yi, yip)), 'i'),
            kpi('%s 수출 누계' % rng, fmt(ye, nd), '톤', '전년 동기 대비 %s' % arrow(pct(ye, yep)), 'e'),
            kpi('%d월 수입 단가' % m, fmt(up_(now), 2) if up_(now) else '-', '달러/kg',
                ('전년 동월 %s달러' % fmt(up_(prev), 2)) if up_(prev) else '전년 동월 수입 없음'),
            kpi('연간 생산량' + (' (%d년)' % py if py else ''), fmt(prod[py], nd_for(prod.values())) if py else '-', '톤' if py else '',
                '임산물생산조사' if py else '공표값 입력 대기')))

        o.append(krei_card(key, K))
        o.append(ts_cards(key, KT))
        labs = [mlabel(x, i == 0) for i, x in enumerate(ms13)]
        mob = ['%s.%s' % (x[2:4], x[5:]) for x in ms13]
        si = [{'name': '수입량', 'color': IMP, 'values': [t_(g(x)['imp_kg']) for x in ms13]}]
        se = [{'name': '수출량', 'color': EXP, 'values': [t_(g(x)['exp_kg']) for x in ms13]}]
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
        sy = [{'name': '수입량', 'color': IMP, 'values': [sp(yy, 'imp_kg') for yy in yrs]},
              {'name': '수출량', 'color': EXP, 'values': [sp(yy, 'exp_kg') for yy in yrs]}]
        o.append('<div class="card span"><div class="sec">YEAR TO DATE</div><div class="h2">연도별 %s 누계 수출입량</div>'
                 '<div class="cap">단위 : 톤 · 해마다 같은 기간(%s)끼리 비교</div>%s%s</div>'
                 % (rng, rng, legend(sy), dual([('%d년' % yy, '') for yy in yrs], sy, nd, w=1180, h=250,
                                               mob_labels=['%d년' % yy for yy in yrs])))
        o.append('<div class="card span"><div class="sec">PRODUCTION</div><div class="h2">연간 생산량</div>')
        if prod:
            pyrs = sorted(prod)[-8:]
            spp = [{'name': '생산량', 'color': '#6F8F7F', 'values': [prod[yy] for yy in pyrs]}]
            o.append('<div class="cap">단위 : 톤 · 산림청 임산물생산조사(연 1회, 다음 해 10월 공표)</div>%s'
                     % dual([('%d년' % yy, '') for yy in pyrs], spp, nd_for(prod.values()), w=1180, h=230,
                            mob_labels=['%d년' % yy for yy in pyrs]))
        else:
            o.append('<div class="cap">산림청 임산물생산조사(연 1회, 다음 해 10월 공표)</div>'
                     '<div class="empty">월별 생산량은 국가통계로 공표되지 않음 · 연간 공표값을 '
                     '<b>data/production.csv</b>에 넣으면 이 자리에 추이가 표시됨</div>')
        o.append('</div>')

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


def summary_pane(T, P, ref, allnews, K):
    o = ['<section class="pane p-all">']
    if not ref:
        o.append('<div class="hero"><div class="eyebrow">임산물 수급 레이더 · 종합</div><h1>임산물 6개 품목 수출입 · 생산 · 뉴스 모니터링</h1>'
                 '<ul class="dek"><li>품목 탭에서 밤 · 호두 · 대추 · 잣 · 표고버섯 · 떫은감을 각각 확인</li>'
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
        h1 = '임산물 6개 품목 수출입 동향 - %d년 %d월 기준' % (y, m)
        dek = ['%s 수입 누계 전년 동기 대비 변화가 가장 큰 품목 : %s' % (
            rng, ' · '.join('%s %s' % (lb, fmt_pct(pp)) for _, lb, pp in movers[:3]) or '-'),
            '품목 탭에서 월별 추이 · 연도별 누계 · 생산량 · 최근 뉴스를 확인']
        o.append('<div class="hero"><div class="eyebrow">임산물 수급 레이더 · 종합</div><h1>%s</h1><ul class="dek">%s</ul></div>'
                 % (esc(h1), ''.join('<li>%s</li>' % d for d in dek)))
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
                        hbars([a for a, _ in arr], [{'name': title, 'color': col, 'values': [v for _, v in arr]}], nd, w=560)))
        o.append('</div>')
    o.append('<div class="grid"><div class="card span"><div class="sec">NEWS</div><div class="h2">임업 · 임산물 최근 뉴스</div>'
             '<div class="cap">최근 %d일 · 임업 정책과 6개 품목 기사 통합 · 최신순</div>%s</div></div>'
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
    body = [summary_pane(T, P, ref, allnews, K)]
    body += [item_pane(it, T, forms, P, ref, news[it['key']], K, KT) for it in ITEMS]
    radios = ''.join('<input class="tg" type="radio" name="tg" id="t-%s"%s>' % (k, ' checked' if k == 'all' else '') for k in keys)
    tabs = '<nav class="tabs"><label for="t-all">종합</label>%s</nav>' % ''.join(
        '<label for="t-%s">%s</label>' % (it['key'], it['label']) for it in ITEMS)
    err = ('<br>수출입 수집 알림 : %s' % esc(meta['trade_err'])) if meta.get('trade_err') else ''
    doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>임산물 수급 레이더</title>'
           '<meta name="description" content="밤 · 호두 · 대추 · 잣 · 표고버섯 · 떫은감 월별 수출입, 연간 생산량, 최근 뉴스">%s</head><body>'
           '<header class="mast"><div class="in"><div class="wm">SOUTHERN<b>POST</b></div><div class="vr"></div>'
           '<div class="team"><span class="t1">(주)서던포스트</span><span class="t2">임산물 수급 레이더</span></div>'
           '<div class="upd">페이지 갱신 <b>%s</b><br>수출입 기준월 <b>%s</b></div></div>'
           '<div class="ribbon"><i></i><i></i></div></header>%s<main class="wrap">%s%s'
           '<footer class="foot"><b>자료</b> 관세청 수출입무역통계(공공데이터포털 「품목별 수출입실적」 API, 중량 · 금액 월별) · '
           '한국농촌경제연구원 임업관측 월보(매월 4일) · 산림청 임산물생산조사(연간) · 네이버 뉴스 · Google 뉴스<br>'
           '<b>갱신</b> 뉴스 매일 07:00 · 수출입 매일 확인(최근 14개월 재수집으로 잠정치 수정 반영) · '
           '월별 수치는 HS 부호 합산(밤 · 표고버섯은 냉동 · 조제품 포함, 농경연 관측 월보와 같은 범위)%s<br>'
           '<b>(주)서던포스트</b> · 최근 뉴스 수집 %s · 최근 수출입 수집 %s</footer></main></body></html>'
           % (css, today.strftime('%Y.%m.%d %H:%M'), (ref.replace('-', '.') if ref else '수집 대기'), radios, tabs,
              ''.join(body), err, meta.get('news_run', '-'), meta.get('trade_run', '-')))
    doc = doc.replace('—', '-').replace('–', '-')
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
