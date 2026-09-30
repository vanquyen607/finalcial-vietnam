import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { fmtClock, fmtPct, tone } from "../lib/format";
import type { Alert } from "../lib/types";
import { useMarket } from "../state/Market";

const DIRECTIONS: { key: "up" | "down"; label: string }[] = [
  { key: "up", label: "Tăng ≥" },
  { key: "down", label: "Giảm ≥" },
];

export default function Alerts() {
  const { symbols, quotes } = useMarket();
  const [items, setItems] = useState<Alert[]>([]);
  const [code, setCode] = useState("sjc");
  const [direction, setDirection] = useState<"up" | "down">("up");
  const [threshold, setThreshold] = useState("1");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const res = await api.alerts();
      const byCode = Object.fromEntries(symbols.map((s) => [s.code, s.name]));
      setItems(res.items.map((a) => ({ ...a, name: a.name || byCode[a.code] || a.code })));
    } catch (e) {
      setMsg(String(e));
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbols.length]);

  const askNotify = async () => {
    if (!("Notification" in window)) {
      setMsg("Trình duyệt này không hỗ trợ notification.");
      return;
    }
    const res = await Notification.requestPermission();
    setMsg(res === "granted" ? "Đã bật thông báo." : "Bạn chưa cho phép thông báo.");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api.createAlert({
        code,
        direction,
        threshold: Number(threshold) || 1,
        note: note.trim(),
      });
      setNote("");
      setMsg("Đã tạo cảnh báo.");
      await load();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    await api.deleteAlert(id);
    await load();
  };

  const toggle = async (a: Alert) => {
    await api.toggleAlert(a.id, !a.active);
    await load();
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page__title">Cảnh báo giá vàng</h1>
          <p className="page__sub">
            Nhận cảnh báo khi giá biến động vượt ngưỡng trong ngày · mỗi cảnh báo chỉ báo 1 lần
          </p>
        </div>
        <div className="page-head__actions">
          <button className="btn btn--ghost" onClick={() => void askNotify()}>
            Bật thông báo trình duyệt
          </button>
        </div>
      </div>

      <div className="split">
        <section className="panel">
          <div className="panel__head">
            <span className="panel__title">Tạo cảnh báo mới</span>
          </div>
          <div className="panel__body">
            <form onSubmit={submit}>
              <label className="field">
                <span>Loại vàng</span>
                <select value={code} onChange={(e) => setCode(e.target.value)}>
                  {symbols.map((s) => (
                    <option key={s.code} value={s.alias}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </label>

              <div className="row" style={{ gap: 12, alignItems: "flex-end" }}>
                <label className="field" style={{ flex: 1 }}>
                  <span>Điều kiện</span>
                  <select
                    value={direction}
                    onChange={(e) => setDirection(e.target.value as "up" | "down")}
                  >
                    {DIRECTIONS.map((d) => (
                      <option key={d.key} value={d.key}>
                        {d.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field" style={{ flex: 1 }}>
                  <span>Ngưỡng (%)</span>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="100"
                    value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                  />
                </label>
              </div>

              <label className="field">
                <span>Ghi chú (không bắt buộc)</span>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="vd: chốt lời SJC"
                />
              </label>

              <button className="btn btn--primary btn--block" disabled={busy} type="submit">
                {busy ? "Đang tạo…" : "Tạo cảnh báo"}
              </button>
            </form>
            {msg && <p className="meta" style={{ marginTop: 12 }}>{msg}</p>}
          </div>
        </section>

        <section className="panel">
          <div className="panel__head">
            <span className="panel__title">Danh sách cảnh báo · {items.length}</span>
            <span className="meta">MỖI MÃ CHỈ BÁO 1 LẦN / NGÀY</span>
          </div>
          <div className="panel__body">
            {items.length === 0 ? (
              <div className="empty">Chưa có cảnh báo nào.</div>
            ) : (
              items.map((a) => {
                const q = quotes[a.code];
                const prev = q ? q.buy - q.change_buy : 0;
                const pct = q && prev ? (q.change_buy / prev) * 100 : 0;
                return (
                  <div key={a.id} className="list-row">
                    <div>
                      <div className="list-row__name">
                        {a.name}{" "}
                        <span className={a.direction === "up" ? "up" : "down"}>
                          {a.direction === "up" ? "↑ tăng" : "↓ giảm"} ≥ {a.threshold}%
                        </span>
                      </div>
                      <div className="list-row__meta">
                        HIỆN <span className={tone(pct)}>{fmtPct(pct)}</span>
                        {a.note ? ` · ${a.note}` : ""}
                        {a.triggered_at ? ` · ĐÃ KÍCH HOẠT ${fmtClock(a.triggered_at)}` : ""}
                      </div>
                    </div>
                    <div className="row">
                      <button
                        className={`chip ${a.active ? "chip--up" : "chip--flat"}`}
                        onClick={() => void toggle(a)}
                      >
                        {a.active ? "ĐANG BẬT" : "TẠM DỪNG"}
                      </button>
                      <button className="chip chip--down" onClick={() => void remove(a.id)}>
                        XÓA
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
