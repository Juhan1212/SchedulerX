import { useEffect, useState } from "react";
import { useCryptoOptionsStore } from "../states/cryptoOptionState";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Stack from "@mui/material/Stack";
import CompChart from "../components/chart/CompChart";
import "../assets/styles/routes/trade.scss";
import { useNavigate } from "react-router-dom";

const exchange1Options = ["UPBIT", "BITHUMB"];
const exchange2Options = ["GATEIO", "BYBIT", "BINANCE", "OKX"];

const Home = () => {
  const [exchange1, setExchange1] = useState<string>("UPBIT");
  const [exchange2, setExchange2] = useState<string>("BYBIT");
  const [tickers, setTickers] = useState<
    { name: string; ex_rate?: string | null }[]
  >([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>("XRP"); // 감시할 티커 선택
  const { addCryptoOption } = useCryptoOptionsStore();
  const navigate = useNavigate();

  useEffect(() => {
    // 공통 티커 데이터 가져오기
    const fetchData = async () => {
      try {
        const res = await fetch(
          `/api/tickers?exchange1=${exchange1}&exchange2=${exchange2}`,
          { credentials: "include" }
        );
        if (!res.ok) {
          // 네트워크 또는 기타 에러
          throw new Error(`Fetch error: ${res.status} ${res.statusText}`);
        }
        const data = await res.json();
        setTickers(data); // data: [{name: 'BTC', ex_rate: '1375'}, ...]
      } catch (err) {
        if (err instanceof TypeError) {
          // 네트워크 에러 (ex: 서버 다운, 인터넷 연결 문제)
          alert("네트워크 오류가 발생했습니다. 인터넷 연결을 확인하세요.");
        } else {
          // 기타 에러
          console.error("Unknown error:", err);
          alert("알 수 없는 오류가 발생했습니다.");
        }
      }
    };

    // WebSocket 연결 함수
    const connectWebSocket = () => {
      // ws:// 또는 wss:// 자동 판별
      const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
      const wsUrl = `${wsProtocol}://${window.location.host}/ws`;
      let socket: WebSocket;
      let reconnectTimeout: NodeJS.Timeout | null = null;

      const connect = () => {
        socket = new window.WebSocket(wsUrl);

        socket.onopen = () => {
          console.log("WebSocket connected");
        };
        socket.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (
              msg.exchange1?.toUpperCase() === exchange1 &&
              msg.exchange2?.toUpperCase() === exchange2 &&
              Array.isArray(msg.results)
            ) {
              console.log(msg.results);
              setTickers((prev) => {
                // prev: 기존 상태, msg.results: 새로 들어온 티커들
                const map = new Map(prev.map((t) => [t.name, t]));
                msg.results.forEach(
                  (item: { name: string; ex_rate?: string | null }) => {
                    map.set(item.name, { ...map.get(item.name), ...item });
                  }
                );
                return Array.from(map.values());
              });
            }
          } catch (e) {
            console.error("WebSocket message parsing error:", e);
          }
        };
        socket.onerror = (err) => {
          console.error("WebSocket error", err);
        };
        socket.onclose = (event) => {
          console.log("WebSocket closed", event.reason);
          // 재연결 로직 (3초 후 재시도)
          if (!event.wasClean) {
            console.log("Reconnecting WebSocket...");
            reconnectTimeout = setTimeout(connect, 3000);
          }
        };
      };

      connect();

      // 언마운트 시 소켓 및 타임아웃 정리
      return () => {
        if (reconnectTimeout) clearTimeout(reconnectTimeout);
        socket.close();
      };
    };

    // 로그인 상태 확인
    const checkAuth = async () => {
      const res = await fetch("/api/login/auth", { credentials: "include" });
      if (!res.ok) {
        navigate("/login", { replace: true });
      } else {
        await fetchData();
        connectWebSocket();
      }
      // 실패 시 아무 동작 안 함
    };
    checkAuth();
  }, [navigate, exchange1, exchange2]);

  // 선택된 티커가 변경될 때마다 cryptoOptions에 추가
  useEffect(() => {
    if (selectedTicker) {
      addCryptoOption({
        value: selectedTicker,
        label: `${selectedTicker}/USDT`,
      });
    }
  }, [selectedTicker, addCryptoOption]);

  // if (loading) return <div>로딩 중...</div>;
  return (
    <div>
      {/* 거래소 선택 SelectBox */}
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        sx={{ width: 400, marginTop: 3 }}
      >
        <TextField
          select
          label="거래소1"
          value={exchange1}
          onChange={(e) => setExchange1(e.target.value)}
          SelectProps={{ native: true }}
          sx={{ flex: 1 }}
        >
          {exchange1Options.map((ex) => (
            <option key={ex} value={ex}>
              {ex}
            </option>
          ))}
        </TextField>
        <TextField
          select
          label="거래소2"
          value={exchange2}
          onChange={(e) => setExchange2(e.target.value)}
          SelectProps={{ native: true }}
          sx={{ flex: 1 }}
        >
          {exchange2Options.map((ex) => (
            <option key={ex} value={ex}>
              {ex}
            </option>
          ))}
        </TextField>
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
          exchange1={exchange1}
          exchange2={exchange2}
          symbol={selectedTicker}
          interval="1m"
        />
      )}
    </div>
  );
};

export default Home;
