import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import { MarketProvider } from "./state/Market";
import "./styles/tokens.css";
import "./styles/app.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <MarketProvider>
          <App />
        </MarketProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);

// Đăng ký PWA service worker (chỉ khi có file, tránh lỗi lúc dev).
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
