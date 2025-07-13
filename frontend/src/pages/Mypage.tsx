import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Gnb from "../components/shared/Gnb";
import Footer from "../components/shared/Footer";

// const MY_MENU = [
//   {
//     title: "비밀번호 변경",
//     to: "password",
//     imageId: "v1741931810/lock_tcecph.png",
//   },
//   {
//     title: "거래소 연동",
//     to: "connect",
//     imageId: "v1741931810/manage_t8upd8.png",
//   },
//   {
//     title: "친구 초대 및 관리",
//     to: "friends",
//     imageId: "v1741934852/people_pwpa6z.png",
//   },
//   {
//     title: "기타 설정",
//     to: "settings",
//     imageId: "v1741931810/docs_nq5oou.png",
//   },
// ] as const;

export default function MyPage() {
  // const [user, setUser] = useState({ username: "test" });
  // const location = useLocation();
  const navigate = useNavigate();
  // const isRootPath = location.pathname === "/my";

  useEffect(() => {
    // Fetch user info from FastAPI backend
    // fetch("/api/user/me", { credentials: "include" })
    //   .then((res) => {
    //     if (res.status === 401) {
    //       navigate("/login");
    //       return null;
    //     }
    //     return res.json();
    //   })
    //   .then((data) => setUser(data))
    //   .catch(() => navigate("/login"));
  }, [navigate]);

  // if (!user) return null;
  // const { username } = user;

  // console.log("MyPage username:", username);

  // const handleLogout = async (e: React.FormEvent) => {
  //   e.preventDefault();
  //   await fetch("/api/logout", { method: "POST", credentials: "include" });
  //   navigate("/login");
  // };

  return (
    <div className="page-container">
      <Gnb username={"test"} />
      <div className="contents-container">
        {/* {isRootPath ? (
          <>
            <MyPageHeader username={username} />
            <section className="menu-links-wrapper">
              <ul className="menu-links">
                {MY_MENU.map((menuItem) => (
                  <li key={menuItem.title}>
                    <Link to={menuItem.to} className="menu-link-btn">
                      <div className="menu-link">
                        <p>{menuItem.title}</p>
                        <Icon type="arrow" />
                      </div>
                      <CloudinaryImage
                        publicId={menuItem.imageId}
                        alt={menuItem.title}
                        className={`img-${menuItem.to}`}
                      />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
            <form onSubmit={handleLogout} className="my-logout-form">
              <button className="my-logout-btn">로그아웃</button>
            </form>
          </>
        ) : (
          <Outlet />
        )} */}
      </div>
      <Footer />
    </div>
  );
}
