import { Form, Link } from "react-router-dom";
import { useState } from "react";
import Icon from "./SVGIcon";

interface GnbProps {
  username: string;
}

export default function Gnb({ username }: GnbProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const closeMenu = () => {
    setIsMenuOpen(false);
  };

  const handleContentClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    e.stopPropagation();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      closeMenu();
    }
    if (e.key === "Enter" || e.key === " ") {
      handleContentClick(e);
    }
  };

  return (
    <nav className="gnb-container">
      <div className="gnb">
        <Link to="/trade" className="symbol-link">
          <Icon type="symbol" className="symbol" />
        </Link>
        <div className="right-section">
          <div className="link-wrapper">
            <Link to="/trade" className="trade-link">
              거래소
            </Link>
            <div className="border-bar" />
            <Link to="/my" className="user-link">
              <div className="icon-wrapper">
                <Icon className="icon-user" type="user" />
              </div>
              {username} 님
            </Link>
          </div>
          <Form action="/logout" method="post">
            <button type="submit" className="logout-btn">
              <Icon className="icon-logout" type="logout" />
            </button>
          </Form>
        </div>
        <button
          type="button"
          className="hamburger-btn"
          onClick={toggleMenu}
          aria-expanded={isMenuOpen}
          aria-label="메뉴 열기"
        >
          <Icon type="hamburger" />
        </button>
        {isMenuOpen && (
          <div
            role="button"
            tabIndex={0}
            className="side-menu"
            onClick={closeMenu}
            onKeyDown={(e) => e.key === "Escape" && closeMenu()}
            aria-label="사이드 메뉴"
          >
            <div
              className="side-menu-content"
              onClick={handleContentClick}
              onKeyDown={handleKeyDown}
              role="menu"
              tabIndex={0}
            >
              <div className="link-menu">
                <Link
                  to="/trade"
                  className="side-menu-link"
                  onClick={toggleMenu}
                  role="menuitem"
                >
                  <Icon type="chart" />
                  거래소
                </Link>
                <Link
                  to="/my"
                  className="side-menu-link"
                  onClick={toggleMenu}
                  role="menuitem"
                >
                  <Icon className="icon-user" type="user" />
                  마이페이지
                </Link>
              </div>
              <Form action="/logout" method="post">
                <button
                  type="submit"
                  className="side-logout-btn"
                  role="menuitem"
                >
                  <Icon type="logout" />
                  로그아웃
                </button>
              </Form>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
