# -*- coding: utf-8 -*-
"""공용 - 시간대 · DB · 수치 표기(사사오입 · 천 단위 콤마)"""
import os, sqlite3
from datetime import timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

KST = timezone(timedelta(hours=9))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'radar.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS news(
  url TEXT NOT NULL,
  item TEXT NOT NULL,
  title TEXT NOT NULL,
  media TEXT,
  date TEXT NOT NULL,
  summary TEXT,
  category TEXT,
  source TEXT,
  collected_at TEXT,
  PRIMARY KEY(url, item)
);
CREATE INDEX IF NOT EXISTS ix_news_date ON news(date);
CREATE TABLE IF NOT EXISTS trade(
  item TEXT NOT NULL,          -- 품목 키 (chestnut 등)
  hs TEXT NOT NULL,            -- API가 돌려준 HS 부호
  ym TEXT NOT NULL,            -- YYYY-MM
  stat_kor TEXT,               -- API 한글 품목명
  form TEXT,                   -- 형태 (껍데기 있는 것 등)
  exp_kg REAL, exp_usd REAL,   -- 수출 중량(kg) · 금액(달러)
  imp_kg REAL, imp_usd REAL,   -- 수입 중량(kg) · 금액(달러)
  fetched_at TEXT,
  PRIMARY KEY(item, hs, ym)
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""


def db(path=None):
    path = path or DB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def rnd(x, nd=0):
    """사사오입 (파이썬 round의 은행가 반올림 · 부동소수점 오차 방지)"""
    q = Decimal(1).scaleb(-nd)
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def fmt(x, nd=0):
    """천 단위 콤마 + 소수 자리 고정 (예: 17586 → 17,586 / 88 → 88.0)"""
    if x is None:
        return '-'
    d = rnd(x, nd)
    if d == 0:
        d = abs(d)            # -0.0 방지
    return '{:,.{n}f}'.format(d, n=nd)


def pct(now, prev, nd=1):
    """증감률(%) - 비교 기준이 0이거나 없으면 None"""
    if prev in (None, 0) or now is None:
        return None
    return (now - prev) / prev * 100


def fmt_pct(p, nd=1, sign=True):
    if p is None:
        return '-'
    s = fmt(p, nd)
    if sign and rnd(p, nd) > 0:
        s = '+' + s
    return s + '%'
