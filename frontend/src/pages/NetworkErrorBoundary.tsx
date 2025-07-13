import React from "react";
import { useNavigate } from "react-router-dom";
import authContainerStyles from "../assets/styles/shared/authContainer.module.scss";
import Icon from "../components/shared/SVGIcon";

const NetworkErrorBoundary: React.FC = () => {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate("/");
  };

  return (
    <div className={authContainerStyles["auth-container"]}>
      <main className={authContainerStyles["main"]}>
        <section className={authContainerStyles["auth-form"]}>
          <div className={authContainerStyles["form-inner-wrapper"]}>
            <Icon
              className={authContainerStyles["icon-error"]}
              type="error"
            />
            <h2 className={authContainerStyles["title"]}>
              네트워크 오류가 발생했습니다
            </h2>
            <p className={authContainerStyles["subtitle"]}>
              서버와의 통신 중 문제가 발생했습니다.<br />
              잠시 후 다시 시도해 주세요.
            </p>
            <button
              className={authContainerStyles["auth-submit-btn"]}
              onClick={handleGoHome}
            >
              홈으로 이동
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};

export default NetworkErrorBoundary;
