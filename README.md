# 📊 Phân Tích Cổ Phiếu Việt Nam

> Hệ thống phân tích + chấm điểm cổ phiếu HOSE/HNX/UPCOM — FastAPI + Vanilla JS, dữ liệu từ vnstock.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## 🚀 Chạy nhanh

```bash
cd stocks
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8100
```

Mở `http://127.0.0.1:8100`

---

## ✨ Tính năng

### Phân tích
| Tính năng | Mô tả |
|-----------|-------|
| **Chấm điểm tự động** | Điểm -20 đến +15 dựa trên RSI, MA, volume, momentum |
| **Market-regime gate** | Chỉ khuyến nghị MUA khi thị trường thuận lợi (VN-Index > MA50) |
| **Backtest** | Kiểm chứng stop ATR, T1/T2, hold 20 phiên — trung thực về kết quả |
| **Lịch sự kiện** | GDKHQ, niêm yết, ĐHCĐ, kết quả kinh doanh (CafeF) |
| **News sentiment** | Tag tin tức: 🟢 tích cực, 🔴 tiêu cực, ⚡ catalyst, ⚠️ rủi ro |

### Dữ liệu
| Tính năng | Mô tả |
|-----------|-------|
| **BCTC theo quý + năm** | ROE, tăng trưởng doanh thu/LNST, sparkline YoY |
| **So sánh ngành (peers)** | ROE/PE/PB vs trung bình ngành, xếp hạng #N |
| **Room ngoại + đòn bẩy** | Foreign net buy, D/E, nợ vay/tài sản |
| **Breadth thị trường** | Số mã tăng/giảm trên HOSE/HNX/UPCOM |
| **VN-Index overview** | Giá, MA20/50/200, volume, trend |

### Công cụ
| Tính năng | Mô tả |
|-----------|-------|
| **Alert chủ động** | 6 loại rule (giá, volume, điểm, RSI), scheduler 5 phút |
| **Portfolio tracking** | CRUD vị thế, P&L, phân bổ vốn |
| **Morning brief** | Bản tin tổng hợp từ cache — chỉ số, regime, top screen, sự kiện |
| **Màn lọc (screener)** | Lọc 40 mã theo điểm, tải CSV |

---

## 🏗️ Kiến trúc

```
stocks/
├── backend/           # FastAPI + module Python
│   ├── main.py        # App + routes
│   ├── calc.py        # Chấm điểm + backtest logic
│   ├── screen.py      # Màn lọc
│   ├── regime.py      # Market-regime gate
│   ├── overview.py    # VN-Index, breadth
│   ├── symbol.py      # Chi tiết 1 mã
│   ├── events.py      # Lịch sự kiện (CafeF)
│   ├── sentiment.py   # News sentiment
│   ├── fund.py        # Phân tích cơ bản
│   ├── fundtrend.py   # BCTC theo quý/năm
│   ├── peers.py       # So sánh ngành
│   ├── flow.py        # Room ngoại, đòn bẩy
│   ├── news.py        # Tin tức CafeF
│   ├── alerts.py      # Alert scheduler
│   ├── portfolio.py   # Portfolio CRUD
│   ├── brief.py       # Morning brief
│   ├── market.py      # Market data (8 file split)
│   ├── store.py       # Cache local (TTL 6h)
│   └── vnrate.py      # Rate limiter (7.5s gap)
│
├── frontend/          # Vanilla JS, không framework
│   ├── index.html     # SPA 1 trang
│   ├── core.js        # Helpers, API client
│   ├── overview.js    # Chỉ số + breadth
│   ├── screen.js      # Màn lọc
│   ├── detail.js      # Chi tiết mã
│   ├── alerts.js      # Alert panel
│   ├── portfolio.js   # Portfolio panel
│   ├── brief.js       # Brief panel
│   ├── live.js        # Auto-refresh
│   └── style.css      # Dark/light theme
│
├── tests/             # Test suite
│   ├── test_calc.py   # Chấm điểm assertions
│   ├── backtest.py    # Backtest scenario A
│   ├── backtest_stop.py  # Stop/T1/T2 vs hold
│   └── backtest_stat.py  # Statistical tests
│
└── data/              # Cache (git-ignore)
    ├── sym/           # Giá + kỹ thuật
    ├── fund/          # Fundamental ratios
    ├── fundtrend/     # BCTC trends
    ├── peers/         # Industry mapping
    ├── flow/          # Foreign flow
    ├── events/        # Lịch sự kiện
    ├── news/          # Tin tức
    ├── alerts/        # Alert instances
    └── overview.json, screen.json, regime.json, breadth.json...
```

