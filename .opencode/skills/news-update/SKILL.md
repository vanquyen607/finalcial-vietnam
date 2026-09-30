---
name: news-update
description: Thu thập tin tức mới từ CafeF/Vietstock/VNExpress, deduplicate với archive, chỉ hiển thị tin chưa từng thấy. Dùng khi user muốn cập nhật tin tức mới nhất mà không bị lặp lại tin cũ.
argument-hint: "[SYMBOL]"
allowed-tools: Bash
---

# Skill: News Update — Tin tức mới (không trùng lặp)

## Cách chạy

Chạy 1 lệnh duy nhất:

```
Bash("cd /home/hieutran/projects/tam/stock-trader && python3 scripts/news_update.py")
```

Nếu có SYMBOL (lọc tin theo mã):

```
Bash("cd /home/hieutran/projects/tam/stock-trader && python3 scripts/news_update.py VNM")
```

## Script tự động thực hiện

1. Đọc `data/news_archive.json` (tạo mới nếu chưa có)
2. Fetch tin từ CafeF, Vietstock, VNExpress qua scraper trực tiếp
3. Dedup: so sánh `title.lower().strip()` với archive + intra-batch dedup
4. Append tin mới vào archive, giữ max 2000 bài
5. Ghi lại archive
6. Output ra stdout theo format chuẩn

## Format đầu ra

### ⚠️ QUY TẮC BẮT BUỘC:
1. **KHÔNG dùng markdown link** `[text](url)` — Telegram không render được.
2. **PHẢI có plain text URL** cho mỗi tin (paste URL trực tiếp).
3. **PHẢI list TẤT CẢ tin mới** — KHÔNG được tóm tắt/rút gọn thành "X tin nổi bật". Mỗi tin mới = 1 bullet.
4. Nếu >15 tin mới: list đủ 15 tin đầu, cuối ghi "... và N tin khác đã lưu vào archive".

### Output mẫu:
```
📰 NEWS UPDATE
🆕 {N} tin mới  |  📦 Archive: {total} bài

• Tóm tắt ngắn 1 câu
  https://cafef.vn/article/123 (CafeF)
• Tóm tắt ngắn 1 câu
  https://vietstock.vn/article/456 (Vietstock)
• Tóm tắt ngắn 1 câu
  https://vnexpress.net/article/789 (VNExpress)
[... list TẤT CẢ tin mới, tối đa 15 ...]

... và {N-15} tin khác đã lưu vào archive.  ← khi N > 15

✅ Không có tin mới — tất cả đã đọc.     ← khi N = 0
```

## Xử lý lỗi

- `data/news_archive.json` không tồn tại → tạo mới với `[]`
- Deps chưa cài → script tự dùng venv của vn-stock-trader (`.venv/bin/python3`)
- Source lỗi → bỏ qua source đó, tiếp tục các source còn lại
