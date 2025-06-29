import { BrowserRouter, Routes, Route } from "react-router-dom";
import Signup from "./Signup";
import "./App.css";
import Login from "./Login";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        {/* 필요시 다른 라우트도 추가 가능 */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;
