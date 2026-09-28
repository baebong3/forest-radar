# -*- coding: utf-8 -*-
"""임산물생산조사 보고서 텍스트(data/prod_txt/연도.txt.gz) → 전 품목 × 시군구 생산량 · 생산액

  - 보고서 부록은 시도 · 시군구 · 국유림관리소마다 같은 서식(2쪽, 좌우 2단)으로 전 품목을 싣고 있음
  - 줄마다 「품목명 단위 생산량 생산액」 묶음을 찾아 좌 · 우 단 순서대로 읽음
  - 세로로 인쇄된 분류 글자(조 · 경 · 수 · 실 …)가 품목명 앞에 붙어 읽히는 경우는 NAME_FIX 로 바로잡음
  - 같은 이름이 분류마다 다시 나오는 조경재(소나무 · 해송 · 향나무 · 소사나무 · 철쭉)는 나온 차례로 분류를 가름
"""
import gzip, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(ROOT, 'data', 'prod_txt')

U = r'(kg|그루|㎡|ℓ|톤|㎥|ha)'
RX = re.compile(r'([가-힣()]+(?:[ ]+[가-힣()]+)*)\s+' + U + r'\s+([\d,]+|-)\s+([\d,]+|-)')

NAME_FIX = {'조기타관목류': '기타관목류', '경향나무': '향나무', '재소사나무': '소사나무', '재소소나무': '소나무', '완소나무': '소나무',
            '잔한지형잔디': '한지형잔디', '디난지형잔디': '난지형잔디', '실개암': '개암', '실감': '떫은감', '실떫은감': '떫은감',
            '나참나물': '참나물', '액기타수액': '기타수액', '수기타수액': '기타수액', '재사료': '사료', '연흑탄': '흑탄',
            '료장작': '장작', '수칡뿌리': '칡뿌리', '물음나무순': '음나무순', '목순임목': '순임목', '산수지(칠액)': '수지(칠액)',
            '물독활': '독활', '약황칠나무': '황칠나무', '(닥나무)': '섬유원료(닥나무)', '섬유원료(닥나무)': '섬유원료(닥나무)'}

# 분류 · 품목 (보고서 순서) - 조림 · 양묘 · 토석과 소계(계)는 뺌
CATS = [
    ('수실류', '밤 호두 대추 떫은감 잣 은행 도토리 산딸기 복분자딸기 머루 다래 개암 석류 돌배 기타수실'),
    ('버섯', '송이 건표고 생표고 목이 석이 능이 꽃송이버섯 복령 싸리 기타버섯류'),
    ('산나물', '고사리 도라지 더덕 두릅 취나물 고비 참나물 원추리 산마늘 고려엉겅퀴(곤드레) 어수리 눈개승마(삼나물) 죽순 기타산나물'),
    ('약용식물', '산수유 오미자 구기자 두충나무 헛개나무 음나무 참죽나무 산초 초피 옻나무 산사나무 황칠나무 꾸지뽕나무 마가목 화살나무 '
              '목단 오갈피 백출 독활 산양삼 삼지구엽초 참쑥 시호 작약 천마 결명자 구절초 약모밀 당귀 천궁 하수오 잔대 마 감초 둥굴레 기타약용식물'),
    ('수액', '자작나무 고로쇠 기타수액'),
    ('수목부산물', '톱밥 목초액 은행잎 칡뿌리 섬유원료(닥나무) 수지(칠액) 음나무순 참죽나무순 옻나무순 오갈피순 기타부산물'),
    ('연료 · 농용자재', '흑탄 백탄 장작 지엽 퇴비 사료'),
    ('용재 · 순임목', '용재 죽재 순임목'),
    ('조경수', '단풍나무류 느티나무류 동백나무 회양목 주목 철쭉류 소나무 배롱나무 벚나무 이팝나무 기타교목류 기타관목류'),
    ('분재 · 잔디 · 화훼', '해송 향나무 소사나무 소나무 철쭉 기타분재소재 기타분재완재 한지형잔디 난지형잔디 야생화 자생란'),
]
DUP = {'해송': ['분재소재', '분재완재'], '향나무': ['분재소재', '분재완재'], '소사나무': ['분재소재', '분재완재'],
       '소나무': ['조경수', '분재소재', '분재완재'], '철쭉': ['분재소재', '분재완재']}

