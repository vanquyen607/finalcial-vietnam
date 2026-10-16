# -*- coding: utf-8 -*-
"""Unit test cac module moi: sentiment, events, auth, brief — khong go API, <5s."""
import os
import sys
from pathlib import Path

os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import auth, brief, events, sentiment

fails = []


def check(name, cond, extra=""):
    if cond:
        print(f"  OK  {name}")
    else:
        fails.append(name)
        print(f"FAIL  {name} {extra}")


# ---------------------------------------------------------------- sentiment
print("== sentiment.analyze_text ==")
pos = sentiment.analyze_text("Lợi nhuận tăng trưởng mạnh trong quý 3")
check("tich cuc: score > 0", pos.score > 0, f"score={pos.score}")
check("tich cuc: tag positive", "positive" in pos.tags, pos.tags)

neg = sentiment.analyze_text("Công ty thua lỗ nặng, doanh thu giảm mạnh")
check("tieu cuc: score < 0", neg.score < 0, f"score={neg.score}")
check("tieu cuc: tag negative", "negative" in neg.tags, neg.tags)

cat = sentiment.analyze_text("FPT công bố báo cáo tài chính quý 3")
check("catalyst: co tag catalyst", "catalyst" in cat.tags, cat.tags)

risk = sentiment.analyze_text("Cảnh báo rủi ro nợ xấu gia tăng")
check("risk: co tag risk", "risk" in risk.tags, risk.tags)

skip = sentiment.analyze_text("Ngôi sao showbiz đám cưới")
check("skip tin quan he: tag skip", "skip" in skip.tags, skip.tags)
check("skip: score = 0", skip.score == 0.0, f"score={skip.score}")

neutral = sentiment.analyze_text("Hội đồng quản trị tổ chức họp định kỳ")
check("trung tinh: |score| <= 1", -1.0 <= neutral.score <= 1.0, f"score={neutral.score}")

empty = sentiment.analyze_text("")
check("rong: score = 0", empty.score == 0.0)

# score luon trong [-1, 1]
for t in ["lợi nhuận tăng trưởng kỷ lục bứt phá phục hồi",
          "lỗ sụt giảm khủng hoảng phá sản thất bại"]:
    s = sentiment.analyze_text(t).score
    check(f"score clamp [-1,1]: {t[:20]}", -1.0 <= s <= 1.0, f"score={s}")

print("== sentiment.analyze_news_item / tag_news_list ==")
item = sentiment.analyze_news_item({"title": "HPG lợi nhuận tăng", "sub": ""})
check("analyze_news_item: co field sentiment", "sentiment" in item, item.keys())
check("analyze_news_item: co field sent_tags", "sent_tags" in item)
tagged = sentiment.tag_news_list([{"title": "A"}, {"title": "B"}])
check("tag_news_list: giu nguyen so luong", len(tagged) == 2)
check("tag_news_list: moi item co sentiment", all("sentiment" in x for x in tagged))

# ---------------------------------------------------------------- events
print("== events._parse_date ==")
d1 = events._parse_date("GDKHQ ngày 15.10.2026")
check("DD.MM.YYYY -> 2026-10-15", d1 is not None and d1.strftime("%Y-%m-%d") == "2026-10-15",
      str(d1))
d2 = events._parse_date("15/10/2026 chốt quyền")
check("DD/MM/YYYY -> 2026-10-15", d2 is not None and d2.strftime("%Y-%m-%d") == "2026-10-15",
      str(d2))
check("khong co ngay -> None", events._parse_date("Thông báo khác") is None)
check("ngay sai -> None", events._parse_date("32.13.2026") is None)

print("== events._classify ==")
check("co tuc -> dividend", events._classify("Trả cổ tức bằng tiền mặt") == "dividend")
check("niem yet -> listing", events._classify("Niêm yết bổ sung cổ phiếu") == "listing")
check("phat hanh -> issuance", events._classify("Phát hành thêm cổ phiếu cho cổ đông") == "issuance")
check("dai hoi -> agm", events._classify("Tổ chức đại hội cổ đông thường niên") == "agm")
check("kqkd -> earnings", events._classify("Công bố kết quả kinh doanh quý 3") == "earnings")
check("khac -> other", events._classify("Thông báo thay đổi nhân sự") == "other")

# ---------------------------------------------------------------- auth
print("== auth ==")
check("is_locked tra ve bool", isinstance(auth.is_locked(), bool))

# ---------------------------------------------------------------- screen cooldown
print("== screen.start_screen cooldown ==")
from backend import screen

# stub worker + thread de khong go API / khong ton quota
screen._screen_worker = lambda: None
import threading as _th
_real_thread = _th.Thread
_th.Thread = lambda *a, **k: type("T", (), {"start": lambda self: None})()
try:
    screen._last_manual = 0.0
    screen.screen_state["worker_alive"] = False
    screen.screen_state["status"] = "idle"
    r1 = screen.start_screen(auto=False)
    check("lan dau (khong cooldown) -> running", r1.get("status") == "running", str(r1))
    # worker stub khong that su chay -> coi nhu chua chay xong
    screen.screen_state["worker_alive"] = False
    screen.screen_state["status"] = "idle"
    r2 = screen.start_screen(auto=False)
    check("lan 2 trong 90s -> cooldown", r2.get("status") == "cooldown", str(r2))
    check("cooldown: co retry_in > 0", r2.get("retry_in", 0) > 0, str(r2))
    r3 = screen.start_screen(auto=True)
    check("auto bo qua cooldown -> running", r3.get("status") == "running", str(r3))
finally:
    _th.Thread = _real_thread

# ---------------------------------------------------------------- brief (smoke)
print("== brief.build_brief (smoke) ==")
try:
    b = brief.build_brief()
    check("build_brief: status ready", b.get("status") == "ready")
    for k in ("lines", "indices", "regime", "breadth", "top_screen",
              "upcoming_events", "alert_count"):
        check(f"build_brief: co key {k}", k in b)
    check("build_brief: lines la list", isinstance(b["lines"], list))
except Exception as e:
    check("build_brief khong crash", False, repr(e))

print()
if fails:
    print(f"TEST_MODULES FAILED — {len(fails)} loi: {fails}")
    sys.exit(1)
print("TEST_MODULES OK — all assertions passed")
