"""Toan phan tich ky thuat — RSI, diem so, vung vao lenh. Khong go API."""
import pandas as pd

from backend.store import now_vn


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, 1e-12)
    return 100 - 100 / (1 + rs)


def _tick(p: float) -> float:
    return 0.1 if p < 20 else (0.2 if p < 50 else (0.5 if p < 100 else 1.0))


def _r(x: float) -> float:
    t = _tick(x)
    return round(round(x / t) * t, 2)


def to_dong(val: pd.Series) -> pd.Series:
    """VCI accumulated_value dang o don vi TRIEU dong (HPG ~400000 = 400 ty) — quy ve dong.

    Neu median phan duong >= 1e6 thi da la dong roi, khong nhan nua.
    """
    nz = val[val > 0]
    if len(nz) and float(nz.median()) < 1e6:
        return val * 1e6
    return val


def make_entry_zone(last: float, sup: float, res: float, ma20: float,
                    rsi: float, score: int) -> tuple[list[float], str]:
    """Vung vao lenh — luon tang dan (pure function de unit test).

    canh near_res co y dat vung len tren gia (cho break qua khang cu).
    """
    near_res = res / last - 1 <= 0.03
    if rsi > 70:
        entry = [_r(ma20 * 0.99), _r(ma20 * 1.02)]
        entry_note = (f"RSI {rsi:.0f} đang quá mua — KHÔNG mua đuổi, "
                      f"chờ pullback về vùng {entry[0]}–{entry[1]}")
    elif near_res:
        a, b = _r(last * 0.998), _r(res * 1.005)
        entry = [min(a, b), max(a, b)]
        entry_note = (f"Chờ đóng cửa trên kháng cự {res:.1f} với thanh khoản cao để mua, "
                      f"hoặc tích lũy trong vùng {entry[0]}–{entry[1]}")
    else:
        lo = max(sup * 0.99, min(ma20 * 0.985, last * 0.995))
        entry = [_r(min(lo, last * 0.995)), _r(last)]
        entry_note = f"Mua tích lũy trong vùng {entry[0]}–{entry[1]} (gần hỗ trợ {sup:.1f})"
    if entry[0] > entry[1]:
        entry = [_r(min(entry[0], entry[1])), _r(max(entry[0], entry[1]))]
    if entry[0] == entry[1] and entry[1] > 0:
        entry[0] = _r(entry[1] - _tick(entry[1]))   # lam tron tick de chet vung -> mo rong 1 tick

    if score < 0:
        entry_note = (f"KHÔNG mua lúc này — cấu trúc kỹ thuật đang xấu. Vùng {entry[0]}–{entry[1]} "
                      f"chỉ là nơi nhiều người cắt lỗ; chờ giá vượt MA20 với thanh khoản tốt rồi tính tiếp")
    return entry, entry_note


