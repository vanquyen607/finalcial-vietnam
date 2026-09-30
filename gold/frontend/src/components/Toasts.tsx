import { useMarket } from "../state/Market";

export default function Toasts() {
  const { toasts, dismissToast } = useMarket();
  if (!toasts.length) return null;
  return (
    <div className="toasts">
      {toasts.map((t) => (
        <button
          key={t.id}
          className={`toast ${t.kind === "alert" ? "toast--alert" : ""}`}
          onClick={() => dismissToast(t.id)}
        >
          {t.message}
        </button>
      ))}
    </div>
  );
}
