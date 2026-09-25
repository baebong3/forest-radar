# -*- coding: utf-8 -*-
"""산림임업통계플랫폼 임산물생산조사 게시판 목록 · 상세 · 첨부 점검 (1회성)"""
import os, re, json, urllib.request, urllib.parse, http.cookiejar
OUT = 'probe/prod2'; os.makedirs(OUT, exist_ok=True)
B = 'https://kfss.forest.go.kr/stat'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124'), ('Accept-Language', 'ko-KR'),
                 ('X-Requested-With', 'XMLHttpRequest')]
def get(u):
    with op.open(u, timeout=40) as r:
        return r.read(), r.headers.get('Content-Type', ''), r.headers.get('Content-Disposition', '')
log = {}
get(B + '/ptl/article/articleList.do?curMenu=9847&bbsId=ptlPdsMntProdReq')
q = urllib.parse.urlencode({'bbsId': 'ptlPdsMntProdReq', 'curMenu': '9847', 'pageIndex': 1, 'pageUnit': 30, 'recordCountPerPage': 30})
b, ct, _ = get(B + '/ptl/article/selectArticleList.do?' + q)
open(OUT + '/list.json', 'wb').write(b)
try:
    d = json.loads(b)
    rows = d.get('data') or []
    log['rows'] = [{k: r.get(k) for k in list(r)[:30]} for r in rows[:30]]
except Exception as ex:
    log['list_err'] = repr(ex) + ' ' + b[:300].decode('utf-8', 'ignore')
    rows = []
for r in rows[:3]:
    seq = r.get('articleSeq') or r.get('seq') or r.get('nttId')
    try:
        b2, _, _ = get(B + '/ptl/article/articleDtl.do?' + urllib.parse.urlencode({'bbsId': 'ptlPdsMntProdReq', 'curMenu': '9847', 'articleSeq': seq}))
        t = b2.decode('utf-8', 'ignore')
        open('%s/dtl_%s.html' % (OUT, seq), 'w', encoding='utf-8').write(t)
        log['dtl_%s' % seq] = sorted(set(re.findall(r'[\'"]([^\'"]*(?:[Ff]ile|[Dd]own)[^\'"]*)[\'"]', t)))[:40]
    except Exception as ex:
        log['dtl_err_%s' % seq] = repr(ex)
json.dump(log, open(OUT + '/log.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(log, ensure_ascii=False, indent=1, default=str)[:6000])
