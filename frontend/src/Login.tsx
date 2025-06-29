import React, { useState } from "react";
import "./Signup.css";
import CryptoJS from "crypto-js";

class LoginError extends Error {
  code?: string;
  field?: string;
  constructor(message: string, code?: string, field?: string) {
    super(message);
    this.name = "LoginError";
    this.code = code;
    this.field = field;
  }
}

const Login: React.FC = () => {
  const [form, setForm] = useState({
    email: "",
    password: "",
  });
  const [error, setError] = useState<LoginError | null>(null);
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError(null);
    setSuccess(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    try {
      // 비밀번호를 SHA-256으로 암호화
      const encryptedPassword = CryptoJS.SHA256(form.password).toString();
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          password_hash: encryptedPassword,
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        setError(
          new LoginError(
            data.message || "로그인 실패",
            data.code,
            data.field
          )
        );
        return;
      }
      setSuccess(true);
    } catch (err) {
      if (err instanceof LoginError) {
        setError(err);
      } else if (err instanceof Error) {
        setError(new LoginError(err.message || "네트워크 오류"));
      } else {
        setError(new LoginError("알 수 없는 오류가 발생했습니다."));
      }
    }
  };

  return (
    <div className="signup-container">
      <form className="signup-form" onSubmit={handleSubmit}>
        <h2>로그인</h2>
        <input
          type="email"
          name="email"
          placeholder="이메일"
          value={form.email}
          onChange={handleChange}
          required
        />
        <input
          type="password"
          name="password"
          placeholder="비밀번호"
          value={form.password}
          onChange={handleChange}
          required
        />
        {error && <div className="error-message">{error.message}</div>}
        {success && <div className="success-message">로그인 성공!</div>}
        <button type="submit">로그인</button>
      </form>
    </div>
  );
};

export default Login;
