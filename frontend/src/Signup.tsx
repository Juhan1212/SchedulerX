import React, { useState } from "react";
import "./Signup.css";
import CryptoJS from "crypto-js";

class SignupError extends Error {
  code?: string;
  field?: string;
  constructor(message: string, code?: string, field?: string) {
    super(message);
    this.name = "SignupError";
    this.code = code;
    this.field = field;
  }
}

const Signup: React.FC = () => {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState<SignupError | null>(null);
  const [success, setSuccess] = useState(false);

  // 비밀번호 일치 여부 실시간 체크
  const isPasswordMatch =
    form.confirmPassword.length > 0 && form.password !== form.confirmPassword;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError(null);
    setSuccess(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    if (form.password !== form.confirmPassword) {
      setError(new SignupError("비밀번호가 일치하지 않습니다."));
      return;
    }
    try {
      // 비밀번호를 SHA-256으로 암호화
      const encryptedPassword = CryptoJS.SHA256(form.password).toString();
      const response = await fetch("/signup", {
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
          new SignupError(
            data.message || "회원가입 실패",
            data.code,
            data.field
          )
        );
        return;
      }
      setSuccess(true);
    } catch (err) {
      if (err instanceof SignupError) {
        setError(err);
      } else if (err instanceof Error) {
        setError(new SignupError(err.message || "네트워크 오류"));
      } else {
        setError(new SignupError("알 수 없는 오류가 발생했습니다."));
      }
    }
  };

  return (
    <div className="signup-container">
      <form className="signup-form" onSubmit={handleSubmit}>
        <h2>회원가입</h2>
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
        <input
          type="password"
          name="confirmPassword"
          placeholder="비밀번호 확인"
          value={form.confirmPassword}
          onChange={handleChange}
          required
        />
        {isPasswordMatch && (
          <div className="error-message">비밀번호가 일치하지 않습니다.</div>
        )}
        {error && <div className="error-message">{error.message}</div>}
        {success && <div className="success-message">회원가입 성공!</div>}
        <button type="submit">가입하기</button>
      </form>
    </div>
  );
};

export default Signup;
