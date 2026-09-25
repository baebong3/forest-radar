# -*- coding: utf-8 -*-
"""
data/radar.db → docs/index.html (GitHub Pages 공개 페이지) · 임업진흥원 담당자 데일리 확인용

디자인 : 숲 초록 #1F3D2B 바탕 + 품목별 고유색 · 그림 (밤 밤색 · 호두 올리브 · 대추 적색 · 표고 먹갈색 · 떫은감 주황)
  - 상단 : 자료 기준(수출입 · 임업관측 · 생산조사 · 오늘 뉴스) 한 줄, 품목 그림이 들어간 고정 탭
  - 종합 탭 : 오늘의 핵심 이슈 → 품목 보드(품목별 핵심 이슈 · 생산 · 수입 · 수출 · 추이) → 뉴스 + 임업관측 전망
             → 생산량 → 수출입
  - 품목 탭 : 품목 머리(그림 · 핵심 이슈) → 주요 수치(추이 그림 포함) → 임업관측 · 뉴스 · 가격 → 생산량 → 수출입
  - 긴 월별 표는 접어 두고 필요할 때 펼침 (자바스크립트 없이 동작)
  - 수입 = 숲 초록, 수출 = 앰버 (모든 탭 공통) · 생산 · 가격 · 주산지는 품목색
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
from charts import dual, hbars, legend, esc, lines, spark
from art import PAL, icon, ridge, hill

OUT = os.path.join(ROOT, 'docs', 'index.html')
PROD = os.path.join(ROOT, 'data', 'production.csv')
IMP, EXP = '#1F3D2B', '#B8742A'          # 수입 = 숲 초록, 수출 = 밤색 앰버
IMP_L, EXP_L = '#C3D1BE', '#EBD6BC'
NEWS_DAYS = 30
SHOW_NEWS, SHOW_ROWS = 6, 12
WD = '월화수목금토일'

CSS = """<style>
@font-face{font-family:'PretendardSub';font-weight:400;font-display:swap;src:url(assets/fonts/pretendard-sub-Regular.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:600;font-display:swap;src:url(assets/fonts/pretendard-sub-SemiBold.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:800;font-display:swap;src:url(assets/fonts/pretendard-sub-ExtraBold.woff2) format('woff2')}
:root{color-scheme:light;--green:#1F3D2B;--moss:#5E7F4F;--sage:#A9BBA2;--org:#B8742A;--org-d:#8C5518;
  --ink:#17211B;--sub:#4B5A50;--muted:#86928A;--rule:#E3E8E1;--rule2:#EFF2ED;--bg:#FFFFFF;--tint:#EEF3EC;
  --c:#1F3D2B;--t:#EEF3EC;--d:#142A1D}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:var(--ink);font-size:14px;line-height:1.55;letter-spacing:-.1px;
  font-family:'PretendardSub','Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif}
a{color:inherit;text-decoration:none}
svg{width:100%;height:auto;display:block;overflow:visible}
svg.ico{flex:none;overflow:visible}
svg text{font-family:'PretendardSub','Pretendard','Malgun Gothic',sans-serif}

/* 머리 */
.mast .in{max-width:1240px;margin:0 auto;padding:14px 16px 12px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.logos{display:flex;align-items:center;gap:12px}
.lg-sp{height:24px;width:auto;display:block}.lg-kf{height:32px;width:auto;display:block}
.logos .x{font-size:14px;color:var(--muted);font-weight:600}
.vr{width:1px;height:30px;background:var(--rule)}
.team{display:flex;flex-direction:column;line-height:1.25}
.team .t1{font-size:12px;font-weight:600;color:var(--muted)}
.team .t2{font-size:18px;font-weight:800;letter-spacing:-.5px;color:var(--green)}
.fresh{margin-left:auto;display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.fresh span{display:inline-flex;align-items:baseline;gap:6px;border:1px solid var(--rule);border-radius:8px;padding:4px 10px;font-size:12px;white-space:nowrap}
.fresh em{font-style:normal;color:var(--muted);font-weight:600}
.fresh b{font-weight:800;font-variant-numeric:tabular-nums}
.fresh .nw b{color:#B23A2A}
.ribbon{display:flex;height:5px}.ribbon i{flex:1}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px}

/* 탭 */
.tg{position:absolute;opacity:0;pointer-events:none}
.tabs{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.97);display:flex;gap:6px;overflow-x:auto;
  padding:12px 0;margin:0 0 20px;border-bottom:1px solid var(--rule);scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tabs label{--c:#1F3D2B;--t:#EEF3EC;cursor:pointer;display:inline-flex;align-items:center;gap:8px;white-space:nowrap;flex:none;
  border:1px solid var(--rule);background:#fff;border-radius:999px;padding:4px 15px 4px 4px;font-weight:800;font-size:14.5px;color:var(--sub)}
.tabs label:hover{border-color:var(--c);color:var(--c)}
.ti{width:32px;height:32px;border-radius:50%;background:var(--t);display:grid;place-items:center;flex:none}
.nb{font-size:10.5px;font-weight:800;color:#fff;background:#B23A2A;border-radius:999px;padding:0 6px;line-height:17px;font-variant-numeric:tabular-nums}
.pane{display:none}
/*TOGGLE*/

/* 종합 브리핑 */
.brief{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 420px;align-items:end;border:1px solid var(--rule);
  border-radius:16px;overflow:hidden;background:linear-gradient(180deg,#fff 0,#F5F8F3 100%);margin:0 0 26px}
.brief .bl{padding:26px 0 28px 28px}
.brief .br{align-self:end}
.brief .br svg{height:150px}
.eyebrow{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;font-size:12px;font-weight:800;color:var(--d)}
.eyebrow .dt{background:var(--c);color:#fff;border-radius:6px;padding:2px 8px;font-variant-numeric:tabular-nums}
.hl1{font-size:29px;line-height:1.32;font-weight:800;letter-spacing:-1px;margin:10px 0 12px;word-break:keep-all;color:var(--ink)}
.src{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;font-size:12.5px;color:var(--sub)}
.tag{display:inline-block;font-size:11.5px;font-weight:800;border-radius:999px;padding:2px 10px;background:var(--c);color:#fff;white-space:nowrap}
.tag.l{background:#fff;color:var(--d);border:1px solid var(--c)}
.chipi{display:inline-flex;align-items:center;gap:5px;font-weight:800;color:var(--d)}

/* 부 제목 */
.part{display:flex;align-items:center;gap:10px;margin:36px 0 14px;padding-bottom:10px;border-bottom:2px solid var(--c)}
.part b{font-size:12.5px;font-weight:800;color:#fff;background:var(--c);border-radius:6px;padding:3px 8px;font-variant-numeric:tabular-nums}
.part span{font-size:21px;font-weight:800;letter-spacing:-.6px}
.part small{font-size:12px;color:var(--muted);margin-left:auto;text-align:right}

/* 품목 보드 */
.board{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}
.ib{display:flex;flex-direction:column;border:1px solid var(--rule);border-radius:14px;overflow:hidden;background:#fff;cursor:pointer;min-width:0}
.ib:hover{border-color:var(--c);box-shadow:0 6px 18px rgba(23,33,27,.07)}
.ib .top{display:flex;align-items:center;gap:10px;background:var(--t);padding:12px 14px;border-bottom:3px solid var(--c)}
.ib .art{width:46px;height:46px;border-radius:50%;background:#fff;display:grid;place-items:center;flex:none}
.ib .nm{font-size:18px;font-weight:800;letter-spacing:-.4px;color:var(--d);line-height:1.2}
.ib .nm small{display:block;font-size:11px;font-weight:700;color:var(--sub);letter-spacing:0;margin-top:2px}
.ib .top .nb{margin-left:auto}
.ib .hl{padding:12px 14px 2px;min-height:96px}
.ib .hl .tag{margin-bottom:6px}
.ib .hl p{margin:0;font-size:14.5px;font-weight:800;line-height:1.45;letter-spacing:-.3px;word-break:keep-all}
.ib .hs{padding:4px 14px 0;font-size:11.5px;color:var(--muted)}
.ib dl{display:grid;grid-template-columns:auto 1fr auto;gap:5px 8px;margin:12px 14px 0;padding-top:10px;border-top:1px solid var(--rule2);font-size:12.5px;align-items:baseline}
.ib dt{color:var(--sub);font-weight:600;white-space:nowrap}
.ib dd{margin:0;text-align:right;font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap}
.ib dd small{font-weight:600;color:var(--muted);margin-left:1px}
.ib dd.p{min-width:4.2em}
.ib .spw{margin:10px 14px 0}
.ib .spw .sp{height:34px}
.ib .cap2{font-size:10.5px;color:var(--muted);margin-top:3px;display:flex;justify-content:space-between}
.ib .go{margin-top:auto;padding:10px 14px;font-size:12.5px;font-weight:800;color:var(--c);border-top:1px solid var(--rule2);margin-top:12px}
.up{color:#B23A2A}.dn{color:#2E6DA4}

/* 카드 */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start;margin-bottom:16px}
.grid>*{min-width:0}
.g2{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px;align-items:start;margin-bottom:16px}
.card{background:#fff;border:1px solid var(--rule);border-radius:14px;padding:18px 22px 20px;min-width:0}
.span{grid-column:1/-1}
.sec{display:flex;align-items:center;gap:7px;font-size:11px;font-weight:800;letter-spacing:1.4px;color:var(--c)}
.sec:before{content:'';width:10px;height:10px;background:var(--c);border-radius:0 70% 0 70%;flex:none}
.h2{font-size:19px;font-weight:800;letter-spacing:-.6px;margin:5px 0 2px;word-break:keep-all}
.cap{font-size:12px;color:var(--muted);margin-bottom:10px;word-break:keep-all}
.cap a,.foot a{color:var(--c);font-weight:700;border-bottom:1px solid var(--rule)}
.lg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--sub);margin:0 0 6px}
.lg span{white-space:nowrap}
.lg i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-right:6px;vertical-align:3px}
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
.empty{background:var(--tint);color:var(--sub);font-size:13px;padding:14px 16px;border-radius:8px;word-break:keep-all}
.empty b{color:var(--ink)}

/* 품목 머리 */
.ihero{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 150px;gap:20px;align-items:center;
  background:var(--t);border-radius:18px;padding:26px 30px 34px;margin:0 0 8px;overflow:hidden}
.ihero .hill{position:absolute;left:0;bottom:0;width:100%;height:56px}
.ihero .tx,.ihero .art{position:relative;z-index:1}
.ihero .art{width:150px;height:150px;border-radius:50%;background:#fff;display:grid;place-items:center;box-shadow:0 0 0 10px rgba(255,255,255,.45)}
.ihero .nm{font-size:13px;font-weight:800;color:var(--d);letter-spacing:.5px}

/* KPI */
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:16px 0 4px}
.kpi{border:1px solid var(--rule);border-radius:12px;padding:13px 14px 12px;min-width:0;background:#fff}
.kl{font-size:12.5px;font-weight:800;color:var(--sub)}
.kv{font-size:25px;font-weight:800;letter-spacing:-.8px;line-height:1.2;margin-top:3px;font-variant-numeric:tabular-nums;white-space:nowrap}
.kv small{font-size:12.5px;font-weight:600;color:var(--muted);margin-left:2px;letter-spacing:0}
.kv.i{color:var(--green)}.kv.e{color:var(--org-d)}.kv.p{color:var(--c)}
.ks{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.ks .up,.ks .dn{font-weight:800}
.kpi .sp{height:30px;margin-top:9px}
.kpi .kc2{font-size:10.5px;color:var(--muted);margin-top:3px}

/* 표 */
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.t{width:100%;border-collapse:collapse;font-size:13px}
.t th{font-size:12px;font-weight:800;text-align:center;padding:8px 6px;border-bottom:1.5px solid var(--ink);white-space:nowrap;vertical-align:bottom;color:var(--sub)}
.t th.l,.t td.l{text-align:left}
.t td{padding:8px 6px;border-bottom:1px solid var(--rule2);white-space:nowrap;vertical-align:middle}
.t td.n{text-align:center;font-variant-numeric:tabular-nums}
.t td.n span{display:inline-block;text-align:right}
.t tbody tr:last-child td{border-bottom:1px solid #9FAEA3}
.t tr.ex{display:none}
.t td.w{white-space:normal;word-break:keep-all;min-width:180px;line-height:1.45}
.t .it{display:inline-flex;align-items:center;gap:7px;font-weight:800;line-height:1}
.t .it .ti{width:26px;height:26px}
.t td .sp{width:84px;height:24px;display:inline-block;vertical-align:middle}
.more{position:absolute;opacity:0;pointer-events:none}
.more:checked~.tw .t tr.ex{display:table-row}
.more:checked~ul li.ex{display:flex}
.mbtn{display:block;margin-top:12px;text-align:center;font-size:13px;font-weight:700;color:var(--c);border:1px solid var(--c);border-radius:999px;padding:7px;cursor:pointer;background:#fff}
.mbtn .c{display:none}.more:checked~.mbtn .o{display:none}.more:checked~.mbtn .c{display:inline}
details.dt{margin-top:12px;border-top:1px dashed var(--rule)}
details.dt summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-top:10px;font-size:12.5px;font-weight:800;color:var(--c)}
details.dt summary::-webkit-details-marker{display:none}
details.dt summary:before{content:'+';display:grid;place-items:center;width:18px;height:18px;border-radius:50%;background:var(--t);color:var(--c);font-size:14px;line-height:1}
details.dt[open] summary:before{content:'−'}
details.dt[open] summary{margin-bottom:8px}

/* 뉴스 */
.nl{list-style:none;margin:0;padding:0}
.nl li{display:flex;gap:10px;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--rule2)}
.nl li.ex{display:none}
.nl .d{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;min-width:36px}
.nl .d.new{color:#B23A2A;font-weight:800}
.nl .tt{font-size:14px;font-weight:700;line-height:1.45;word-break:keep-all}
.nl .tt a:hover{color:var(--c);text-decoration:underline}
.chip{display:inline-block;font-size:11px;font-weight:700;border-radius:4px;padding:0 6px;background:#F1F4F0;color:var(--sub);white-space:nowrap;margin-right:5px;vertical-align:1px}
.chip.i{color:#fff}

/* 임업관측 */
.kgs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.kh{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:800;color:var(--d);border-bottom:2px solid var(--c);padding-bottom:7px;margin-bottom:2px}
.kh i{font-style:normal;display:grid;place-items:center;width:22px;height:22px;border-radius:6px;background:var(--t);color:var(--c);font-size:12px}
.kl2{list-style:none;margin:0;padding:0}
.kl2 li{padding:9px 0;border-bottom:1px solid var(--rule2);word-break:keep-all}
.kl2 li b{display:block;font-size:14px;line-height:1.45}
.kl2 li span{display:block;font-size:12.5px;color:var(--sub);margin-top:3px;line-height:1.5}
.ko{list-style:none;margin:0;padding:0}
.ko>li{display:grid;grid-template-columns:40px minmax(0,1fr);gap:10px;padding:11px 0;border-bottom:1px solid var(--rule2)}
.ko .ti{width:38px;height:38px}
.ko .nm{font-size:14px;font-weight:800;color:var(--d)}
.ko .nm small{font-weight:600;color:var(--muted);font-size:11.5px;margin-left:6px}
.ko p{margin:4px 0 0;font-size:13px;line-height:1.45;word-break:keep-all;display:grid;grid-template-columns:44px 1fr;gap:6px}
.ko p i{font-style:normal;font-size:11px;font-weight:800;color:var(--sub);background:#F1F4F0;border-radius:4px;text-align:center;height:19px;line-height:19px;margin-top:1px}
.hsn{font-size:12px;color:var(--muted);margin-top:10px;word-break:keep-all}
.foot{margin:34px 0 0;padding:18px 0 40px;border-top:1px solid var(--rule);font-size:12px;color:var(--muted);line-height:1.7}
.foot b{color:var(--sub)}

@media(max-width:1180px){.board{grid-template-columns:repeat(3,minmax(0,1fr))}.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:980px){.grid,.g2{grid-template-columns:1fr}.kgs{grid-template-columns:1fr}
  .brief{grid-template-columns:1fr}.brief .br svg{height:96px}.brief .bl{padding:22px 20px 4px}
  .fresh{margin-left:0;justify-content:flex-start;width:100%}}
@media(max-width:640px){
  .hl1{font-size:22px}.kv{font-size:21px}.board{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .vr{display:none}.lg-sp{height:20px}.lg-kf{height:27px}.team .t2{font-size:16px}
  .card{padding:14px}.tabs label{padding:3px 12px 3px 3px;font-size:13.5px}.ti{width:28px;height:28px}
  .ihero{grid-template-columns:minmax(0,1fr) 78px;padding:18px 18px 26px;gap:12px}
  .ihero .art{width:78px;height:78px;box-shadow:0 0 0 5px rgba(255,255,255,.45)}
  .ihero .art svg{width:54px!important;height:54px!important}
  .ch-d{display:none}.ch-m{display:block}.part span{font-size:18px}.part small{display:none}
  table.t{font-size:12px}.t th{font-size:11px}.t th,.t td{padding-left:4px;padding-right:4px}
  .fresh span{font-size:11.5px;padding:3px 8px}
  .ib .hl{min-height:0}.ib .hs,.ib .go{display:none}.ib .spw .sp{height:26px}.ib .spw{margin-bottom:12px}.ib .top{padding:9px 12px}.ib .art{width:40px;height:40px}
  .kl2 li span{display:none}.kl2 li{padding:7px 0}.kpi .sp{height:24px}}
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



def ko_ym(ym):
    return '%s년 %d월호' % (ym[:4], int(ym[5:]))



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




# ── 품목 색 · 그림 도우미 ────────────────────────────────────────
def pal(key):
    return PAL.get(key, PAL['all'])


def pvars(key):
    c, t, d = pal(key)
    return '--c:%s;--t:%s;--d:%s' % (c, t, d)


def ti(key, size=24):
    return '<span class="ti" style="%s">%s</span>' % (pvars(key), icon(key, size))


def light(c, k=.62):
    return _mix(c, '#FFFFFF', k)


def series_cols(key):
    """품목 탭 여러 계열 색 : 품목색 → 숲 초록 → 앰버(품목색과 겹치면 이끼색) → 회색"""
    c = pal(key)[0]
    if key == 'shiitake':                              # 먹갈색은 숲 초록과 구분이 어려워 이끼색 · 앰버 · 황갈색으로
        return [c, '#7FA06E', '#B8742A', '#8A968D', '#D9B38C']
    third = '#7FA06E' if key in ('chestnut', 'persimmon', 'jujube') else '#B8742A'
    return [c, '#1F3D2B', third, '#8A968D', light(c, .45)]


LAB = {it['key']: it['label'] for it in ITEMS}


# ── 표기 도우미 ──────────────────────────────────────────────
def t_(kg):
    return (kg or 0) / 1000.0            # kg → 톤


def k_(usd):
    return (usd or 0) / 1000.0           # 달러 → 천 달러


def nd_for(vals):
    """작은 값 품목은 소수 1자리, 나머지는 정수 - 한 품목 안에서는 통일"""
    m = max([abs(v) for v in vals if v is not None] + [0])
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


def dots(ym):
    return ym.replace('-', '.')


def fold(label, inner):
    return '<details class="dt"><summary>%s</summary>%s</details>' % (label, inner)


# ── 조각 ──────────────────────────────────────────────────
def kpi(label, val, unit, sub, cls='', sp='', cap=''):
    return ('<div class="kpi"><div class="kl">%s</div><div class="kv %s">%s<small>%s</small></div>'
            '<div class="ks">%s</div>%s%s</div>' % (label, cls, val, unit, sub, sp, ('<div class="kc2">%s</div>' % cap) if cap else ''))


def news_list(key, items, today, show=SHOW_NEWS, item_chip=False):
    if not items:
        return '<div class="empty">최근 %d일 동안 수집된 기사가 없음</div>' % NEWS_DAYS
    fresh = {today.strftime('%Y-%m-%d'), (today - timedelta(days=1)).strftime('%Y-%m-%d')}
    li = []
    for i, n in enumerate(items[:40]):
        chip = ''
        if item_chip:
            k = n['item'] if n['item'] in LAB else 'all'
            chip = '<span class="chip i" style="background:%s">%s</span>' % (pal(k)[0], esc(LAB.get(n['item'], '정책')))
        new = n['date'] in fresh
        li.append('<li%s><span class="d%s">%s</span><span class="tt">%s<span class="chip">%s</span>'
                  '<a href="%s" target="_blank" rel="noopener">%s</a></span></li>'
                  % (' class="ex"' if i >= show else '', ' new' if new else '', n['date'][5:].replace('-', '.'), chip,
                     esc(n['cat']), esc(n['url']), esc(n['title'])))
    if len(items[:40]) > show:
        more = ('<label class="mbtn" for="nm-%s"><span class="o">기사 더보기 (%d건)</span><span class="c">접기</span></label>'
                % (key, len(items[:40]) - show))
        return '<input class="more" type="checkbox" id="nm-%s"><ul class="nl">%s</ul>%s' % (key, ''.join(li), more)
    return '<ul class="nl">%s</ul>' % ''.join(li)


def wait_card():
    return ('<div class="empty"><b>수출입 통계 수집 대기</b> - 저장소 Settings › Secrets › Actions에 '
            '<b>DATA_GO_KR_KEY</b>(공공데이터포털 「관세청_품목별 수출입실적(GW)」 인증키)를 등록하면 '
            '다음 자동 실행 때 2016년 1월부터 채워짐</div>')


def part(no, title, sub=''):
    return '<div class="part"><b>%02d</b><span>%s</span>%s</div>' % (no, title, ('<small>%s</small>' % sub) if sub else '')


def news_card(key, lab, news, today):
    return ('<div class="card span"><div class="sec">NEWS</div><div class="h2">%s 최근 뉴스</div>'
            '<div class="cap">최근 %d일 · 제목에 품목 핵심어가 있는 기사만 · 최신순 · 붉은 날짜는 오늘 · 어제 기사</div>%s</div>'
            % (esc(lab), NEWS_DAYS, news_list(key, news, today)))


def fresh_count(news, today):
    f = {today.strftime('%Y-%m-%d'), (today - timedelta(days=1)).strftime('%Y-%m-%d')}
    return sum(1 for n in news if n['date'] in f)


# ── 농경연 임업관측 ──────────────────────────────────────────
KGLYPH = {'생산·출하': '◆', '수출입': '⇄', '가격': '₩'}


def ts_cards(item_key, KT, kind=None):
    tabs = KT.get(item_key) or []
    if kind == 'trade':
        tabs = [t for t in tabs if re.search(r'수입|수출', t['title'])]
    elif kind == 'price':
        tabs = [t for t in tabs if not re.search(r'수입|수출', t['title'])]
    if not tabs:
        return ''
    cols = series_cols(item_key) if kind == 'price' else [IMP, EXP, '#7FA06E', '#8A968D']
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
        series = [{'name': sub or t['title'], 'color': cols[i], 'values': [sd.get(x) for x in xs]} for i, (sub, sd) in enumerate(subs)]
        lg = legend(series) if len(series) > 1 else ''
        chart = ('<div class="ch-d">%s</div><div class="ch-m">%s</div>'
                 % (lines(xs, series, nd), lines(xs, series, nd, w=360, h=230, fs=10.5)))
        yrs = sorted({int(x[:4]) for x in allym})[-3:][::-1]
        cells = []
        for sub, sd in subs:
            for y in yrs:
                row = [sd.get('%04d-%02d' % (y, m)) for m in range(1, 13)]
                if not any(v is not None for v in row):
                    continue
                cells.append((sub, y, [fmt(v, nd) if v is not None else '-' for v in row]))
        ws = [span_w([c[2][m] for c in cells]) for m in range(12)]
        body = ''.join('<tr><td class="l">%s</td>%s</tr>' % (esc(('%s ' % sub if sub else '') + '%d년' % y),
                                                            ''.join(numtd(v, ws[m]) for m, v in enumerate(row)))
                       for sub, y, row in cells)
        tb = ('<div class="tw"><table class="t"><thead><tr><th class="l">구분</th>%s</tr></thead><tbody>%s</tbody></table></div>'
              % (''.join('<th>%d월</th>' % m for m in range(1, 13)), body))
        o.append('<div class="card span"><div class="sec">KREI MONTHLY</div><div class="h2">%s</div>'
                 '<div class="cap">단위 : %s · %s ~ %s · 농경연 임업관측 월보 표에서 추출(같은 달은 최신 호 값 사용, 평년 행 제외)</div>'
                 '%s%s%s</div>' % (esc(t['title']), esc(t['unit'] or '-'), dots(xs[0]), dots(last), lg, chart,
                                    fold('최근 3년 월별 표 펼치기', tb)))
    return '<div class="grid">%s</div>' % ''.join(o)


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
        groups.append('<div class="kg"><div class="kh"><i>%s</i>%s</div><ul class="kl2">%s</ul></div>'
                      % (KGLYPH.get(sec, '◆'), sec.replace('·', ' · '), li))
    return ('<div class="grid"><div class="card span kc"><div class="sec">KREI OUTLOOK</div>'
            '<div class="h2">농경연 임업관측 %s</div><div class="cap">한국농촌경제연구원 임업관측 월보의 소제목(판단)과 첫 문장(근거) · '
            '<a href="%s" target="_blank" rel="noopener">원문 PDF</a> · <a href="%s" target="_blank" rel="noopener">월보 페이지</a></div>'
            '<div class="kgs">%s</div></div></div>' % (ko_ym(k['ym']), esc(k['pdf']), esc(k['view']), ''.join(groups)))


def krei_overview(K):
    li = []
    for it in ITEMS:
        k = K.get(it['key'])
        if not k:
            continue
        rows = []
        for sec, short in (('생산·출하', '생산'), ('수출입', '수출입'), ('가격', '가격')):
            hs = [h['head'] for h in k['heads'] if h['sec'] == sec]
            fc = [h for h in hs if '전망' in h or '듯' in h]
            if hs:
                rows.append('<p><i>%s</i><span>%s</span></p>' % (short, esc((fc or hs)[0])))
        li.append('<li style="%s">%s<div><div class="nm">%s<small><a href="%s" target="_blank" rel="noopener">%s</a></small></div>%s</div></li>'
                  % (pvars(it['key']), ti(it['key'], 28), it['label'], esc(k['pdf']), ko_ym(k['ym']), ''.join(rows)))
    if not li:
        return ''
    return ('<div class="card"><div class="sec">KREI OUTLOOK</div><div class="h2">농경연 임업관측 최신 전망</div>'
            '<div class="cap">품목별 최신 월보에서 절마다 전망 문장 우선 1개 · 월보명을 누르면 원문 PDF</div><ul class="ko">%s</ul></div>'
            % ''.join(li))


# ── 임산물생산조사 (품목색) ─────────────────────────────────────
def tile_map(vals, nd, total, key, TW=132, TH=74, G=6, fs=(13, 11, 17)):
    """시도 타일맵 - 생산량이 많을수록 짙은 품목색 (명암 단계)"""
    c, t0, d = pal(key)
    lo = _mix(t0, c, .12)
    mx = max(vals.values(), default=0) or 1
    o = ['<svg viewBox="0 0 %d %d" role="img">' % (4 * TW + 3 * G, 5 * TH + 4 * G)]
    for sd, (cx, cy) in TILE.items():
        v = vals.get(sd, 0) or 0
        x, y = cx * (TW + G), cy * (TH + G)
        if v > 0:
            t = (v / mx) ** 0.5
            fill = _mix(lo, d, t)
            fg = '#FFFFFF' if t > 0.42 else '#17211B'
            sh = '%s%%' % fmt(v / total * 100, 1) if total else ''
        else:
            fill, fg, sh = '#F5F6F4', '#A3ADA6', ''
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s"/>' % (x, y, TW, TH, fill))
        o.append('<text class="tn" x="%d" y="%d" fill="%s" style="font-size:%dpx">%s</text>' % (x + 8, y + fs[0] + 7, fg, fs[0], sd))
        if sh:
            o.append('<text class="ts" x="%d" y="%d" fill="%s" style="font-size:%dpx">%s</text>' % (x + TW - 7, y + fs[0] + 7, fg, fs[1], sh))
        o.append('<text class="tv" x="%d" y="%d" fill="%s" style="font-size:%dpx">%s</text>' % (x + 8, y + TH - 12, fg, fs[2], fmt(v, nd) if v > 0 else '-'))
    o.append('</svg>')
    return ''.join(o)


def prod_cards(item, lab, PD):
    c, t0, d = pal(item)
    subs = PD.get(item) or {}
    cards = []
    for sub in [k for k in ('', '생표고', '건표고') if k in subs]:
        dd = subs[sub]
        nat = {y: v for y, v in dd['nat'].items() if v > 0}
        if not nat:
            continue
        name = (sub or lab)
        trend = not (sub and subs.get('') and subs['']['nat'])
        yrs = sorted(nat)[-13:]
        ly = yrs[-1]
        nd = nd_for(nat.values())
        spp = [{'name': '생산량', 'color': c, 'light': light(c), 'values': [nat[y] for y in yrs]}]
        p1 = pct(nat[ly], nat.get(ly - 1))
        if trend:
            cards.append('<div class="card span"><div class="sec">PRODUCTION · 임산물생산조사</div><div class="h2">%s 연간 생산량 %d년 %s톤%s</div>'
                         '<div class="cap">단위 : 톤 · 산림청 임산물생산조사(연 1회, 다음 해 공표) · %d~%d년</div>%s</div>'
                         % (esc(name), ly, fmt(nat[ly], nd), (', 전년 대비 %s' % fmt_pct(p1)) if p1 is not None else '', yrs[0], ly,
                            dual([('%d년' % y, '') for y in yrs], spp, nd, w=1180, h=240, mob_labels=['%d년' % y for y in yrs])))
        sido = dd['sido'].get(ly, {})
        if sido:
            top_sd = sorted(sido.items(), key=lambda kv: -kv[1])[:3]
            cards.append('<div class="card"><div class="sec">BY PROVINCE · %d</div><div class="h2">시도별 %s 생산량</div>'
                         '<div class="cap">단위 : 톤 · 색이 진할수록 생산량이 많음 · 오른쪽 위는 전국 대비 비중 · 상위 : %s</div>%s</div>'
                         % (ly, esc(name), ' · '.join('%s %s%%' % (k, fmt(v / nat[ly] * 100, 1)) for k, v in top_sd),
                            '<div class="ch-d">%s</div><div class="ch-m">%s</div>'
                            % (tile_map(sido, nd, nat[ly], item), tile_map(sido, nd, nat[ly], item, TW=86, TH=62, G=4, fs=(13, 10, 15)))))
        sg = dd['sgg'].get(ly, {})
        if sg:
            top = sorted(sg.items(), key=lambda kv: -kv[1])[:10]
            mx = top[0][1] or 1
            cols = [_mix(light(c, .55), d, (v / mx) ** 0.7) for _, v in top]
            labels = ['%s %s' % (k[0], k[1]) for k, _ in top]
            ser1 = [{'name': '생산량', 'color': d, 'colors': cols, 'hl': [0], 'values': [v for _, v in top]}]
            hb = '<div class="ch-d">%s</div><div class="ch-m">%s</div>' % (hbars(labels, ser1, nd, w=560), hbars(labels, ser1, nd, w=360))
            share = sum(v for _, v in top) / nat[ly] * 100
            cards.append('<div class="card"><div class="sec">MAIN PRODUCING AREAS · %d</div><div class="h2">%s 주산지 상위 10개 시군구</div>'
                         '<div class="cap">단위 : 톤 · 막대 색이 진할수록 생산량이 많음 · 10곳이 전국의 %s%%</div>%s</div>'
                         % (ly, esc(name), fmt(share, 1), hb))
            ys5 = [y for y in sorted(dd['sgg']) if y > ly - 5]
            rows, cells = [], []
            for i, ((sd_, sg_), v) in enumerate(top):
                vs = [dd['sgg'][y].get((sd_, sg_)) for y in ys5]
                pv = dd['sgg'].get(ly - 1, {}).get((sd_, sg_))
                cells.append([str(i + 1), '%s %s' % (sd_, sg_)] + [fmt(x, nd) if x is not None else '-' for x in vs]
                             + [arrow(pct(v, pv)) if pv else '-', fmt(v / nat[ly] * 100, 1)])
            nc = len(ys5) + 2
            ws = [span_w([re.sub('<[^>]+>', '', c_[j + 2]) for c_ in cells]) for j in range(nc)]
            for c_ in cells:
                rows.append('<tr><td class="l">%s</td><td class="l"><b>%s</b></td>%s</tr>'
                            % (c_[0], esc(c_[1]), ''.join(numtd(c_[j + 2], ws[j]) for j in range(nc))))
            top5 = top[:5]
            yall = [y for y in sorted(dd['sgg']) if y > ly - 12]
            sc = series_cols(item)
            ser = [{'name': '%s %s' % k, 'color': sc[i], 'values': [dd['sgg'][y].get(k) for y in yall]} for i, (k, _) in enumerate(top5)]
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


def prod_nat_series(item, PD, n=8):
    subs = PD.get(item) or {}
    d = subs.get('') or subs.get('생표고')
    if not d:
        return [], []
    nat = {y: v for y, v in d['nat'].items() if v > 0}
    ys = sorted(nat)[-n:]
    return ys, [nat[y] for y in ys]


# ── 품목 탭 ────────────────────────────────────────────────
def item_hero(key, lab, pk):
    c, t0, d = pal(key)
    if pk:
        top = ('<div class="eyebrow"><span class="nm">%s 수급 레이더</span><span class="tag">핵심 이슈 · %s</span></div>'
               % (lab, esc(pk[0])))
        h1, src = pk[2], pk[1]
    else:
        top, h1, src = '<div class="eyebrow"><span class="nm">%s 수급 레이더</span></div>' % lab, '%s 수급 레이더' % lab, ''
    return ('<div class="ihero">%s<div class="tx">%s<h1 class="hl1">%s</h1>%s</div><div class="art">%s</div></div>'
            % (hill(_mix(t0, c, .10), _mix(t0, c, .18)), top, esc(h1),
               ('<div class="src">출처 · %s</div>' % esc(src)) if src else '', icon(key, 104)))


def item_pane(it, T, forms, P, ref, news, K, KT, PD, PICK, today):
    """품목 탭 : 머리 → ① 주요 수치 → ② 최근 뉴스 · 동향 → ③ 생산량 → ④ 수출입"""
    key, lab = it['key'], it['label']
    c, t0, dcol = pal(key)
    S = T.get(key, {})
    g = lambda ym: S.get(ym, {'exp_kg': 0, 'exp_usd': 0, 'imp_kg': 0, 'imp_usd': 0})
    o = ['<section class="pane p-%s" style="%s">' % (key, pvars(key))]
    o.append(item_hero(key, lab, PICK.get(key)))
    ply, plv, plp = prod_latest(key, PD)
    pys, pvs = prod_nat_series(key, PD)
    has_trade = bool(ref and S)

    # ① 주요 수치
    kp = []
    if ply:
        kp.append(kpi('연간 생산량 (%d년)' % ply, fmt(plv, nd_for([plv])), '톤', '전년 대비 %s' % arrow(plp), 'p',
                      spark(pvs, c, light(c)), '%d~%d년' % (pys[0], pys[-1]) if pys else ''))
    if has_trade:
        y, m = int(ref[:4]), int(ref[5:])
        allv = [t_(g(x)['imp_kg']) for x in S] + [t_(g(x)['exp_kg']) for x in S]
        nd = nd_for(allv)
        now, prev = g(ref), g(ym_add(ref, -12))
        ytd = lambda yy, f: sum(t_(g('%04d-%02d' % (yy, k))[f]) for k in range(1, m + 1))
        first_year = int(min(S)[:4])
        yrs = list(range(max(first_year, y - 7), y + 1))
        yi, yip, ye, yep = ytd(y, 'imp_kg'), ytd(y - 1, 'imp_kg'), ytd(y, 'exp_kg'), ytd(y - 1, 'exp_kg')
        up_ = lambda dd: (dd['imp_usd'] / dd['imp_kg']) if dd['imp_kg'] else None
        rng = '1~%d월' % m if m > 1 else '1월'
        ms13 = [ym_add(ref, -k) for k in range(12, -1, -1)]
        cap13 = '%s ~ %s 월별' % (dots(ms13[0])[2:], dots(ref)[2:])
        kp += [
            kpi('%s 수입 누계' % rng, fmt(yi, nd), '톤', '전년 동기 대비 %s' % arrow(pct(yi, yip)), 'i',
                spark([ytd(yy, 'imp_kg') for yy in yrs], IMP, IMP_L), '%d~%d년 같은 기간' % (yrs[0], y)),
            kpi('%s 수출 누계' % rng, fmt(ye, nd), '톤', '전년 동기 대비 %s' % arrow(pct(ye, yep)), 'e',
                spark([ytd(yy, 'exp_kg') for yy in yrs], EXP, EXP_L), '%d~%d년 같은 기간' % (yrs[0], y)),
            kpi('%d월 수입량' % m, fmt(t_(now['imp_kg']), nd), '톤', '전년 동월 대비 %s' % arrow(pct(t_(now['imp_kg']), t_(prev['imp_kg']))), 'i',
                spark([t_(g(x)['imp_kg']) for x in ms13], IMP, IMP_L), cap13),
            kpi('%d월 수출량' % m, fmt(t_(now['exp_kg']), nd), '톤', '전년 동월 대비 %s' % arrow(pct(t_(now['exp_kg']), t_(prev['exp_kg']))), 'e',
                spark([t_(g(x)['exp_kg']) for x in ms13], EXP, EXP_L), cap13),
            kpi('%d월 수입 단가' % m, fmt(up_(now), 2) if up_(now) else '-', '달러/kg' if up_(now) else '',
                ('전년 동월 %s달러' % fmt(up_(prev), 2)) if up_(prev) else '전년 동월 수입 없음', '',
                spark([up_(g(x)) for x in ms13], IMP, kind='line'), cap13)]
    o.append(part(1, '주요 수치', ('관세청 %s년 %d월 기준 · 생산은 %s년' % (ref[:4], int(ref[5:]), ply)) if has_trade and ply else ''))
    o.append('<div class="kpis">%s</div>' % ''.join(kp) if kp else '<div class="card">%s</div>' % wait_card())

    # ② 최근 뉴스 · 동향 : 임업관측 → 뉴스 → 가격
    o.append(part(2, '최근 뉴스 · 동향', '농경연 임업관측 · 뉴스 · 가격'))
    o.append(krei_card(key, K))
    o.append('<div class="grid">%s</div>' % news_card(key, lab, news, today))
    o.append(ts_cards(key, KT, kind='price'))

    # ③ 생산량
    pc = prod_cards(key, lab, PD)
    if pc:
        o.append(part(3, '생산량', '산림청 임산물생산조사 · 전국 추이 · 시도 · 주산지'))
        o.append('<div class="grid">%s</div>' % pc)

    # ④ 수출입
    o.append(part(4 if pc else 3, '수출입', '관세청 수출입실적 · 농경연 월보 수출입 표'))
    if not has_trade:
        o.append('<div class="grid"><div class="card span">%s</div></div>' % wait_card())
        o.append(ts_cards(key, KT, kind='trade'))
    else:
        ndk = nd_for([k_(g(x)['imp_usd']) for x in S] + [k_(g(x)['exp_usd']) for x in S])
        labs = [mlabel(x, i == 0) for i, x in enumerate(ms13)]
        mob = ['%s.%s' % (x[2:4], x[5:]) for x in ms13]
        si = [{'name': '수입량', 'color': IMP, 'light': IMP_L, 'values': [t_(g(x)['imp_kg']) for x in ms13]}]
        se = [{'name': '수출량', 'color': EXP, 'light': EXP_L, 'values': [t_(g(x)['exp_kg']) for x in ms13]}]
        o.append('<div class="grid">')
        o.append('<div class="card"><div class="sec">MONTHLY IMPORT</div><div class="h2">최근 13개월 수입량</div>'
                 '<div class="cap">단위 : 톤 · %s ~ %s</div>%s</div>' % (dots(ms13[0]), dots(ref), dual(labs, si, nd, mob_labels=mob)))
        o.append('<div class="card"><div class="sec">MONTHLY EXPORT</div><div class="h2">최근 13개월 수출량</div>'
                 '<div class="cap">단위 : 톤 · %s ~ %s</div>%s</div>' % (dots(ms13[0]), dots(ref), dual(labs, se, nd, mob_labels=mob)))
        sy = [{'name': '수입량', 'color': IMP, 'light': IMP_L, 'values': [ytd(yy, 'imp_kg') for yy in yrs]},
              {'name': '수출량', 'color': EXP, 'light': EXP_L, 'values': [ytd(yy, 'exp_kg') for yy in yrs]}]
        o.append('<div class="card span"><div class="sec">YEAR TO DATE</div><div class="h2">연도별 %s 누계 수출입량</div>'
                 '<div class="cap">단위 : 톤 · 해마다 같은 기간(%s)끼리 비교</div>%s%s</div>'
                 % (rng, rng, legend(sy), dual([('%d년' % yy, '') for yy in yrs], sy, nd, w=1180, h=250,
                                               mob_labels=['%d년' % yy for yy in yrs])))
        o.append('</div>')
        o.append(ts_cards(key, KT, kind='trade'))
        rows = [ym_add(ref, -k) for k in range(0, 24) if ym_add(ref, -k) >= min(S)]
        cols = []
        for x in rows:
            dd = g(x)
            cols.append([dots(x), fmt(t_(dd['imp_kg']), nd), fmt(k_(dd['imp_usd']), ndk),
                         fmt(up_(dd), 2) if up_(dd) else '-', fmt(t_(dd['exp_kg']), nd), fmt(k_(dd['exp_usd']), ndk),
                         fmt(k_(dd['exp_usd'] - dd['imp_usd']), ndk)])
        ws = [span_w([cc[j] for cc in cols]) for j in range(7)]
        body = ''.join('<tr><td class="l">%s</td>%s</tr>' % (cc[0], ''.join(numtd(cc[j], ws[j]) for j in range(1, 7))) for cc in cols)
        tb = ('<div class="tw"><table class="t"><thead><tr><th class="l">연월</th><th>수입량<br>(톤)</th>'
              '<th>수입액<br>(천 달러)</th><th>수입 단가<br>(달러/kg)</th><th>수출량<br>(톤)</th><th>수출액<br>(천 달러)</th>'
              '<th>무역수지<br>(천 달러)</th></tr></thead><tbody>%s</tbody></table></div>' % body)
        hsn = ' · '.join('%s %s' % (hs, esc(sk or fm)) for hs, (sk, fm) in sorted(forms.get(key, {}).items()))
        o.append('<div class="grid"><div class="card span"><div class="sec">MONTHLY TABLE</div><div class="h2">월별 수출입 상세</div>'
                 '<div class="cap">최근 %d개월 · 최신 월이 위 · 무역수지 = 수출액 - 수입액</div>%s'
                 '<div class="hsn">HS 부호 · 관세청 품목명 : %s</div></div></div>' % (len(cols), fold('월별 표 펼치기 (%d개월)' % len(cols), tb), hsn))
    o.append('</section>')
    return ''.join(o)


# ── 종합 탭 ────────────────────────────────────────────────
def board_card(it, T, ref, PD, pk, nnew):
    key, lab = it['key'], it['label']
    c, t0, d = pal(key)
    S = T.get(key, {})
    gg = lambda ym, f: (S.get(ym) or {}).get(f, 0) / 1000.0
    ply, plv, plp = prod_latest(key, PD)
    rows = []
    if ply:
        rows.append(('생산 %d년' % ply, fmt(plv, nd_for([plv])), plp))
    spw = ''
    if ref and S:
        y, m = int(ref[:4]), int(ref[5:])
        rng = '1~%d월' % m if m > 1 else '1월'
        ytd = lambda yy, f: sum(gg('%04d-%02d' % (yy, k), f) for k in range(1, m + 1))
        yi, yip, ye, yep = ytd(y, 'imp_kg'), ytd(y - 1, 'imp_kg'), ytd(y, 'exp_kg'), ytd(y - 1, 'exp_kg')
        nd = nd_for([yi, ye, yip, yep])
        rows.append(('수입 %s' % rng, fmt(yi, nd), pct(yi, yip)))
        rows.append(('수출 %s' % rng, fmt(ye, nd), pct(ye, yep)))
        ms13 = [ym_add(ref, -k) for k in range(12, -1, -1)]
        f, fl, col, lt = ('imp_kg', '수입', IMP, IMP_L) if yi >= ye else ('exp_kg', '수출', EXP, EXP_L)
        spw = ('<div class="spw">%s<div class="cap2"><span>월별 %s량</span><span>%s ~ %s</span></div></div>'
               % (spark([gg(x, f) for x in ms13], col, lt), fl, dots(ms13[0])[2:], dots(ref)[2:]))
    dl = ''.join('<dt>%s</dt><dd>%s<small>톤</small></dd><dd class="p">%s</dd>' % (a, b, arrow(p) if p is not None else '-')
                 for a, b, p in rows)
    hl = ('<div class="hl"><span class="tag">%s</span><p>%s</p></div><div class="hs">%s</div>' % (esc(pk[0]), esc(pk[2]), esc(pk[1]))
          if pk else '<div class="hl"><p>%s 수급 레이더</p></div>' % lab)
    return ('<label class="ib" for="t-%s" style="%s"><span class="top"><span class="art">%s</span>'
            '<span class="nm">%s</span>%s</span>%s<dl>%s</dl>%s<span class="go">%s 상세 보기 ›</span></label>'
            % (key, pvars(key), icon(key, 36), lab, ('<span class="nb">새 뉴스 %d</span>' % nnew) if nnew else '',
               hl, dl, spw, lab))


def summary_pane(T, P, ref, allnews, K, PICK, PD, news, today):
    """종합 탭 : 브리핑 → ① 주요 수치(품목 보드) → ② 최근 뉴스 · 동향 → ③ 생산량 → ④ 수출입"""
    PD = PD or {}
    o = ['<section class="pane p-all" style="%s">' % pvars('all')]
    cand = [(k, v) for k, v in (PICK or {}).items() if v]
    best = max(cand, key=lambda kv: kv[1][3], default=None)
    date = '%s (%s)' % (today.strftime('%Y.%m.%d'), WD[today.weekday()])
    if best:
        bk, bv = best
        o.append('<div class="brief"><div class="bl"><div class="eyebrow"><span class="dt">%s</span>임산물 수급 데일리 브리핑 · 오늘의 핵심 이슈</div>'
                 '<h1 class="hl1">%s</h1><div class="src"><span class="chipi" style="%s">%s%s</span><span class="tag l">%s</span>출처 · %s</div></div>'
                 '<div class="br">%s</div></div>'
                 % (date, esc(bv[2]), pvars(bk), icon(bk, 22), LAB[bk], esc(bv[0]), esc(bv[1]), ridge()))
    else:
        o.append('<div class="brief"><div class="bl"><div class="eyebrow"><span class="dt">%s</span>임산물 수급 데일리 브리핑</div>'
                 '<h1 class="hl1">임산물 5개 품목 수출입 · 생산 · 뉴스 모니터링</h1></div><div class="br">%s</div></div>' % (date, ridge()))
    y = m = None
    if ref:
        y, m = int(ref[:4]), int(ref[5:])
    rng = ('1~%d월' % m if m > 1 else '1월') if m else ''

    # ① 주요 수치 : 품목 보드
    ply0 = max([prod_latest(it['key'], PD)[0] or 0 for it in ITEMS]) or None
    o.append(part(1, '주요 수치', ('품목별 핵심 이슈 · 생산 %s년 · 수출입 %s년 %d월 누계 · 카드를 누르면 품목 상세' % (ply0, y, m)) if (ply0 and m) else ''))
    o.append('<div class="board">%s</div>' % ''.join(
        board_card(it, T, ref, PD, (PICK or {}).get(it['key']), fresh_count(news[it['key']], today)) for it in ITEMS))

    # ② 최근 뉴스 · 동향
    o.append(part(2, '최근 뉴스 · 동향', '임업 정책 · 품목 뉴스 · 농경연 임업관측'))
    o.append('<div class="g2"><div class="card"><div class="sec">NEWS</div><div class="h2">임업 · 임산물 최근 뉴스</div>'
             '<div class="cap">최근 %d일 · 임업 정책과 5개 품목 기사 통합 · 최신순 · 붉은 날짜는 오늘 · 어제 기사</div>%s</div>%s</div>'
             % (NEWS_DAYS, news_list('all', allnews, today, 10, item_chip=True), krei_overview(K)))

    # ③ 생산량 : 품목별 최근 5년 전국 생산량 + 추이 + 1위 주산지
    prow = []
    yrs_all = sorted({yy for it in ITEMS for sub in (PD.get(it['key']) or {}).values() for yy, v in sub['nat'].items() if v})[-5:]
    for it in ITEMS:
        subs = PD.get(it['key']) or {}
        d = subs.get('') or subs.get('생표고')
        if not d:
            continue
        vals = [d['nat'].get(yy) for yy in yrs_all]
        ly, lv, lp = prod_latest(it['key'], PD)
        dm = subs.get('') if subs.get('') and subs['']['sgg'] else subs.get('생표고')
        top = ''
        if dm and dm['sgg']:
            yy = max(dm['sgg'])
            (sd_, sg_), tv = max(dm['sgg'][yy].items(), key=lambda kv: kv[1])
            nat_ = dm['nat'].get(yy) or 0
            top = '%s %s (%s%%)' % (sd_, sg_, fmt(tv / nat_ * 100, 1)) if nat_ else '%s %s' % (sd_, sg_)
        c = pal(it['key'])[0]
        prow.append([it['key']] + [fmt(v, 0) if v else '-' for v in vals] + [arrow(lp) if ly else '-',
                    spark(vals, c, light(c)), esc(top)])
    if prow:
        nc = len(yrs_all) + 1
        ws = [span_w([re.sub('<[^>]+>', '', r[j + 1]) for r in prow]) for j in range(nc)]
        body = ''.join('<tr><td class="l"><span class="it">%s%s</span></td>%s<td>%s</td><td class="l">%s</td></tr>'
                       % (ti(r[0], 20), LAB[r[0]], ''.join(numtd(r[j + 1], ws[j]) for j in range(nc)), r[-2], r[-1]) for r in prow)
        o.append(part(3, '생산량', '산림청 임산물생산조사'))
        o.append('<div class="grid"><div class="card span"><div class="sec">PRODUCTION</div><div class="h2">품목별 연간 생산량</div>'
                 '<div class="cap">단위 : 톤 · 표고버섯은 생 · 건 합계 · 추이는 %d~%d년 · 1위 주산지는 최근 연도 시군구와 전국 대비 비중</div>'
                 '<div class="tw"><table class="t"><thead><tr><th class="l">품목</th>%s<th>전년<br>대비</th><th>추이</th><th class="l">1위 주산지</th>'
                 '</tr></thead><tbody>%s</tbody></table></div></div></div>'
                 % (yrs_all[0], yrs_all[-1], ''.join('<th>%d년</th>' % yy for yy in yrs_all), body))

    # ④ 수출입
    o.append(part(4 if prow else 3, '수출입', '관세청 수출입실적'))
    if not ref:
        o.append('<div class="grid"><div class="card span">%s</div></div>' % wait_card())
    else:
        last12 = [ym_add(ref, -k) for k in range(11, -1, -1)]
        rows, i12, e12 = [], [], []
        for it in ITEMS:
            S = T.get(it['key'], {})
            g = lambda ym: S.get(ym, {'exp_kg': 0, 'exp_usd': 0, 'imp_kg': 0, 'imp_usd': 0})
            now, prev = g(ref), g(ym_add(ref, -12))
            rows.append([it['key'], fmt(t_(now['imp_kg']), 1), arrow(pct(t_(now['imp_kg']), t_(prev['imp_kg']))),
                         fmt(t_(now['exp_kg']), 1), arrow(pct(t_(now['exp_kg']), t_(prev['exp_kg'])))])
            i12.append((it['key'], sum(t_(g(x)['imp_kg']) for x in last12)))
            e12.append((it['key'], sum(t_(g(x)['exp_kg']) for x in last12)))
        ws = [span_w([re.sub('<[^>]+>', '', r[j]) for r in rows]) for j in range(5)]
        body = ''.join('<tr><td class="l"><span class="it">%s%s</span></td>%s</tr>'
                       % (ti(r[0], 20), LAB[r[0]], ''.join(numtd(r[j], ws[j]) for j in range(1, 5))) for r in rows)
        o.append('<div class="grid"><div class="card span"><div class="sec">TRADE · %d월</div><div class="h2">품목별 %d월 수출입</div>'
                 '<div class="cap">단위 : 톤 · 증감률은 전년 같은 달 대비 · 올해 누계는 ① 품목 보드 참고</div><div class="tw"><table class="t"><thead>'
                 '<tr><th class="l">품목</th><th>%d월<br>수입량</th><th>전년<br>동월 대비</th><th>%d월<br>수출량</th><th>전년<br>동월 대비</th></tr></thead>'
                 '<tbody>%s</tbody></table></div></div>' % (m, m, m, m, body))
        for title, arr, sec in (('최근 12개월 수입량', i12, 'IMPORT'), ('최근 12개월 수출량', e12, 'EXPORT')):
            arr = sorted(arr, key=lambda x: -x[1])              # 값이 큰 품목이 위
            nd = nd_for([v for _, v in arr])
            ser = [{'name': title, 'color': '#1F3D2B', 'colors': [pal(k)[0] for k, _ in arr], 'hl': list(range(len(arr))),
                    'values': [v for _, v in arr]}]
            o.append('<div class="card"><div class="sec">%s · 12 MONTHS</div><div class="h2">%s</div>'
                     '<div class="cap">단위 : 톤 · %s ~ %s 합계 · 막대는 품목색</div>%s</div>'
                     % (sec, title, dots(last12[0]), dots(ref), hbars([LAB[k] for k, _ in arr], ser, nd, w=560)))
        o.append('</div>')
    o.append('</section>')
    return ''.join(o)


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
        c = pal(k)[0]
        tog.append('#t-%s:checked~.wrap .tabs label[for=t-%s]{background:%s;border-color:%s;color:#fff}' % (k, k, c, c))
        tog.append('#t-%s:checked~.wrap .tabs label[for=t-%s] .ti{background:#fff}' % (k, k))
        tog.append('#t-%s:checked~.wrap .p-%s{display:block}' % (k, k))
    css = CSS.replace('/*TOGGLE*/', '\n'.join(tog))

    K = load_krei(con)
    KT = load_krei_ts(con)
    PD = load_prod_db(con)
    PICK = {}
    for it in ITEMS:
        PICK[it['key']] = pick_headline(it['label'], trade_cand(it['key'], it['label'], T, ref), K.get(it['key']),
                                        news[it['key']], today)
    body = [summary_pane(T, P, ref, allnews, K, PICK, PD, news, today)]
    body += [item_pane(it, T, forms, P, ref, news[it['key']], K, KT, PD, PICK, today) for it in ITEMS]
    radios = ''.join('<input class="tg" type="radio" name="tg" id="t-%s"%s>' % (k, ' checked' if k == 'all' else '') for k in keys)
    ntoday = fresh_count(allnews, today)
    tabs = '<nav class="tabs">%s</nav>' % ''.join(
        '<label for="t-%s" style="%s">%s%s%s</label>' % (k, pvars(k), ti(k, 24), '종합' if k == 'all' else LAB[k],
                                                          ('<span class="nb">%d</span>' % fresh_count(news[k], today))
                                                          if k != 'all' and fresh_count(news[k], today) else '')
        for k in keys)
    kym = max([v['ym'] for v in K.values()] or [''])
    ply0 = max([prod_latest(it['key'], PD)[0] or 0 for it in ITEMS]) or None
    fresh = ''.join('<span%s><em>%s</em><b>%s</b></span>' % (cl, a_, b_) for cl, a_, b_ in (
        ('', '수출입', dots(ref) if ref else '수집 대기'),
        ('', '임업관측', ('%s년 %d월호' % (kym[:4], int(kym[5:]))) if kym else '-'),
        ('', '생산조사', ('%d년' % ply0) if ply0 else '-'),
        (' class="nw"', '새 뉴스', '%s건' % fmt(ntoday)),
        ('', '갱신', today.strftime('%m.%d %H:%M'))))
    ribbon = '<div class="ribbon">%s</div>' % ''.join('<i style="background:%s"></i>' % pal(k)[0] for k in keys)
    err = ('<br>수출입 수집 알림 : %s' % esc(meta['trade_err'])) if meta.get('trade_err') else ''
    doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">'
           '<title>임산물 수급 레이더</title>'
           '<meta name="description" content="밤 · 호두 · 대추 · 표고버섯 · 떫은감 월별 수출입, 연간 생산량, 임업관측, 최근 뉴스">%s</head><body>'
           '<header class="mast"><div class="in"><div class="logos"><img class="lg-sp" src="assets/logo_southernpost.png" alt="서던포스트">'
           '<span class="x">×</span><img class="lg-kf" src="assets/logo_kofpi.png" alt="한국임업진흥원"></div><div class="vr"></div>'
           '<div class="team"><span class="t1">품목별 수출입 · 가격 · 전망 · 뉴스 데일리</span><span class="t2">임산물 수급 레이더</span></div>'
           '<div class="fresh">%s</div></div>%s</header>%s<main class="wrap">%s%s'
           '<footer class="foot"><b>자료</b> 관세청 수출입무역통계(공공데이터포털 「품목별 수출입실적」 API, 중량 · 금액 월별) · '
           '한국농촌경제연구원 임업관측 월보(매월 초) · 산림청 임산물생산조사(연간) · 네이버 뉴스 · Google 뉴스<br>'
           '<b>갱신</b> 매일 07:00 자동 · 수출입은 최근 14개월 재수집으로 잠정치 수정 반영 · 새 임업관측 · 생산조사는 공표 뒤 첫 실행에 반영 · '
           '월별 수치는 HS 부호 합산(밤 · 표고버섯은 냉동 · 조제품 포함, 농경연 관측 월보와 같은 범위)%s<br>'
           '<b>(주)서던포스트</b> · 최근 뉴스 수집 %s · 최근 수출입 수집 %s</footer></main></body></html>'
           % (css, fresh, ribbon, radios, tabs, ''.join(body), err, meta.get('news_run', '-'), meta.get('trade_run', '-')))
    doc = doc.replace('—', '-').replace('–', '-')
    doc = re.sub(r'<ul class="dek">.*?</ul>', '', doc, flags=re.S)
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
