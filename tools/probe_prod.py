# -*- coding: utf-8 -*-
"""임산물생산조사 첨부 목록 · 엑셀 받기 (1회성)"""
import os, json, urllib.request, urllib.parse, http.cookiejar
OUT = 'probe/prod3'; os.makedirs(OUT, exist_ok=True)
B = 'https://kfss.forest.go.kr/stat'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124'), ('Accept-Language', 'ko-KR'), ('X-Requested-With', 'XMLHttpRequest')]
def get(u):
    with op.open(u, timeout=60) as r:
        return r.read(), r.headers.get('Content-Type', ''), r.headers.get('Content-Disposition', '')
get(B + '/ptl/article/articleList.do?curMenu=9847&bbsId=ptlPdsMntProdReq')
log = {}
for seq in ('2664', '2550'):
    b, _, _ = get(B + '/ptl/article/selectArticleFileList.do?' + urllib.parse.urlencode({'workPath': 'Article', 'workSeq': seq}))
    d = json.loads(b)
    files = d.get('data') or []
    log[seq] = [{k: f.get(k) for k in ('fileSeq', 'fileNm', 'fileSize', 'fileExt')} for f in files]
    for f in files:
        nm = f.get('fileNm') or ''
        if nm.lower().endswith(('.xlsx', '.xls', '.csv')) and (f.get('fileSize') or 0) < 25_000_000:
            fb, ct, cd = get(B + '/ptl/article/articleFileDown.do?' + urllib.parse.urlencode({'fileSeq': f['fileSeq'], 'workSeq': seq}))
            open('%s/%s_%s' % (OUT, seq, nm.replace('/', '_')), 'wb').write(fb)
json.dump(log, open(OUT + '/log.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(log, ensure_ascii=False, indent=1, default=str))
