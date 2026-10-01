# Aurum Terminal — Theo dõi giá vàng realtime

Web PWA theo dõi giá vàng realtime (SJC, DOJI, PNJ, cửa hàng tư nhân: Mi Hồng, Bảo Tín Mạnh Hải,
Phú Quý, Ngọc Thẩm, vàng thế giới) + biểu đồ + cảnh báo — 19 mã.
Nguồn: [vang.today](https://vang.today) (12 mã) + Simplize (5 mã) + Ngọc Thẩm chính chủ (2 mã) cho
giá trong nước (đều CORS/public, không cần key) + giá spot thế giới realtime từ
TradingView/gold-api (xem mục "Nguồn dữ liệu" bên dưới).

```
gold/
├── backend/          FastAPI + SQLite (port 8000, phục vụ luôn SPA đã build)
│   ├── app/
│   │   ├── config.py          cấu hình qua env GOLD_*
│   │   ├── db.py              SQLite: quotes / daily / alerts
│   │   ├── symbols.py         19 mã vàng + alias (SJC, DOJI, PNJ, Mi Hồng, Phú Quý…)
│   │   ├── providers/         vangtoday.py + simplize.py + ngoctham.py (composite) | mock.py
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
| `vang.today` (= `giavang.now`) `GET /api/prices?action=current` | 12 mã nội địa (SJC, DOJI, PNJ, BTMC, Viettin…) | `current_time` cũ 14–25 phút giữa hai lần lấy cách nhau 40s; giá nội địa đứng yên hàng giờ | **Đang dùng** — nhanh nhất trong nhóm không cần key |
| `simplize.vn/_next/data/{buildId}/gia-vang/{brand}/{slug}.json` | 5 mã cửa hàng tư nhân: Mi Hồng (SJC, 9999), Bảo Tín Mạnh Hải 9999, Phú Quý (SJC, 9999) | JSON Next.js public, `priceBuy/priceSell` theo ngày, cache 15 phút; buildId lấy lại từ HTML khi đổi deploy | **Đang dùng** — Simplize không có API key, catalog lấy từ `sitemap/gold/sitemap_gold.xml` |
| `ngoctham.com/ajax/proxy_banggia.php` | 2 mã Ngọc Thẩm (9999, SJC) — **nguồn chính chủ** | JSON public, có ETag/304, `date` theo giờ VN; giá niêm yết theo **CHỈ** → app ×10 ra lượng | **Đang dùng** — nhanh nhất nhóm chính chủ (đo 01/10/2026: cập nhật 07:20, giá 140.0/143.5tr SJC) |
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
Ngọc Thẩm cập nhật nhiều lần trong ngày (đo được 07:20 trong ngày giao dịch); Simplize niêm yết theo ngày.
19 mã = 12 (vang.today, gồm cả XAUUSD spot realtime) + 5 (Simplize) + 2 (Ngọc Thẩm).
Không tìm thấy nguồn nội địa free, không key, cập nhật nhanh hơn 30 phút cho nhóm SJC/DOJI/PNJ.

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
| `GOLD_HOST` / `GOLD_PORT` | `127.0.0.1` / `8000` | địa chỉ lắng nghe (production: `0.0.0.0`) |
| `GOLD_DB_PATH` | `gold/data/gold.db` | đường dẫn SQLite |
| `GOLD_PROVIDER` | `vangtoday` | `mock` để chạy offline/demo |
| `GOLD_PROVIDER_TIMEOUT` | `12.0` | timeout gọi nguồn (giây) |
| `GOLD_POLL_INTERVAL` | `30` | giây giữa 2 lần kéo giá |
| `GOLD_HISTORY_DAYS` | `30` | số ngày lịch sử giữ trong DB |
| `GOLD_FX_INTERVAL` | `1800` | giây giữa 2 lần làm mới tỷ giá |
| `GOLD_NEWS_INTERVAL` | `900` | giây giữa 2 lần quét tin RSS |
| `GOLD_STATIC_DIR` | `gold/frontend/dist` | thư mục SPA đã build |
| `GOLD_ALERT_THRESHOLD_PCT` | `1.0` | (dự trữ) ngưỡng cảnh báo mặc định |
| `GOLD_API_TOKEN` | _(rỗng = mở)_ | đặt token để yêu cầu header `X-Api-Token` cho POST/PATCH/DELETE |
| `GOLD_CORS_ORIGINS` | _(rỗng = cùng origin)_ | origin cross-site, cách nhau dấu phẩy |
| `GOLD_RATE_LIMIT_PER_MIN` | `120` | request/phút/IP cho `/api/*` (`0` = tắt) |
| `GOLD_ENABLE_POLLER` | `true` | `false` = worker API-only, đọc DB dùng chung (multi-worker) |
| `GOLD_TELEGRAM_BOT_TOKEN` / `GOLD_TELEGRAM_CHAT_ID` | _(trống = tắt)_ | báo khi nguồn giá chết liên tục quá `GOLD_TELEGRAM_ALERT_AFTER_SEC` (mặc định 600s) |

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
| GET | `/api/metrics` | nhịp poll, lỗi từng nguồn, trạng thái tỷ giá/tin, streak lỗi |
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
- Nguồn lỗi → poller tự thử lại; nếu fail lâu sẽ rơi về `MockProvider` để UI không chết
  (header hiện `MOCK`). **Giá mock không bao giờ ghi vào DB và không kích hoạt cảnh báo.**
- DB prune tự động: `quotes`/`fx` giữ 30/7 ngày, `news` giữ 7 ngày, `daily` giữ `GOLD_HISTORY_DAYS`.
- Backup DB hàng ngày: `python gold\backend\scripts\backup_db.py` (giữ 7 bản trong `gold\backups\`).
  Windows: lên lịch bằng Task Scheduler (`schtasks /create /tn AurumBackup /sc daily /st 02:00 …`).
- Production: đặt `GOLD_API_TOKEN` (sinh bằng `python -c "import secrets; print(secrets.token_hex(32))"`),
  chạy sau reverse proxy có TLS, `GOLD_HOST=0.0.0.0`, xem `docker-compose.yml`.
- Multi-worker: chạy 1 container poller (`GOLD_ENABLE_POLLER=true`) + N container API
  (`GOLD_ENABLE_POLLER=false`, chung volume DB). Lưu ý: WebSocket broadcast nằm trong RAM
  từng worker nên cần sticky session ở proxy, hoặc chấp nhận mỗi client chỉ nhận tick của worker mình nối.
- **Giá vàng chỉ mang tính tham khảo, không phải lời khuyên đầu tư.**
