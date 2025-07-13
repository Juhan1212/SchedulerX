import axios from "axios";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import CompChart from "../components/chart/CompChart";
import "../assets/styles/routes/trade.scss";

// Add TradingView type to window
declare global {
  interface Window {
    TradingView?: {
      widget: (options: Record<string, unknown>) => void;
    };
  }
}

const Home = () => {
  const navigate = useNavigate();
  // const [loading, setLoading] = useState(true);
  // const [tickers, setTickers] = useState<{ name: string }[]>([]);
  // const [loading] = useState(true);
  const [tickers] = useState<{ name: string }[]>([]);
  const [inputValue, setInputValue] = useState(""); // 현재 인풋값
  const [selectedTicker, setSelectedTicker] = useState<string | null>("XRP"); // 감시할 티커 선택

  // useEffect(() => {
  //   const fetchData = async () => {
  //     try {
  //       const res = await axios.get("/api/tickers", { withCredentials: true });
  //       console.log(res);
  //       setTickers(res.data); // res.data가 [{name: 'BTC'}, ...] 형태라고 가정
  //       setLoading(false);
  //     } catch (err) {
  //       if (axios.isAxiosError(err)) {
  //         if (err.response && err.response.status === 401) {
  //           navigate("/login", { replace: true });
  //         }
  //       } else {
  //         console.error("Unknown error:", err);
  //         setLoading(false);
  //       }
  //     }
  //   };
  //   fetchData();
  // }, [navigate]);

  // 선택된 티커가 변경될 때마다 차트 업데이트
  useEffect(() => {}, [selectedTicker]);

  const handleExclude = async () => {
    if (!inputValue) return;
    try {
      await axios.post(
        `/api/tickers/exclude?name=${encodeURIComponent(inputValue)}`,
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

  // if (loading) return <div>로딩 중...</div>;
  return (
    <div>
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        sx={{ width: 400, marginTop: 3 }}
      >
        {/* 감시제외 Autocomplete */}
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
        />
        <Button variant="outlined" onClick={handleExclude}>
          감시제외
        </Button>
      </Stack>
      {/* 감시할 티커 Autocomplete */}
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
          // value={tickers.find((t) => t.name === selectedTicker) || null}
          onInputChange={(_, newInputValue) => {
            const match = tickers.find((t) => t.name === newInputValue);
            if (match) setSelectedTicker(match.name);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label="감시할 티커 선택"
              variant="outlined"
            />
          )}
          sx={{ flex: 1 }}
        />
      </Stack>
      {/* 선택된 티커의 차트 표시 */}
      {selectedTicker && (
        <CompChart
          exchange1="UPBIT"
          exchange2="GATEIO"
          symbol={selectedTicker} // 선택된 티커가 없으면 기본값 사용
          interval="1m"
        />
      )}
    </div>
  );
};

export default Home;
