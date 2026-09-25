# -*- coding: utf-8 -*-
"""KREI 임업관측 점검 3차 - 품목별 목록 · 최신 호 상세 · PDF 원본 저장"""
import os, re, json, html, urllib.request, urllib.error
OUT = 'probe'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9'}
BASE = 'https://www.krei.re.kr/krei/page/21'
CT = {'0101': '밤', '0102': '표고버섯', '0103': '대추', '0104': '떫은감', '0105': '0105', '0107': '호두'}

def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read()

log = []
for c, nm in CT.items():
    rec = {'ctgry': c, 'name': nm}
    try:
        t = get(BASE + '?cmd=list&ctgry=' + c).decode('utf-8', 'ignore')
        open('%s/list_%s.html' % (OUT, c), 'w', encoding='utf-8').write(t)
        items = re.findall(r'href="\?cmd=view&(?:amp;)?ctgry=(\d+)&(?:amp;)?yr=(\d+)&(?:amp;)?mm=(\d+)"[^>]*title="([^"]*)".*?href="(/attach/observ/[^"]+\.pdf)"', t, re.S)
        rec['n'] = len(items); rec['top'] = items[:4]
        if items:
            _, yr, mm, title, pdf = items[0]
            v = get(BASE + '?cmd=view&ctgry=%s&yr=%s&mm=%s' % (c, yr, mm)).decode('utf-8', 'ignore')
            open('%s/view_%s.html' % (OUT, c), 'w', encoding='utf-8').write(v)
            if c in ('0101', '0102', '0104'):
                b = get('https://www.krei.re.kr' + pdf)
                open('%s/pdf_%s.pdf' % (OUT, c), 'wb').write(b)
                rec['pdf_bytes'] = len(b)
    except Exception as ex:
        rec['error'] = repr(ex)
    log.append(rec)
json.dump(log, open(OUT + '/log.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(log, ensure_ascii=False, indent=1))
