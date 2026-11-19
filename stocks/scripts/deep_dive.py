"""Phan tich sau cac ung vien dau tu tu screener."""
import sys, os, time, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screener_tech import _throttle, _read_cache, _write_cache, CACHE
from vnstock import Reference

CANDIDATES = os.environ.get(
    "DD_LIST", "TCB,VPB,FRT,HDB,BSR,GVR,MSN").split(",")
SKIP_INFO = os.environ.get("DD_SKIP_INFO", "") == "1"
OUT_NAME = os.environ.get("DD_OUT", "deep_dive_result.json")


def get(df_like, keys):
    out = {}
    if df_like is None or len(df_like) == 0:
        return out
    if isinstance(df_like, pd.DataFrame):
        row = df_like.iloc[0]
    else:
        row = df_like
    for k in keys:
        try:
            v = row[k]
            out[k] = None if pd.isna(v) else v
        except Exception:
            pass
    return out


def main():
    ref = Reference()
    results = {}
    for sym in CANDIDATES:
        info = news = ev = None
        try:
            comp = ref.company(symbol=sym)
        except Exception as e:
            print(f"  [{sym}] company() ERR {e}")
            comp = None
        if comp is not None:
            todo = [("news", "news"), ("events", "events")]
            if not SKIP_INFO:
                todo.insert(0, ("info", "info"))
            for name, setter in todo:
                for a in range(3):
                    try:
                        _throttle()
                        val = getattr(comp, name)()
                        if setter == "info":
                            info = val
                        elif setter == "news":
                            news = val
                        else:
                            ev = val
                        break
                    except SystemExit:
                        time.sleep(35)
                    except Exception as e:
                        if a == 2:
                            print(f"  [{sym}.{name}] ERR {e}")
                        time.sleep(2)

        n_rows = len(news) if news is not None else 0
        news_list = []
        if news is not None and n_rows:
            cols = [c for c in news.columns
                    if c.lower() in ("publishedat", "published_at", "title", "source", "url", "symbol", "content")]
            if not cols:
                cols = list(news.columns)[:5]
            head = news[cols].head(6)
            news_list = json.loads(head.to_json(orient="records", force_ascii=False))

        full_info = {}
        if info is not None and len(info):
            try:
                full_info = json.loads(info.head(1).to_json(orient="records", force_ascii=False))[0]
            except Exception:
                full_info = get(info, ["symbol", "companyName", "price"])

        results[sym] = dict(
            info=full_info,
            events=json.loads(ev.head(5).to_json(orient="records", force_ascii=False)) if ev is not None and len(ev) else [],
            news=news_list,
        )
        print(f"=== {sym} ===")
        print("  INFO:", json.dumps(results[sym]["info"], ensure_ascii=False, default=str)[:400])
        print("  EV  :", json.dumps(results[sym]["events"], ensure_ascii=False, default=str)[:300])
        print("  NEWS:", json.dumps(results[sym]["news"], ensure_ascii=False, default=str)[:600])

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT_NAME)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print("\nSaved:", out)


if __name__ == "__main__":
    main()
