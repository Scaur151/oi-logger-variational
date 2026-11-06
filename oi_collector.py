#!/usr/bin/env python3
"""Variational Omni: снимок открытого интереса по ВСЕМ рынкам (свопы + перпы).

Один запуск = один снимок. Пишет в data/oi_ГГГГ-Wнн.csv (неделя ISO, UTC).
Колонки: ts_utc,ticker,contract_type,long_oi,short_oi,total_oi,mark_price,volume_24h,funding
Только стандартная библиотека. Не падает на сетевых сбоях: 5 попыток, потом выходит с кодом 1
(в Actions это просто красный запуск, данные не портятся).
"""
import csv, json, os, sys, time, urllib.request, datetime as dt

URL = "https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/v2/stats"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COLS = ["ts_utc", "ticker", "contract_type", "long_oi", "short_oi", "total_oi",
        "mark_price", "volume_24h", "funding"]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def fetch():
    last = None
    for i in range(5):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "oi-logger/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            if d.get("listings"):
                return d
            last = "empty listings"
        except Exception as e:
            last = e
        time.sleep(5 * (i + 1))
    raise RuntimeError("fetch failed: %s" % last)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:00:00Z")  # метка = начало часа, чтобы дубли не плодились
    iso = now.isocalendar()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "oi_%d-W%02d.csv" % (iso[0], iso[1]))
    if os.path.exists(path):
        with open(path) as fh:
            if any(line.startswith(ts + ",") for line in fh):
                print("уже есть снимок за", ts)
                return
    data = fetch()
    rows = []
    for l in data["listings"]:
        oi = l.get("open_interest") or {}
        lo, so = num(oi.get("long_open_interest")), num(oi.get("short_open_interest"))
        rows.append([ts, l.get("ticker"), l.get("contract_type"), lo, so, lo + so,
                     num(l.get("mark_price")), num(l.get("volume_24h")), l.get("funding")])
    new = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(COLS)
        w.writerows(rows)
    print(ts, len(rows), "рынков ->", os.path.basename(path))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ОШИБКА:", e, file=sys.stderr)
        sys.exit(1)
