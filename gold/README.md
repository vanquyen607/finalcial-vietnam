# Aurum Terminal — Theo dõi giá vàng realtime

Web PWA theo dõi giá vàng realtime (SJC, DOJI, PNJ, vàng thế giới) + biểu đồ + cảnh báo.
Nguồn: [vang.today](https://vang.today) cho giá trong nước (CORS mở, không cần key) +
giá spot thế giới lấy realtime từ TradingView/gold-api (xem mục "Nguồn dữ liệu" bên dưới).

```
gold/
├── backend/          FastAPI + SQLite (port 8000, phục vụ luôn SPA đã build)
│   ├── app/
│   │   ├── config.py          cấu hình qua env GOLD_*
│   │   ├── db.py              SQLite: quotes / daily / alerts
│   │   ├── symbols.py         12 mã vàng + alias (SJC, DOJI, PNJ, XAUUSD…)
│   │   ├── providers/         vangtoday.py (nguồn thật) | mock.py (offline)
│   │   ├── services/          poller.py (đẩy giá 30s) | hub.py (WebSocket) | alerts.py
│   │   ├── api/routes.py      REST + WS
│   │   └── main.py            FastAPI + CORS + static SPA fallback
│   └── run.py                 entry point
├── frontend/         React + TypeScript + Vite + lightweight-charts
│   ├── public/                 manifest.webmanifest, sw.js, icons/
│   ├── src/pages/              Home, Detail, ChartPage, Alerts, Settings
│   └── dist/                   build output (backend mount tại đây)
├── data/gold.db      SQLite (tự tạo khi chạy lần đầu)
└── README.md
```

## Nguồn dữ liệu

Đo trực tiếp ngày 30/09/2026:

| Nguồn | Dùng cho | Tần suất thực đo | Kết luận |
| --- | --- | --- | --- |
| `vang.today` (= `giavang.now`) `GET /api/prices?action=current` | 12 mã nội địa | `current_time` cũ 14–25 phút giữa hai lần lấy cách nhau 40s; giá nội địa đứng yên hàng giờ | **Đang dùng** — nhanh nhất trong nhóm không cần key |
| `scanner.tradingview.com` (OANDA → TVC:GOLD → FX → FOREXCOM → SAXO → PAXG) | XAUUSD | tick realtime `streaming` (đo 30/09/2026: các nguồn forex ~4180.0–4180.6) | **Đang dùng** (cuối cùng `api.gold-api.com/price/XAU`). TradingView **không có** giá vàng miếng SJC/DOJI/PNJ nội địa (đã kiểm tra symbol-search) |
| `BINANCE:PAXGUSDT` (token vàng, qua scanner TradingView) | XAUUSD dự phòng | realtime **24/7**, kể cả cuối tuần khi forex đóng; giá ≈ spot + vài USD (đo: 4188.01) | nguồn dự phòng cuối chuỗi |
| `sjc.com.vn` | SJC chính chủ | bảng giá render bằng JS (WebForms), feed cũ `/xml/tygiavang.xml` đã 404 | bỏ — phải render headless |
| `giavang.doji.vn` | DOJI chính chủ | API cùng origin `/api/…` trả 401/403 (cần `accessToken`) | bỏ — cần đăng nhập |
| `pnj.com.vn/blog/gia-vang` | PNJ chính chủ | HTML render sẵn, `#time-now` rỗng, không rõ mốc cập nhật | bỏ — chỉ dùng đối chiếu thủ công |
| `api.btmc.vn/api/BTMCAPI/getpricebtmc` | BTMC (key public trong docs) | timeout | bỏ |
| `github.com/availableservices/gia-vang` | JSON tổng hợp | `sjc.json/pnj.json/doji.json` cũ 10/2024 | bỏ — dữ liệu lỗi thời |
| `github.com/namtrhg/vn-gold-price-api` | self-host scraper | Puppeteer scrape SJC/DOJI/PNJ, không có endpoint public | bỏ — phải tự chạy máy chủ |
| `tygiavang24h.com/api.php` | API VN + lịch sử | free tier **1 request/ngày** | bỏ — không đủ để poll |
| `open.er-api.com` (+ dự phòng `currency-api` qua jsDelivr) | USD/VND | cache 30 phút (giới hạn free ~1500 lượt/tháng) | **Đang dùng** cho chỉ số chênh lệch SJC–thế giới |
| RSS VnExpress / CafeF / VietnamNet / VTV (lọc từ khóa vàng) | tin tức | làm mới 15 phút, dedupe theo link, giữ 7 ngày | **Đang dùng** (`/api/news`, trang Tin tức) |
| `metals-api`, `goldapi.io`, `vapi.vnappmob`, `developers.fhsc.com.vn` | kim loại/FX | cần API key (free 15 ngày hoặc trả phí) | bỏ — tránh key bên thứ ba |

Nguồn giá trong nước ở VN đều chỉ niêm yết lại **1–4 lần/ngày**, nên trần độ tươi của giá nội địa
là ~30 phút (vang.today) — app đã ở mức nhanh nhất có thể, còn realtime thật chỉ có ở XAUUSD.
Không tìm thấy nguồn nội địa free, không key, cập nhật nhanh hơn 30 phút.

## Chạy

```powershell
# 1) Backend (cần build frontend trước nếu muốn thấy giao diện)
cd gold\frontend; npm install; npm run build
cd ..\backend; python run.py        # -> http://127.0.0.1:8000
```

Frontend dev riêng (hot-reload, proxy /api → :8000):

```powershell
cd gold\frontend; npm run dev       # -> http://127.0.0.1:5173
```

## Biến môi trường (backend)

| Env | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `GOLD_HOST` / `GOLD_PORT` | `127.0.0.1` / `8000` | địa chỉ lắng nghe |
| `GOLD_DB` | `gold/data/gold.db` | đường dẫn SQLite |
| `GOLD_PROVIDER` | `vangtoday` | `mock` để chạy offline/demo |
| `GOLD_POLL_INTERVAL` | `30` | giây giữa 2 lần kéo giá |
| `GOLD_FX_INTERVAL` | `1800` | giây giữa 2 lần làm mới tỷ giá |
| `GOLD_NEWS_INTERVAL` | `900` | giây giữa 2 lần quét tin RSS |
| `GOLD_HISTORY_DAYS` | `30` | số ngày lịch sử lưu |
| `GOLD_CORS_ORIGINS` | `*` | origins được phép |
| `GOLD_STATIC_DIR` | `gold/frontend/dist` | thư mục SPA (`__STATIC_DIR__` override) |

## API

| Method | Endpoint | Ghi chú |
| --- | --- | --- |
| GET | `/api/health` | `{state, source, polls, clients, last_success, last_error}` |
| GET | `/api/symbols?featured=true` | danh mục mã (`code`, `alias`, `brand`, `name`, `unit`) |
| GET | `/api/quotes` | 12 giá hiện tại + `change_buy/sell`, `ts` |
| GET | `/api/quotes/{ref}` | theo code hoặc alias (`sjc`, `xauusd`…) |
| GET | `/api/history/{ref}?days=30` | `{intraday[], daily[], source}` |
| GET | `/api/premium` | chênh lệch SJC–thế giới: `gap_abs`, `gap_pct`, `world_vnd_luong`, tỷ giá |
| GET | `/api/news?limit=30` | tin vàng RSS đã lọc/dedupe (`title`, `link`, `source`, `published`, `image`) |
| GET | `/api/sparklines?hours=24` | chuỗi điểm cho card ở Home |
| GET/POST/PATCH/DELETE | `/api/alerts`, `/api/alerts/{id}` | CRUD cảnh báo |
| WS | `/api/ws?topics=quotes,status` | snapshot ngay khi kết nối + push khi có tick |

WebSocket push: `{"type":"quotes","quotes":[…]}` và `{"type":"status",…}`.
Biên độ hoạt động: mua/bán VND/lượng, `XAUUSD` là USD/ounce (`sell=0`).

## Cảnh báo & thông báo

- Ngưỡng theo **% thay đổi trong ngày** (`direction=up|down`), mỗi mã **chỉ báo 1 lần** rồi tự tắt.
- Trình duyệt: bấm "Bật thông báo" ở trang Cảnh báo → `Notification.requestPermission()`.
- Thông báo hệ thống OS cần app đang chạy (PWA đã cài thì service worker giữ trang).

## PWA / Offline

- `manifest.webmanifest` + `sw.js` (cache shell, API network-first có backup cache).
- Cài: Chrome → dấu ⋮ → "Cài đặt trang web/Ứng dụng…" hoặc nút **CÀI** ở trang Cài đặt.
- Icon sinh bằng `python frontend\scripts\make_icons.py` (Pillow) → `public/icons/`.

## Ghi chú vận hành

- Giá trong nước do `vang.today` cung cấp, cập nhật ~30 phút/lần; `poll_interval=30s` chỉ là tần suất **đọc**.
- `XAUUSD` được ghi đè mỗi poll bằng spot realtime (`source=spot`), nên luôn nhảy cùng thị trường.
- Nguồn lỗi → poller tự thử lại; nếu fail lâu sẽ rơi về `MockProvider` để UI không chết (kiểm tra `GOLD_PROVIDER`).
- DB prune tự động: `quotes` giữ theo `GOLD_POLL_INTERVAL`, `daily` giữ `GOLD_HISTORY_DAYS`.
- **Giá vàng chỉ mang tính tham khảo, không phải lời khuyên đầu tư.**
