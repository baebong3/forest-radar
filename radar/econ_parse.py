# -*- coding: utf-8 -*-
"""임가경제조사 보고서 텍스트(data/econ_txt/econ_연도.txt.gz) → 임가 경제 시계열 · 최신 특성별 지표

  - 보고서 본문 「주요 지표 동향」 「임가소득 동향」 「임업소득 동향」 「임가와 농·어가 가구소득」 「임가자산 동향」
    「임가부채 동향」 표는 최근 5개 연도를 함께 싣고 있어, 해마다 받은 보고서를 겹쳐 2011년 이후 시계열을 만듦
    (같은 연도는 가장 최근 보고서 값 사용)
  - 최신 보고서의 「경영 업종별 · 경영주 연령별 · 지역별 주요지표」 표는 단면 비교용으로 따로 읽음
  - 단위 : 천 원(비율은 %)
"""
import gzip, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(ROOT, 'data', 'econ_txt')

NUM = r'-?\d[\d,]*(?:\.\d+)?'
# (지표 키, 표 제목, 행 이름, 구성비 열 있음)
SERIES = [
    ('income', '임가소득 동향', '임가소득', True), ('ordinary', '임가소득 동향', '경상소득', True),
    ('forest', '임가소득 동향', '임업소득', True), ('nonforest', '임가소득 동향', '임업외소득', True),
    ('transfer', '임가소득 동향', '이전소득', True), ('irregular', '임가소득 동향', '비경상소득', True),
    ('expense', '주요 지표 동향', '가계지출', False), ('surplus', '주요 지표 동향', '임가잉여액', False),
    ('debt', '주요 지표 동향', '임가부채', False),
    ('revenue', '임업소득 동향', '임업총수입', False), ('cost', '임업소득 동향', '임업경영비', False),
    ('farm', '임가와 농', '농가소득', False), ('fish', '임가와 농', '어가소득', False),
    ('asset', '임가자산 동향', '임가자산', False), ('debt_f', '임가부채 동향', '임업용부채', False),
]
LABEL = {'income': '임가소득', 'ordinary': '경상소득', 'forest': '임업소득', 'nonforest': '임업외소득', 'transfer': '이전소득',
         'irregular': '비경상소득', 'expense': '가계지출', 'surplus': '임가잉여액', 'debt': '임가부채', 'revenue': '임업총수입',
         'cost': '임업경영비', 'farm': '농가소득', 'fish': '어가소득', 'asset': '임가자산', 'debt_f': '임업용 부채'}


def years():
    return sorted(int(f[5:9]) for f in os.listdir(TXT) if re.match(r'^econ_\d{4}\.txt\.gz$', f)) if os.path.isdir(TXT) else []


def text(y):
    return gzip.open(os.path.join(TXT, 'econ_%d.txt.gz' % y), 'rt', encoding='utf-8').read()


def nums(s):
    return [float(x.replace(',', '')) for x in re.findall(NUM, s)]


def table_at(lines, title):
    """본문 표 제목 줄 위치들 (목차의 「… 41」 줄은 뺌)"""
    out = []
    for i, l in enumerate(lines):
        if '표' in l and title.replace(' ', '') in l.replace(' ', '') and not re.search(r'[\s·.]\d{1,3}\s*$', l):
            out.append(i)
    return out


def read_series(t):
    """보고서 한 권 → {지표: {연도: 값}}"""
    lines = t.split('\n')
    res = {}
    for key, title, row, share in SERIES:
        for i in table_at(lines, title):
            yrs = None
            for l in lines[i:i + 60]:
                ys = [int(x) for x in re.findall(r'(20\d\d)\s*년', l)]
                if len(ys) >= 3 and yrs is None:
                    yrs = sorted(set(ys))
                    continue
                if yrs is None:
                    continue
                lab = re.sub(r'[\s()A-Za-z\d,.\-:·]', '', l.split(re.search(NUM, l).group(0))[0]) if re.search(NUM, l) else ''
                lab = lab.replace('[', '').replace(']', '')
                if lab != row:
                    continue
                v = nums(l[l.find(re.search(NUM, l).group(0)):])
                if share and len(v) >= 2 * len(yrs):
                    v = v[0:2 * len(yrs):2]
                else:
                    v = v[:len(yrs)]
                if len(v) == len(yrs):
                    res[key] = dict(zip(yrs, v))
                break
            if key in res:
                break
    return res


def series():
    """모든 보고서를 겹친 시계열 {지표: {연도: 천 원}} (같은 연도는 나중 보고서 우선)"""
    out = {}
    for y in years():
        try:
            r = read_series(text(y))
        except Exception:
            continue
        for k, d in r.items():
            out.setdefault(k, {}).update(d)
    return out


CROSS = {
    'type': ('경영 업종별 주요지표', ['전국', '육림 · 목재수확업', '채취업', '밤 재배업', '감 재배업', '수실류 재배업', '버섯 재배업', '조경재업', '기타 재배업']),
    'age': ('경영주 연령별 주요지표', ['전국', '49세 이하', '50대', '60대', '70세 이상']),
    'region': ('지역별 주요지표', ['전국', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '특 · 광역시']),
}
CROWS = ['임가소득', '임업소득', '임업의존도', '가계지출', '임가자산', '임가부채', '부채/자산']


def cross(y):
    """최신 보고서 특성별 표 → {'type': {'cols': [...], '임가소득': [...], ...}, ...}  열 수가 안 맞으면 뺌"""
    lines = text(y).split('\n')
    out = {}
    for k, (title, cols) in CROSS.items():
        for i in table_at(lines, title):
            d = {}
            for l in lines[i:i + 40]:
                m = re.match(r'^\s*([가-힣/]+)\s+(' + NUM + r'.*)$', l)
                if not m:
                    continue
                lab = m.group(1).replace(' ', '')
                v = nums(m.group(2))
                if lab in CROWS and lab not in d and len(v) == len(cols):
                    d[lab] = v
            if len(d) >= 5:
                d['cols'] = cols
                out[k] = d
                break
    return out


if __name__ == '__main__':
    S = series()
    for k in LABEL:
        d = S.get(k, {})
        print('%-10s %s' % (LABEL[k], ' '.join('%d:%s' % (y, '{:,.0f}'.format(v)) for y, v in sorted(d.items()))))
    ly = years()[-1]
    for k, d in cross(ly).items():
        print(k, d['cols'], {r: d[r] for r in ('임가소득', '임업소득')})