---

## 🔌 API

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/overview` | GET | Chỉ số VN-Index, HNX, UPCOM |
| `/api/breadth` | GET | Tăng/giảm theo sàn |
| `/api/regime` | GET | Market regime (bull/bear) |
| `/api/screen` | GET | Màn lọc (`?refresh=1`) |
| `/api/symbol/{sym}` | GET | Chi tiết 1 mã (`?refresh=1`) |
| `/api/symbol/{sym}/events` | GET | Lịch sự kiện |
| `/api/symbol/{sym}/fundtrend` | GET | BCTC theo quý/năm |
| `/api/symbol/{sym}/peers` | GET | So sánh ngành |
| `/api/symbol/{sym}/flow` | GET | Room ngoại + đòn bẩy |
| `/api/symbol/{sym}/news` | GET | Tin tức + sentiment |
| `/api/news` | GET | Tin tức thị trường |
| `/api/brief` | GET | Morning brief |
| `/api/alerts` | GET | Alert instances |
| `/api/alerts/rules` | GET/POST | CRUD quy tắc alert |
| `/api/portfolio` | GET/POST | CRUD danh mục |
| `/api/health` | GET | Health check |

---

## 📈 Backtest

### Kết quả (623 lệnh điểm ≥10, 2022–2026, phí 0.4%)

| Cách thoát | Win% | TB/lệnh | Excess vs VN-Index | t-stat | Max profit | Max loss |
|------------|------|---------|---------------------|--------|------------|----------|
| **Hold 20 phiên** | 48.3% | +0.94% | +0.09% | 0.22 | +64% | -43% |
| **Stop ATR + T1** | 60.0% | +0.01% | -0.85% | -3.42 | +12% | -15% |

### Kết luận trung thực
- **Stop ATR + T1** giảm tail risk (max -43% → -15%) nhưng **thua hold 20 phiên**
- Hệ thống là **công cụ kỷ luật + quản lý rủi ro**, không tạo alpha sau phí
- t-stat = 0.22 → **không có ý nghĩa thống kê** → không chứng minh được chiến lược nào tốt hơn

---

## 🛠️ Công nghệ

- **Backend:** FastAPI, uvicorn, Python 3.11
- **Dữ liệu:** vnstock 4.x (community tier), CafeF scraping
- **Frontend:** Vanilla JS (không framework), CSS variables (dark/light)
- **Cache:** JSON files, TTL 6 giờ
- **Deploy:** Render.com (free tier)

---

## 📦 Cài đặt (chi tiết)

```bash
# 1. Clone
git clone https://github.com/vanquyen607/finalcial-vietnam.git
cd finalcial-vietnam

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Dependencies
pip install -r stocks/requirements.txt

# 4. Chạy
cd stocks
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8100

# 5. Test
python tests/test_calc.py
```

### Environment variables

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `VNSTOCK_DISABLE_AGENT_SETUP` | `1` | Tắt vnstock ghi AGENTS.md |
| `PYTHONIOENCODING` | `utf-8` | Fix encoding Windows |

---

## 📱 Responsive

| Screen | Behavior |
|--------|----------|
| ≥1024px | Full layout, 2 cột |
| ≤720px | Topbar wrap, ix-grid 3 cột |
| ≤560px | Panel → bottom sheet |
| ≤400px | Bảng gọn, grid 2 cột |

---

## 📄 License

MIT