def compute(sym: str, df: pd.DataFrame) -> dict | None:
    if df is None or len(df) < 60:
        return None
    c, v, hi, lo = df["Close"], df["Volume"], df["High"], df["Low"]
    last = float(c.iloc[-1])
    if last <= 0:
        return None

    ma = {p: float(c.rolling(p).mean().iloc[-1]) for p in (20, 50, 200) if len(c) >= p}
    rsi = float(_rsi(c).iloc[-1])
    macd_line = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - sig
    hist_val, hist_prev = float(hist.iloc[-1]), float(hist.iloc[-5])
    vol20 = float(v.rolling(20).mean().iloc[-1]) or 1.0
    vr = float(v.iloc[-1]) / vol20
    r5 = (last / float(c.iloc[-6]) - 1) * 100
    r20 = (last / float(c.iloc[-21]) - 1) * 100 if len(c) > 21 else 0.0
    hi52, lo52 = float(c.tail(250).max()), float(c.tail(250).min())
    sup, res = float(lo.tail(20).min()), float(hi.tail(20).max())
    ma20, ma50 = ma.get(20, last), ma.get(50, last)
    ma200 = ma.get(200, last)

    score = 0
    score += 2 if last > ma20 else -2
    score += 2 if ma20 > ma50 else -2
    score += 2 if last > ma200 else -2
    score += 2 if hist_val > 0 and hist_val > hist_prev else (-2 if hist_val < 0 else 0)
    score += 1 if 45 <= rsi <= 72 else (-2 if rsi > 75 else 0)
    score += 1 if vr >= 1.0 else 0
    score += 2 if r20 > 0 else -1
    score += 1 if r5 > 0 else 0

    atr = float((hi - lo).tail(14).mean())
    stop = _r(max(sup * 0.985, last - 2.2 * atr))
    t1 = _r(min(res * 1.02, last * 1.06))
    t2 = _r(max(hi52, last * 1.12))

    # xu huong
    if last > ma20 > ma50 and last > ma200:
        trend = "xu hướng tăng, giá trên MA20/MA50/MA200"
    elif last > ma20 and last > ma50:
        trend = "hồi phục ngắn hạn, giá đã vượt MA20 và MA50"
    elif last > ma20:
        trend = "vừa vượt MA20 nhưng còn dưới MA50/MA200"
    elif last > ma50:
        trend = "đi ngang, giá dưới MA20"
    else:
        trend = "xu hướng giảm, giá dưới MA20 và MA50"

    # xu the + diem
    if score >= 10:
        verdict, tone = "MUA / TÍCH LŨY", "good"
    elif score >= 6:
        verdict, tone = "THEO DÕI", "watch"
    elif score >= 0:
        verdict, tone = "TRUNG TÍNH", "neutral"
    else:
        verdict, tone = "TRÁNH / GIẢM", "bad"

    entry, entry_note = make_entry_zone(last, sup, res, ma20, rsi, score)

    risk = (last - stop) / last * 100
    rr = (t1 - last) / max(last - stop, 1e-9)
    vol_txt = "thanh khoản thấp" if vr < 0.8 else ("thanh khoản cao" if vr >= 1.3 else "thanh khoản trung bình")

    narrative = (f"Giá {last:,.1f} đang {trend}. RSI {rsi:.0f}, MACD "
                 f"{'tích cực' if hist_val > 0 else 'tiêu cực'}, {vol_txt} ({vr:.2f}× TB20 phiên), "
                 f"20 phiên thay đổi {r20:+.1f}%. {entry_note}. Cắt lỗ {stop:.1f} "
                 f"(rủi ro {risk:.1f}%), chốt lời từng phần tại {t1:.1f} rồi hướng {t2:.1f} "
                 f"(risk:reward ~1:{rr:.1f})."
                 + ("" if score >= 0 else " Cấu trúc kỹ thuật đang xấu — ưu tiên đứng ngoài."))

    ohlcv = [
        {"time": d.strftime("%Y-%m-%d"), "open": round(float(o), 2), "high": round(float(h), 2),
         "low": round(float(l), 2), "close": round(float(x), 2), "volume": int(q)}
        for d, o, h, l, x, q in zip(df.index, df["Open"], df["High"], df["Low"], df["Close"], df["Volume"])
    ]

    return {
        "symbol": sym,
        "close": last,
        "date": str(df.index[-1].date()),
        "rsi": round(rsi, 1),
        "ma20": round(ma20, 2), "ma50": round(ma50, 2), "ma200": round(ma200, 2),
        "macd_hist": round(hist_val, 3),
        "vol_ratio": round(vr, 2),
        "r5": round(r5, 1), "r20": round(r20, 1),
        "sup": round(sup, 2), "res": round(res, 2),
        "hi52": round(hi52, 2), "lo52": round(lo52, 2),
        "score": score, "max_score": 13,
        "verdict": verdict, "tone": tone, "trend": trend,
        "entry": entry, "entry_note": entry_note,
        "stop": stop, "t1": t1, "t2": t2,
        "risk_pct": round(risk, 1), "rr": round(rr, 1),
        "narrative": narrative,
        "ohlcv": ohlcv,
        "updated_at": now_vn().isoformat(timespec="seconds"),
    }
