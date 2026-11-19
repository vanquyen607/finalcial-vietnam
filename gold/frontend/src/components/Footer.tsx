import { Link } from "react-router-dom";
import Logo from "./Logo";

const STOCKS_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8100/"
    : "https://finalcial-vietnam.onrender.com/";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="site-footer__grid">
          <div className="site-footer__brand">
            <Link to="/" className="site-footer__logo">
              <Logo size={26} />
              <span>Aurum Terminal</span>
            </Link>
            <p className="site-footer__desc">
              Theo dõi giá vàng, bạc, xăng dầu và tỷ giá ngoại tệ theo thời gian thực.
            </p>
            <p className="meta">
              Giá chỉ mang tính tham khảo, không phải lời khuyên đầu tư.
            </p>
          </div>

          <div className="site-footer__col">
            <h2 className="site-footer__heading">Thị trường</h2>
            <nav className="site-footer__links" aria-label="Liên kết thị trường">
              <Link to="/">Bảng giá vàng</Link>
              <Link to="/silver">Giá bạc</Link>
              <Link to="/fuel">Giá xăng dầu</Link>
              <Link to="/fx">Tỷ giá ngoại tệ</Link>
            </nav>
          </div>

          <div className="site-footer__col">
            <h2 className="site-footer__heading">Công cụ</h2>
            <nav className="site-footer__links" aria-label="Liên kết công cụ">
              <Link to="/chart">Biểu đồ kỹ thuật</Link>
              <Link to="/news">Tin tức thị trường</Link>
              <Link to="/alerts">Cảnh báo giá</Link>
              <Link to="/settings">Cài đặt</Link>
            </nav>
          </div>
        </div>

        <div className="site-footer__bottom">
          <span className="meta">
            Nguồn: VangToday · Simplize · Ngọc Thẩm · TradingView · Petrolimex · WebGia
          </span>
          <div className="site-footer__right">
            <a className="footer-link" href={STOCKS_URL} title="App phân tích cổ phiếu VN">
              Phân tích cổ phiếu VN →
            </a>
            <span className="meta">© {new Date().getFullYear()} Aurum Terminal</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
