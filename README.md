# finan

Repo chứa **2 ứng dụng độc lập** (không liên quan nhau), mỗi app nằm gọn trong thư mục riêng.

| Thư mục | Ứng dụng | Công nghệ | Chạy | Deploy |
|---------|----------|-----------|------|--------|
| [`stocks/`](stocks/) | Phân tích cổ phiếu Việt Nam | FastAPI + Vanilla JS (vnstock) | `stocks\PhanTichCK.bat` → http://127.0.0.1:8100 | Render (`phan-tich-co-phieu`) |
| [`gold/`](gold/) | Aurum Terminal — giá vàng realtime | FastAPI + React PWA | `gold\KhoiChay.bat` → http://127.0.0.1:8000 | Local + Cloudflare tunnel |

Chi tiết từng app: xem [`stocks/README.md`](stocks/README.md) và [`gold/README.md`](gold/README.md).

## Cấu trúc repo

```
finan/
├── stocks/          # App cổ phiếu (backend/ frontend/ tests/ scripts/ reports/)
├── gold/            # App giá vàng (backend/ frontend/ scripts/)
├── .opencode/       # Skills cho trợ lý AI (phân tích cổ phiếu)
├── .github/         # CI: keep-alive ping Render (chống cold start)
├── render.yaml      # Cấu hình deploy Render — bắt buộc ở gốc repo, trỏ vào stocks/
├── AGENTS.md        # Hướng dẫn vnstock cho trợ lý AI (tự sinh)
└── README.md        # File này
```

> `render.yaml` phải ở gốc repo vì Render Blueprint chỉ đọc file này từ root. Nó trỏ vào `stocks/` qua `buildCommand`/`startCommand`.

## Ghi chú

- Chạy `stocks`: nhấp `stocks\PhanTichCK.bat`, tắt bằng `stocks\DongPhanTichCK.bat`.
- Chạy `gold`: nhấp `gold\KhoiChay.bat`, tắt bằng `gold\Tat.bat`.
- Cache/CSV/data của cả 2 app đều bị `.gitignore` (chỉ giữ trên máy, không commit).
