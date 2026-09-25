# -*- coding: utf-8 -*-
"""옛 생산조사 보고서 서식 점검 (1회성) - 연도별로 '부여' 주변 200줄만 저장"""
import os, re, sys
sys.path.insert(0, 'radar')
import collect_prod as cp
OUT = 'probe/old'; os.makedirs(OUT, exist_ok=True)
op = cp.opener()
arts = cp.articles(op)
for y in (2021, 2019, 2016, 2013):
    seq, title = arts[y]
    try:
        t = cp.pdf_text(op, seq) or ''
    except Exception as ex:
        open('%s/%d.txt' % (OUT, y), 'w').write('ERR %r' % ex); continue
    lines = t.split('\n')
    idx = [i for i, l in enumerate(lines) if '부여' in l]
    head = '\n'.join(lines[:120])
    seg = []
    for i in idx[:6]:
        seg.append('\n'.join(lines[max(0, i - 15):i + 60]))
    open('%s/%d.txt' % (OUT, y), 'w', encoding='utf-8').write('LINES %d  부여 hits %d\n\n' % (len(lines), len(idx)) + head + '\n=====\n' + '\n-----\n'.join(seg))
    print(y, len(lines), len(idx))
