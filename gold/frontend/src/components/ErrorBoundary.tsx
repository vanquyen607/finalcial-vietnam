import { Component } from "react";
import type { ReactNode } from "react";

interface State {
  failed: boolean;
  detail: string;
}

/** Bắt lỗi render cả cây — thay vì trang trắng, hiện panel + nút tải lại. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false, detail: "" };

  static getDerivedStateFromError(err: unknown): State {
    return { failed: true, detail: err instanceof Error ? err.message : String(err) };
  }

  componentDidCatch(err: unknown): void {
    // eslint-disable-next-line no-console
    console.error("Aurum render error:", err);
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="page">
        <section className="panel">
          <div className="panel__head">
            <span className="panel__title">Ứng dụng gặp lỗi hiển thị</span>
          </div>
          <div className="panel__body">
            <p className="page__sub">{this.state.detail || "Lỗi không xác định."}</p>
            <button className="btn" onClick={() => window.location.reload()}>
              Tải lại trang
            </button>
          </div>
        </section>
      </div>
    );
  }
}
