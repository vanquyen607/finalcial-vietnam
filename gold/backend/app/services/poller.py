from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from ..config import settings
from ..db import db
from ..providers import GoldProvider, MockProvider, VangTodayProvider
from ..providers.fx import fetch_usd_vnd
from ..symbols import GOLD_TYPES
from . import alerts as alerts_svc
from . import news as news_svc
from . import notify as notify_svc
from .broadcast import hub

log = logging.getLogger("aurum.poller")

AUX_HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)"}


def build_provider(name: str) -> GoldProvider:
    if name == "mock":
        return MockProvider()
    return VangTodayProvider()


class Poller:
    """Vòng lặp lấy giá -> persist -> broadcast. Có fallback sang mock khi nguồn chết."""

    def __init__(self) -> None:
        self.provider: GoldProvider = build_provider(settings.provider)
        self.fallback = MockProvider()
        self.latest: dict[str, dict] = {}
        self.status: dict[str, Any] = {
            "state": "starting", "source": self.provider.name,
            "last_success": None, "last_error": None, "polls": 0, "clients": 0,
        }
        self._task: asyncio.Task | None = None
        self._history_task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        # Client dùng chung cho tác vụ phụ (tỷ giá, tin tức) — lỗi không ảnh hưởng giá.
        self._aux = httpx.AsyncClient(headers=AUX_HEADERS, follow_redirects=True)
        self._last_fx = 0
        self._last_news = 0
        # Quan sát vận hành cho /api/metrics + báo Telegram.
        self.metrics: dict[str, Any] = {
            "poll_errors": 0,
            "last_poll_ms": None,
            "provider_errors": {},
            "fx": {"ok": 0, "err": 0, "last_ok": None, "last_err": None},
            "news": {"ok": 0, "err": 0, "last_ok": None, "last_err": None},
            "error_since": None,
            "error_notified": False,
        }

    # --- helpers ---
    def _to_rows(self, quotes) -> list[dict]:
        now = int(time.time())
        return [{
            "ts": q.updated_at or now, "code": q.code, "name": q.name,
            "buy": q.buy, "sell": q.sell, "change_buy": q.change_buy,
            "change_sell": q.change_sell, "unit": q.unit, "per": q.per, "source": q.source,
        } for q in quotes]

    @staticmethod
    def _snapshot(rows: list[dict]) -> dict[str, dict]:
        return {r["code"]: r for r in rows}

    async def _fetch(self) -> tuple[list[dict], str]:
        try:
            quotes = await self.provider.fetch_current()
            return self._to_rows(quotes), self.provider.name
        except Exception as exc:  # noqa: BLE001 - provider lỗi là bình thường
            log.warning("provider %s lỗi: %s -> dùng mock", self.provider.name, exc)
            self.status["last_error"] = f"{type(exc).__name__}: {exc}"
            errs = self.metrics["provider_errors"]
            errs[self.provider.name] = errs.get(self.provider.name, 0) + 1
            quotes = await self.fallback.fetch_current()
            return self._to_rows(quotes), self.fallback.name

    def _check_error_streak(self, now: int, failed: bool) -> str | None:
        """Theo dõi nguồn chết liên tục. Trả về 'alert' | 'recovered' | None."""
        if failed:
            if self.metrics["error_since"] is None:
                self.metrics["error_since"] = now
            if (not self.metrics["error_notified"]
                    and now - self.metrics["error_since"] >= settings.telegram_alert_after_sec):
                self.metrics["error_notified"] = True
                return "alert"
            return None
        if self.metrics["error_notified"]:
            self.metrics["error_since"] = None
            self.metrics["error_notified"] = False
            return "recovered"
        self.metrics["error_since"] = None
        return None

    # --- main loop ---
    async def tick(self) -> dict[str, Any]:
        started = time.perf_counter()
        rows, source = await self._fetch()
        now = int(time.time())
        prev = self.latest
        changed = [r for r in rows if r["code"] not in prev
                   or prev[r["code"]]["buy"] != r["buy"]
                   or prev[r["code"]]["sell"] != r["sell"]]

        # Dữ liệu mock chỉ để UI không chết — KHÔNG persist vào DB, KHÔNG đánh alert,
        # để lịch sử/biểu đồ không bao giờ lẫn giá giả.
        is_mock = source == self.fallback.name
        self.latest = self._snapshot(rows)
        if not is_mock:
            db.insert_quotes(rows)

        self.status.update(state="live", source=source, last_success=now,
                           polls=self.status["polls"] + 1, clients=hub.count)
        self.metrics["last_poll_ms"] = round((time.perf_counter() - started) * 1000, 1)

        # Nguồn chính chết liên tục -> báo Telegram một lần, báo hồi phục khi sống lại.
        notice = self._check_error_streak(now, is_mock)
        if notice == "alert":
            await notify_svc.send_telegram(
                self._aux, settings.telegram_bot_token, settings.telegram_chat_id,
                f"Aurum: nguồn giá <b>{self.provider.name}</b> chết liên tục, đang chạy mock.")
        elif notice == "recovered":
            await notify_svc.send_telegram(
                self._aux, settings.telegram_bot_token, settings.telegram_chat_id,
                f"Aurum: nguồn giá <b>{self.provider.name}</b> đã hồi phục.")

        events: list[dict] = []
        if changed and not is_mock:
            events = alerts_svc.evaluate(self.latest)
        # Push snapshot MỖI tick (kể cả khi giá chưa đổi) → UI luôn có nhịp mới.
        msg = {"type": "quotes", "ts": now, "source": source,
               "changed": [r["code"] for r in changed],
               "quotes": rows}
        await hub.broadcast(msg, topic="quote")
        for ev in events:
            await hub.broadcast(ev, topic="alert")
        await hub.broadcast({"type": "status", **self.status}, topic="status")

        # Dọn tick cũ
        if self.status["polls"] % 20 == 0:
            db.prune_quotes(now - settings.history_days * 86_400)
            db.prune_fx(now - 7 * 86_400)

        await self._maybe_refresh_aux(now)
        return {"changed": len(changed), "events": len(events), "source": source}

    async def _maybe_refresh_aux(self, now: int) -> None:
        """Làm mới tỷ giá + tin tức theo chu kỳ riêng; lỗi thì bỏ qua."""
        if now - self._last_fx >= settings.fx_interval:
            self._last_fx = now
            try:
                got = await fetch_usd_vnd(self._aux)
                if got:
                    db.insert_fx(got[0], got[1])
                    self.metrics["fx"]["ok"] += 1
                    self.metrics["fx"]["last_ok"] = now
                else:
                    raise RuntimeError("mọi nguồn tỷ giá đều chết")
            except Exception:  # noqa: BLE001
                self.metrics["fx"]["err"] += 1
                self.metrics["fx"]["last_err"] = now
                log.exception("refresh fx lỗi")
        if now - self._last_news >= settings.news_interval:
            self._last_news = now
            try:
                await news_svc.refresh_news(self._aux)
                self.metrics["news"]["ok"] += 1
                self.metrics["news"]["last_ok"] = now
            except Exception:  # noqa: BLE001
                self.metrics["news"]["err"] += 1
                self.metrics["news"]["last_err"] = now
                log.exception("refresh news lỗi")

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001
                self.metrics["poll_errors"] += 1
                self.status.update(state="error", last_error=f"{type(exc).__name__}: {exc}")
                log.exception("tick lỗi")
                await hub.broadcast({"type": "status", **self.status}, topic="status")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.poll_interval)
            except asyncio.TimeoutError:
                pass

    async def _history_loop(self) -> None:
        """Gom lịch sử theo ngày cho biểu đồ dài hạn."""
        while not self._stop.is_set():
            try:
                await self.refresh_history()
            except Exception:  # noqa: BLE001
                log.exception("refresh_history lỗi")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=600)
            except asyncio.TimeoutError:
                pass

    async def refresh_history(self) -> int:
        total = 0
        for meta in GOLD_TYPES:
            code = meta["code"]
            try:
                rows = await self.provider.fetch_history(code, settings.history_days)
            except NotImplementedError:
                break
            except Exception as exc:  # noqa: BLE001
                log.debug("history %s lỗi: %s", code, exc)
                continue
            payload = [{"code": code, **r} for r in rows if r.get("date")]
            db.upsert_daily(payload)
            total += len(payload)
            await asyncio.sleep(0.35)  # tôn trọng rate limit
        return total

    # --- lifecycle ---
    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="aurum-poller")
        self._history_task = asyncio.create_task(self._history_loop(), name="aurum-history")
        log.info("poller started (interval=%ss, provider=%s)",
                 settings.poll_interval, self.provider.name)

    async def stop(self) -> None:
        self._stop.set()
        for task in (self._task, self._history_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await self.provider.aclose()
        await self._aux.aclose()


poller = Poller()