CAT_OF = {}
for cat, names in CATS:
    for n in names.split():
        CAT_OF.setdefault(n, cat)

SIDO = [('서울', '서울'), ('부산', '부산'), ('대구', '대구'), ('인천', '인천'), ('광주', '광주'), ('대전', '대전'), ('울산', '울산'),
        ('세종', '세종'), ('경기', '경기'), ('강원', '강원'), ('충청북', '충북'), ('충청남', '충남'), ('전라북', '전북'), ('전북', '전북'),
        ('전라남', '전남'), ('경상북', '경북'), ('경상남', '경남'), ('제주', '제주')]


def sido_short(n):
    for k, v in SIDO:
        if n.startswith(k):
            return v
    return None


def item_id(name, occ):
    if name in DUP:
        return '%s(%s)' % (name, DUP[name][min(occ, len(DUP[name]) - 1)])
    return name


def num(s):
    return 0.0 if s == '-' else float(s.replace(',', ''))


def blocks(t):
    for p in re.split(r'\n\s*□\s*', '\n' + t)[1:]:
        head, _, body = p.partition('\n')
        yield re.sub(r'\s+', ' ', head).strip(), body


def entries(body):
    out = []
    for pg in re.split(r'\n[^\n]*구 분\s+단위[^\n]*', '\n' + body)[1:3]:
        L, R = [], []
        for line in pg.split('\n'):
            for m in RX.finditer(line):
                (L if m.start(2) < 70 else R).append((re.sub(r'\s', '', m.group(1)), m.group(2), num(m.group(3)), num(m.group(4))))
        out += L + R
    seen = defaultdict(int)
    res = {}
    for n, u, q, w in out:
        n = NAME_FIX.get(n, n)
        if n not in CAT_OF:
            continue
        iid = item_id(n, seen[n])
        seen[n] += 1
        if u == 'ha':
            continue
        res[iid] = (u, q, w)
    return res


def parse_year(y):
    """→ {'sgg': {(시도, 시군구): {품목: (단위, 생산량, 생산액)}}, 'sido': {...}, 'inst': {...}}"""
    p = os.path.join(TXT, '%d.txt.gz' % y)
    t = gzip.open(p, 'rt', encoding='utf-8').read()
    out = {'sgg': {}, 'sido': {}, 'inst': {}}
    for name, body in blocks(t):
        if re.search(r'(시도|시군구|지역)별', name):
            continue
        e = entries(body)
        if len(e) < 60:
            continue
        toks = name.split(' ')
        sd = sido_short(toks[0])
        if sd:
            if len(toks) == 1:
                out['sido'][sd] = e
            else:
                nm = ' '.join(toks[1:])
                if sd == '경북' and nm == '군위군':             # 2023년 7월 대구광역시로 편입
                    sd = '대구'
                out['sgg'][(sd, nm)] = e
        elif len(toks) == 1:                                   # 지방산림청 · 국립기관 합계 (국유림 생산분)
            out['inst'][name] = e
    return out


def years():
    return sorted(int(f[:4]) for f in os.listdir(TXT) if re.match(r'^\d{4}\.txt\.gz$', f)) if os.path.isdir(TXT) else []


def unit_of(iid):
    base = iid.split('(')[0] if iid.split('(')[0] in DUP else iid
    return base


if __name__ == '__main__':
    import sys
    for y in years():
        r = parse_year(y)
        nat = defaultdict(float)
        for grp in ('sido', 'inst'):
            for e in r[grp].values():
                for k, (u, q, w) in e.items():
                    nat[k] += q
        print(y, '시군구 %d · 시도 %d · 기관 %d · 품목 %d' % (len(r['sgg']), len(r['sido']), len(r['inst']), len(nat)),
              '밤 %s톤 · 생표고 %s톤 · 떫은감 %s톤' % tuple('{:,.0f}'.format(nat[k] / 1000) for k in ('밤', '생표고', '떫은감')))
