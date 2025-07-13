import { Link } from "react-router-dom";
import CloudinaryImage from "./CloudinaryImage";
export default function Footer() {
  return (
    <footer className="footer-container">
      <div className="footer">
        <CloudinaryImage
          publicId="v1741746786/logo_yd08ed.png"
          alt="logo"
          className="footer-logo"
        />

        <div className="company-info">
          <p className="company-desc">No.1 Algorithmic Quant Trading Service</p>
          <p className="company-name">ULTIMATE TRADING</p>
          <p>
            이메일 : admin@ultimatetrading.net
            <br />
            @copyright 2024 | Ultimate Trading | All Right Reserved
          </p>
          {/* <p>
            대표이사 : 구자운 | 사업자등록번호 : 587-88-02823
            <br />
            주소 : 서울특별시 강남구 강남대로 100길 601호
            <br />
            이메일 : admin@ultimatetrading.net
          </p> */}

          <p className="links">
            <Link to="/terms">이용약관</Link>{" "}
            <Link to="/privacy">개인정보처리방침</Link>
          </p>
        </div>
      </div>
    </footer>
  );
}
