# -*- coding: utf-8 -*-
"""임산물생산조사 보고서 PDF 텍스트를 data/prod_txt/연도.txt.gz 로 보관 (생산지도용 전 품목 파싱 원자료)"""
import gzip, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prod import opener, articles, pdf_text

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'prod_txt')
os.makedirs(OUT, exist_ok=True)
years = [int(y) for y in sys.argv[1:]] or [2022, 2023, 2024]
op = arts = None
for i in range(3):
    try:
        op = opener(); arts = articles(op); break
    except Exception as ex:
        print('목록 재시도', ex); time.sleep(20)
print('보고서 연도 :', sorted(arts))
for y in sorted(set(years) | {max(arts)}):
    p = os.path.join(OUT, '%d.txt.gz' % y)
    if y not in arts or os.path.exists(p):
        continue
    for i in range(3):
        try:
            t = pdf_text(op, arts[y][0])
            gzip.open(p, 'wt', encoding='utf-8').write(t)
            print(y, len(t)); break
        except Exception as ex:
            print(y, '재시도', ex); time.sleep(20)
