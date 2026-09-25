# 임산물 수급 레이더

밤 · 호두 · 대추 · 잣 · 표고버섯 · 떫은감 품목별 월별 수출입 시계열, 연간 생산량, 최근 뉴스 · (주)서던포스트

**공개 페이지** : https://baebong3.github.io/forest-radar/

## 동작
- 매일 07:00(KST) GitHub Actions가 뉴스와 관세청 수출입 통계를 모아 `data/radar.db`에 누적하고 `docs/index.html`을 다시 만듦
- 탭(종합 · 품목 6개)은 자바스크립트 없이 동작 → 모바일 앱 내 뷰어에서도 열림

## 자료원
| 구분 | 자료 | 주기 | 필요한 키 (Settings › Secrets › Actions) |
|---|---|---|---|
| 수출입 | 관세청 「품목별 수출입실적(GW)」 공공데이터포털 API - 중량(kg) · 금액(달러) | 월별 | `DATA_GO_KR_KEY` |
| 뉴스 | 네이버 뉴스 검색 API + Google 뉴스 RSS | 매일 | `NAVER_ID` · `NAVER_SECRET` (없으면 Google만) |
| 관측 | 한국농촌경제연구원 임업관측 월보(밤 · 표고버섯 · 대추 · 감 · 호두) - 소제목(판단)과 첫 문장(근거) 추출 | 매월 4일(품목별 발표 월 상이) | 없음 |
| 생산 | 산림청 임산물생산조사 | 연 1회(다음 해 10월 공표) | 없음 - `data/production.csv` 직접 입력 |

- 월별 생산량은 국가통계로 공표되지 않음 → 생산은 연간 공표값만 사용
- 수출입은 처음 실행 때 2016년 1월부터 채우고, 이후에는 최근 14개월을 매번 다시 받아 잠정치 수정을 반영

## HS 부호 (radar/items.py)
| 품목 | 조회 부호 | 비고 |
|---|---|---|
| 밤 | 0802.41 · 0802.42 · 0811.90 중 '밤' · 2008.19 중 '밤' | 생밤 · 깐밤 · 냉동밤 · 조제밤 (농경연 관측 월보와 같은 범위) |
| 호두 | 0802.31 · 0802.32 | 〃 |
| 잣 | 0802.91 · 0802.92 | 〃 |
| 대추 | 0813.40-2000 | 건조한 대추 |
| 표고버섯 | 0712.39-1020 · 0709.59 중 '표고' · 2003.90 중 '표고' | 건표고 · 생표고 · 조제표고 |
| 떫은감 | 0810.70 중 '감' · 0813.40 중 '감' | 감(신선) · 건조감(곶감 등) |

6단위에 다른 품목이 섞이는 부호는 API가 돌려준 한글 품목명(statKor)으로 걸러 저장함. 페이지 각 품목 상세표 아래에 실제 저장된 부호 · 품목명이 표시되므로 거기서 확인

## 연간 생산량 입력 (data/production.csv)
```
year,item,tonnes,source
2024,밤,00000,임산물생산조사
```
item 은 `밤 · 호두 · 대추 · 잣 · 표고버섯 · 떫은감` 중 하나 

## 구조
```
radar/items.py          품목 · HS 부호 · 뉴스 질의어 · 관련성 규칙   ← 품목 추가는 여기서
radar/collect_news.py   뉴스 → data/radar.db (news)
radar/collect_trade.py  관세청 API → data/radar.db (trade)
radar/collect_krei.py   농경연 임업관측 월보 PDF → data/radar.db (krei)
radar/build.py          radar.db + production.csv → docs/index.html (검증 게이트 포함)
radar/charts.py         빌드 시점 SVG 차트 (PC 세로 막대 · 모바일 가로 막대)
```

## 로컬 실행
```bash
pip install -r requirements.txt
set DATA_GO_KR_KEY=...                       # Windows (Decoding 키 권장)
python radar/collect_trade.py
python radar/collect_news.py --days 7
python radar/build.py
```
