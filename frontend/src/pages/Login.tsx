import React, { useState, useEffect } from "react";
import CryptoJS from "crypto-js";
import {
  Form,
  Link,
  useActionData,
  useNavigate,
  redirect,
} from "react-router-dom";
import CloudinaryImage from "../components/shared/CloudinaryImage";
import Icon from "../components/shared/SVGIcon";
import authContainerStyles from "../assets/styles/shared/authContainer.module.scss";

class LoginError extends Error {
  code?: string;
  username?: string;
  password?: string;
  constructor(
    message: string,
    code?: string,
    username?: string,
    password?: string
  ) {
    super(message);
    this.name = "LoginError";
    this.code = code;
    this.username = username;
    this.password = password;
  }
}

export async function action({ request }: { request: Request }) {
  const formData = await request.formData();
  const username = formData.get("username") as string;
  const password = formData.get("password") as string;

  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: username,
      password_hash: CryptoJS.SHA256(password).toString(),
    }),
  });

  if (!response.ok) {
    // FastAPI에서 반환한 에러 메시지 파싱
    const data = await response.json();
    // data.detail, response.status 등 사용 가능
    return new LoginError(
      data.detail || "로그인 실패",
      String(response.status),
      username,
      password
    );
  }
  // 성공시 home으로 리다이렉트
  return redirect("/");
}

const Login: React.FC = () => {
  const actionData = useActionData();
  const [error, setError] = useState<LoginError | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // 로그인 상태 확인
    const checkAuth = async () => {
      const res = await fetch("/api/login/auth", { credentials: "include" });
      if (res.ok) {
        navigate("/", { replace: true });
      }
      // 실패 시 아무 동작 안 함
    };
    checkAuth();
  }, [navigate]);

  useEffect(() => {
    if (actionData?.error) {
      setError(actionData.error);
    }
  }, [actionData]);

  return (
    <div className={authContainerStyles["auth-container"]}>
      <main className={authContainerStyles["main"]}>
        <section className={authContainerStyles["visual"]}>
          <h1 className={authContainerStyles["title"]}>
            ULTIMATE
            <br />
            TRADING
            <br />
            HOUSE
          </h1>
          <p className={authContainerStyles["subtitle"]}>
            시장을 이기는 최고의 투자전략,
            <br />
            얼티밋 트레이딩으로 시작하세요!
          </p>
          <div className={authContainerStyles["img-path"]}>
            <CloudinaryImage
              publicId="v1741610385/coins_sysebu.png"
              alt="coins"
              className={authContainerStyles["img-coins"]}
            />
          </div>
        </section>
        <section className={authContainerStyles["auth-form"]}>
          <Form
            action="/login"
            method="post"
            className={authContainerStyles["form"]}
          >
            <div className={authContainerStyles["form-inner-wrapper"]}>
              <Icon
                className={
                  authContainerStyles["icon-symbol"] +
                  " " +
                  authContainerStyles["login-symbol"]
                }
                type="symbol"
              />
              <div className={authContainerStyles["form-content"]}>
                <div className={authContainerStyles["auth-input-group"]}>
                  <label
                    className={authContainerStyles["auth-input-label"]}
                    htmlFor="username"
                  >
                    아이디
                  </label>
                  <div>
                    <input
                      className={authContainerStyles["auth-input"]}
                      id="username"
                      autoFocus={true}
                      placeholder="아이디 입력"
                      name="username"
                      type="text"
                      aria-describedby="username-error"
                    />
                  </div>
                  {error?.username && (
                    <div className={authContainerStyles["error-message"]}>
                      <Icon
                        className={authContainerStyles["icon-error"]}
                        type="error"
                      />
                      {error?.username}
                    </div>
                  )}
                </div>
                <div className={authContainerStyles["auth-input-group"]}>
                  <label
                    className={authContainerStyles["auth-input-label"]}
                    htmlFor="password"
                  >
                    비밀번호
                  </label>
                  <div>
                    <input
                      className={authContainerStyles["auth-input"]}
                      id="password"
                      placeholder="비밀번호 입력"
                      name="password"
                      type="password"
                      // autoComplete="current-password"
                      autoComplete="new-password"
                      aria-describedby="password-error"
                    />
                  </div>
                  {error?.password && (
                    <div className={authContainerStyles["error-message"]}>
                      <Icon
                        className={authContainerStyles["icon-error"]}
                        type="error"
                      />
                      {error?.password}
                    </div>
                  )}
                </div>
                <input type="hidden" name="formType" value="login" />
                <button
                  type="submit"
                  className={authContainerStyles["auth-submit-btn"]}
                >
                  로그인
                </button>
                {/* 비밀번호찾기 페이지 or form 추가 필요 
                <Link
                  to={{
                    pathname: '/find-password',
                  }}
                  className={authContainerStyles["forgot-password"]}
                >
                  비밀번호를 잊어버리셨습니까?
                </Link> */}
              </div>
            </div>
            <Link
              to={{
                pathname: "/register",
              }}
              className={authContainerStyles["link-btn"]}
            >
              회원가입
            </Link>
          </Form>
        </section>
      </main>
    </div>
  );
};

export default Login;
