import { useEffect, useState } from "react";
import { api, getApiToken, setApiToken } from "../lib/api";
import { fmtClock } from "../lib/format";
import { useMarket } from "../state/Market";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function Settings() {
  const { status, connected, quoteList, refresh } = useMarket();
  const [health, setHealth] = useState<{ clients: number; status: { polls?: number } } | null>(null);
  const [installEvt, setInstallEvt] = useState<BeforeInstallPromptEvent | null>(null);
  const [notify, setNotify] = useState<string>("—");
  const [installed, setInstalled] = useState(false);
  const [token, setToken] = useState(() => getApiToken());
  const [tokenSaved, setTokenSaved] = useState(false);

  const saveToken = () => {
    const v = token.trim();
    setApiToken(v);
    setToken(v);
    setTokenSaved(true);
    window.setTimeout(() => setTokenSaved(false), 1500);
  };

  useEffect(() => {
    void api.health().then(setHealth).catch(() => setHealth(null));
    const id = window.setInterval(() => {
      void api.health().then(setHealth).catch(() => undefined);
    }, 15_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setInstallEvt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setInstallEvt(null);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    if ("Notification" in window) setNotify(Notification.permission);
    if (window.matchMedia("(display-mode: standalone)").matches) setInstalled(true);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const install = async () => {
    if (!installEvt) return;
    await installEvt.prompt();
    await installEvt.userChoice;
    setInstallEvt(null);
  };

  const askNotify = async () => {
    if (!("Notification" in window)) return;
    const r = await Notification.requestPermission();
    setNotify(r);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page__title">Cài đặt</h1>
          <p className="page__sub">Aurum Terminal 1.0.0 · theo dõi giá vàng realtime</p>
        </div>
        <div className="page-head__actions">
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới dữ liệu
          </button>
        </div>
      </div>

      <div className="split">
        <section className="panel">
          <div className="panel__head">
            <span className="panel__title">Nguồn dữ liệu</span>
          </div>
          <div className="panel__body">
            <div className="list-row">
              <div>
                <div className="list-row__name">Nguồn giá</div>
                <div className="list-row__meta">
                  {status.source === "mock" ? "MOCK (MÔ PHỎNG)" : (status.source || "…").toUpperCase()}
                </div>
              </div>
              <span
                className={`chip ${
                  status.state === "live" ? "chip--up" : status.state === "error" ? "chip--down" : "chip--flat"
                }`}
              >
                {status.state.toUpperCase()}
              </span>
            </div>

            <div className="list-row">
              <div>
                <div className="list-row__name">WebSocket</div>
                <div className="list-row__meta">{connected ? "ĐANG MỞ" : "NGẮT — TỰ KẾT NỐI LẠI"}</div>
              </div>
              <span className={`chip ${connected ? "chip--up" : "chip--down"}`}>
                {connected ? "LIVE" : "OFF"}
              </span>
            </div>

            <div className="list-row">
              <div>
                <div className="list-row__name">Lần cập nhật cuối</div>
                <div className="list-row__meta">
                  {status.last_success ? fmtClock(status.last_success) : "—"} · {status.polls ?? 0} LẦN
                  {health ? ` · ${health.clients} CLIENT` : ""}
                </div>
              </div>
              <span className="mono">{quoteList.length}</span>
            </div>

            {status.last_error && (
              <div className="list-row">
                <div>
                  <div className="list-row__name down">Lỗi gần nhất</div>
                  <div className="list-row__meta">{status.last_error}</div>
                </div>
              </div>
            )}
          </div>
        </section>

        <div>
          <section className="panel">
            <div className="panel__head">
              <span className="panel__title">Thông báo</span>
            </div>
            <div className="panel__body">
              <div className="list-row">
                <div>
                  <div className="list-row__name">Thông báo trình duyệt</div>
                  <div className="list-row__meta">TRẠNG THÁI: {String(notify).toUpperCase()}</div>
                </div>
                <button className="chip chip--up" onClick={() => void askNotify()}>
                  {notify === "granted" ? "ĐÃ BẬT" : "BẬT"}
                </button>
              </div>
              <p className="meta" style={{ marginTop: 12 }}>
                QUẢN LÝ CẢNH BÁO TẠI <a href="/alerts" className="up">TRANG CẢNH BÁO</a>
              </p>
            </div>
          </section>

          <section className="panel">
            <div className="panel__head">
              <span className="panel__title">Ứng dụng</span>
            </div>
            <div className="panel__body">
              <div className="list-row">
                <div>
                  <div className="list-row__name">Cài đặt màn hình chính</div>
                  <div className="list-row__meta">
                    {installed
                      ? "ĐÃ CÀI — CHẠY OFFLINE"
                      : "THÊM VÀO MÀN HÌNH CHÍNH ĐỂ CHẠY NHƯ APP"}
                  </div>
                </div>
                {!installed && installEvt && (
                  <button className="chip chip--up" onClick={() => void install()}>
                    CÀI
                  </button>
                )}
              </div>
              <div className="list-row">
                <div>
                  <div className="list-row__name">Phiên bản</div>
                  <div className="list-row__meta">1.0.0 · PWA · REACT + FASTAPI + SQLITE</div>
                </div>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel__head">
              <span className="panel__title">Bảo mật API</span>
              <span className={`chip ${token ? "chip--up" : "chip--flat"}`}>
                {token ? "ĐÃ ĐẶT" : "CHƯA ĐẶT"}
              </span>
            </div>
            <div className="panel__body">
              <p className="meta" style={{ marginTop: 0, lineHeight: 1.7 }}>
                SERVER ĐẶT <span className="mono">GOLD_API_TOKEN</span> THÌ DÁN VÀO ĐÂY —
                PHẦN MỀM SẼ GỬI HEADER <span className="mono">X-API-TOKEN</span> KHI
                TẠO/XÓA/BẬT-TẮT CẢNH BÁO. BỎ TRỐNG NẾU SERVER KHÔNG BẬT.
              </p>
              <div className="list-row">
                <label className="field" style={{ flex: 1, marginBottom: 0 }}>
                  <span>API token</span>
                  <input
                    type="password"
                    value={token}
                    autoComplete="off"
                    spellCheck={false}
                    placeholder="dán GOLD_API_TOKEN ở đây"
                    onChange={(e) => setToken(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveToken();
                    }}
                  />
                </label>
                <div className="row">
                  <button className="chip chip--up" onClick={saveToken}>
                    {tokenSaved ? "ĐÃ LƯU" : "LƯU"}
                  </button>
                  {token && (
                    <button
                      className="chip chip--flat"
                      onClick={() => {
                        setApiToken("");
                        setToken("");
                      }}
                    >
                      XÓA
                    </button>
                  )}
                </div>
              </div>
            </div>
          </section>

          <p className="meta" style={{ marginTop: 18, lineHeight: 1.8 }}>
            GIÁ VÀNG CHỈ MANG TÍNH THAM KHẢO, KHÔNG PHẢI LỜI KHUYÊN ĐẦU TƯ.
            <br />
            DỮ LIỆU: VANG.TODAY · SIMPLIZE · NGỌC THẨM · XAUUSD SPOT.
          </p>
        </div>
      </div>
    </div>
  );
}
