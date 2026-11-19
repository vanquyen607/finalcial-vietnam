"""Tong ket phien: chi so, nganh, breadth."""
import sys, time, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screener_tech import _throttle, _write_cache, _read_cache, CACHE
from vnstock import Reference, Market

IDX = ["VNINDEX", "HNXINDEX", "UPCOMIND"]


def get_index(sym, tries=5):
    df = _read_cache("_IDX_" + sym)
    if df is not None:
        return df
    for a in range(tries):
        try:
            _throttle()
            df = Market().index(symbol=sym).ohlcv(
                start="2026-08-01", end="2026-09-25", interval="1D", count=40)
            df = df.rename(columns={"time": "Date", "open": "Open", "high": "High",
                                    "low": "Low", "close": "Close", "volume": "Volume"})
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
            _write_cache(df, "_IDX_" + sym)
            return df
        except SystemExit:
            time.sleep(60)
        except Exception as e:
            print("  ERR", sym, str(e)[:90])
            time.sleep(3)
    return None


def main():
    print("=== CHI SO ===")
    for s in IDX:
        df = get_index(s)
        if df is None:
            print(s, "FAIL")
            continue
        c = df["Close"]
        last, prev = float(c.iloc[-1]), float(c.iloc[-2])
        v = float(df["Volume"].iloc[-1]) / 1e6
        print(f"{s}: {last:,.2f} ({last - prev:+,.2f}, {(last / prev - 1) * 100:+.2f}%) "
              f"KL={v:,.1f}tr | r5={((last / float(c.iloc[-6]) - 1) * 100):+.1f}% "
              f"r20={((last / float(c.iloc[-21]) - 1) * 100):+.1f}% | {str(df.index[-1])[:10]}")

    # nganh
    ind = None
    for a in range(4):
        try:
            _throttle()
            ind = Reference().industry.list_by_industry()
            break
        except SystemExit:
            time.sleep(60)
        except Exception as e:
            print("  ind err", str(e)[:90])
            time.sleep(3)
    if ind is not None:
        print("\n=== NGANH ===")
        print("cols:", list(ind.columns), "rows=", len(ind))
        print(ind.head(5).to_string())
        ind.to_csv(os.path.join(CACHE, "_IND_BY.csv"), index=False, encoding="utf-8-sig")

    # tong hop tu cache 45 ma
    rows = []
    res = {r["sym"]: r for r in json.load(
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "screener_result.json"),
             encoding="utf-8"))}
    for f in sorted(os.listdir(CACHE)):
        if f.startswith("_") or not f.endswith(".csv"):
            continue
        sym = f[:-4]
        if sym not in res:
            continue
        rows.append(res[sym])
    d = pd.DataFrame(rows)
    if len(d):
        print("\n=== 45 MA: PHIEN 25/09 ===")
        print("tang:", int((d["chg"] > 0.05).sum()),
              "| giam:", int((d["chg"] < -0.05).sum()),
              "| bang:", int((abs(d["chg"]) <= 0.05).sum()))
        d["chg"] = d["chg"].round(2)
        cols = ["sym", "px", "chg", "total", "rsi", "vol_ratio", "liq_yen"]
        print("\n-- TOP 8 tang --")
        print(d.sort_values("chg", ascending=False).head(8)[cols].to_string(index=False))
        print("\n-- TOP 8 giam --")
        print(d.sort_values("chg").head(8)[cols].to_string(index=False))
        print("\n-- tong thanh sach (ty dong) --", round(d["liq_yen"].sum(), 0))


if __name__ == "__main__":
    main()
