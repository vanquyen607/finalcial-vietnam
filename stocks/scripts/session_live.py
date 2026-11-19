"""Bao cao phien dang mo: bang gia realtime + chi so."""
import sys, os, time, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screener_tech import _throttle, _write_cache, _read_cache, UNIVERSE, CACHE
from vnstock import Market

BOARD = os.path.join(CACHE, "_BOARD.csv")


def get_board():
    for a in range(3):
        try:
            _throttle()
            q = Market().equity().quote(symbols_list=UNIVERSE)
            q.to_csv(BOARD, index=False, encoding="utf-8-sig")
            return q
        except SystemExit:
            time.sleep(60)
        except Exception as e:
            print("board err", str(e)[:120])
            time.sleep(3)
    if os.path.exists(BOARD):
        return pd.read_csv(BOARD, encoding="utf-8-sig")
    return None


def get_index(sym, tries=4):
    for a in range(tries):
        try:
            _throttle()
            df = Market().index(symbol=sym).ohlcv(
                start="2026-08-01", end="2026-09-29", interval="1D", count=40)
            df = df.rename(columns={"time": "Date", "open": "Open", "high": "High",
                                    "low": "Low", "close": "Close", "volume": "Volume"})
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
            _write_cache(df, "_IDX_" + sym)
            return df
        except SystemExit:
            time.sleep(60)
        except Exception as e:
            print("idx err", sym, str(e)[:90])
            time.sleep(3)
    return None


def main():
    print("=== CHI SO ===")
    for s in ["VNINDEX", "VN30", "HNXINDEX"]:
        df = get_index(s)
        if df is None:
            print(s, "FAIL")
            continue
        c = df["Close"].astype(float)
        last, prev = float(c.iloc[-1]), float(c.iloc[-2])
        ma20 = float(c.rolling(20).mean().iloc[-1])
        ma50 = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else float("nan")
        print(f"{s}: {last:,.2f} ({last - prev:+,.2f}, {(last / prev - 1) * 100:+.2f}%) "
              f"MA20 {ma20:,.2f} ({(last / ma20 - 1) * 100:+.2f}%) "
              f"MA50 {ma50:,.2f} | {str(df.index[-1])[:10]} | r5 {((last / float(c.iloc[-6]) - 1) * 100):+.2f}% "
              f"r20 {((last / float(c.iloc[-21]) - 1) * 100):+.2f}%")

    print("\n=== BANG REALTIME ===")
    q = get_board()
    if q is None:
        print("no board")
        return
    q = q.copy()
    q["pct"] = q["percent_change"].astype(float)
    q["val_ty"] = q["total_value"].astype(float) / 1e9
    q["fnet_vol"] = q["foreign_buy_volume"].astype(float) - q["foreign_sell_volume"].astype(float)
    q["toward_hi"] = (q["high_price"].astype(float) - q["reference_price"].astype(float)) / q["reference_price"].astype(float) * 100
    q["toward_lo"] = (q["low_price"].astype(float) - q["reference_price"].astype(float)) / q["reference_price"].astype(float) * 100
    print("gio/chi so:", q["time"].max())
    print(f"tong gia tri 45 ma: {q['val_ty'].sum():,.0f} ty | tong KL: {q['volume_accumulated'].astype(float).sum()/1e6:,.1f} tr")
    print("tang:", int((q["pct"] > 0.01).sum()),
          "| giam:", int((q["pct"] < -0.01).sum()),
          "| bang:", int((q["pct"].abs() <= 0.01).sum()))
    cols = ["symbol", "close_price", "reference_price", "pct", "val_ty", "volume_accumulated",
            "high_price", "low_price", "ceiling_price", "floor_price", "fnet_vol"]
    print("\n-- TOP 10 TANG --")
    print(q.sort_values("pct", ascending=False).head(10)[cols].to_string(index=False))
    print("\n-- TOP 10 GIAM --")
    print(q.sort_values("pct").head(10)[cols].to_string(index=False))
    print("\n-- TOP 8 THANH KHOAN --")
    print(q.sort_values("val_ty", ascending=False).head(8)[["symbol", "pct", "val_ty"]].to_string(index=False))
    print("\n-- NGAINGOAI (vol rong) --")
    print(q.sort_values("fnet_vol")[["symbol", "fnet_vol", "pct"]].to_string(index=False)
          if False else q.assign(fn=q["fnet_vol"]).sort_values("fn")[
              ["symbol", "fn", "pct"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
