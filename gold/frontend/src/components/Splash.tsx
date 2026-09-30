import Logo from "./Logo";

export default function Splash({ hidden }: { hidden: boolean }) {
  return (
    <div className={`splash ${hidden ? "splash--hide" : ""}`}>
      <div className="splash__mark">
        <Logo size={84} />
      </div>
      <div className="splash__title">Aurum Terminal</div>
      <div className="meta">GIÁ VÀNG REALTIME</div>
      <div className="splash__bar">
        <i />
      </div>
    </div>
  );
}
