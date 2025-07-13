import Signup from "./pages/Signup";
import Login, { action as loginAction } from "./pages/Login";
import Home from "./pages/Home";
import MyPage from "./pages/Mypage";
import NetworkErrorBoundary from "./pages/NetworkErrorBoundary";

// App 컴포넌트는 children 라우트만 반환
export const routes = [
  {
    path: "/",
    element: <Home />,
  },
  {
    path: "/signup",
    element: <Signup />,
  },
  {
    path: "/login",
    element: <Login />,
    action: loginAction,
    errorElement: <NetworkErrorBoundary />, // 네트워크 에러 바운더리
  },
  {
    path: "/my/*",
    element: <MyPage />,
  },
  // 필요시 다른 라우트도 추가 가능
];

export default routes;
