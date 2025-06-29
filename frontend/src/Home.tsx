import axios from "axios";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

const Home = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tickers, setTickers] = useState<{ name: string }[]>([]);
  const [inputValue, setInputValue] = useState(""); // 현재 인풋값

  useEffect(() => {
    const fetchData = async () => {
      try {
        await axios.get("/login/auth", { withCredentials: true });
        const res = await axios.get("/tickers", { withCredentials: true });
        setTickers(res.data); // res.data가 [{name: 'BTC'}, ...] 형태라고 가정
        setLoading(false);
      } catch (err) {
        if (axios.isAxiosError(err)) {
          if (err.response && err.response.status === 401) {
            navigate("/login", { replace: true });
          }
        } else {
          console.error("Unknown error:", err);
          setLoading(false);
        }
      }
    };
    fetchData();
  }, [navigate]);

  const handleExclude = async () => {
    if (!inputValue) return;
    try {
      await axios.post(
        `/tickers/exclude?name=${encodeURIComponent(inputValue)}`,
        {},
        { withCredentials: true }
      );
      alert(`'${inputValue}' 감시제외 요청 완료`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.response && err.response.status === 401) {
          navigate("/login", { replace: true });
        } else {
          alert(
            `오류 발생: ${err.response?.data?.message || "알 수 없는 오류"}`
          );
        }
      } else {
        console.error("Unknown error:", err);
        alert("알 수 없는 오류가 발생했습니다.");
      }
    }
  };

  if (loading) return <div>로딩 중...</div>;
  return (
    <div>
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        sx={{ width: 400, marginTop: 3 }}
      >
        <Autocomplete
          options={tickers}
          getOptionLabel={(option) =>
            typeof option === "string" ? option : option.name
          }
          inputValue={inputValue}
          onInputChange={(_, newInputValue) => setInputValue(newInputValue)}
          renderInput={(params) => (
            <TextField
              {...params}
              label="티커를 입력하세요"
              variant="outlined"
            />
          )}
          sx={{ flex: 1 }}
          freeSolo
        />
        <Button variant="outlined" onClick={handleExclude}>
          감시제외
        </Button>
      </Stack>
    </div>
  );
};

export default Home;
