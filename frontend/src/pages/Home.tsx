import { useEffect, useState, useCallback } from "react";
import { useCryptoOptionsStore } from "../states/cryptoOptionState";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Stack from "@mui/material/Stack";
import CompChart from "../components/chart/CompChart";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import "../assets/styles/routes/trade.scss";
import { useNavigate } from "react-router-dom";

// Seed 관련 import
import Button from "@mui/material/Button";
import Input from "@mui/material/Input";

const exchange1Options = ["UPBIT", "BITHUMB"];
const exchange2Options = ["GATEIO", "BYBIT", "BINANCE", "OKX"];

const Home = () => {
  // DataGrid columns 정의 (함수 내부로 이동)
  const columns: GridColDef[] = [
    { field: "name", headerName: "티커", width: 120 },
    {
      field: "ex_rate",
      headerName: "환율",
      width: 180,
      valueFormatter: (params) => {
        if (!params) return "-";
        return Number(params).toLocaleString();
      },
    },
  ];
  const [exchange1, setExchange1] = useState<string>("UPBIT");
  const [exchange2, setExchange2] = useState<string>("BYBIT");
  const [tickers, setTickers] = useState<
    { name: string; ex_rate?: string | null }[]
  >([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>("XRP"); // 감시할 티커 선택
  const { addCryptoOption } = useCryptoOptionsStore();
  const navigate = useNavigate();

  // Seed 관련 state
  const [seed, setSeed] = useState<number | null>(null);
  const [seedInput, setSeedInput] = useState<string>("");

  // 공통 티커 데이터 가져오기 useCallback
  const fetchTickers = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/tickers?exchange1=${exchange1}&exchange2=${exchange2}`,
        { credentials: "include" }
      );
      if (!res.ok) {
        throw new Error(`Fetch error: ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      setTickers(
        [...data].sort((a, b) => {
          const av =
            a.ex_rate === null || a.ex_rate === undefined
              ? -Infinity
              : Number(a.ex_rate);
          const bv =
            b.ex_rate === null || b.ex_rate === undefined
              ? -Infinity
              : Number(b.ex_rate);
          return av - bv;
        })
      );
    } catch (err) {
      if (err instanceof TypeError) {
        alert("네트워크 오류가 발생했습니다. 인터넷 연결을 확인하세요.");
      } else {
        console.error("Unknown error:", err);
        alert("알 수 없는 오류가 발생했습니다.");
      }
    }
  }, [exchange1, exchange2]);

  // WebSocket 연결 함수 useCallback
  const connectWebSocket = useCallback(() => {
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
            setTickers((prev) => {
              const map = new Map(prev.map((t) => [t.name, t]));
              msg.results.forEach(
                (item: { name: string; ex_rate?: string | null }) => {
                  map.set(item.name, { ...map.get(item.name), ...item });
                }
              );
              return Array.from(map.values()).sort((a, b) => {
                const av =
                  a.ex_rate === null || a.ex_rate === undefined
                    ? -Infinity
                    : Number(a.ex_rate);
                const bv =
                  b.ex_rate === null || b.ex_rate === undefined
                    ? -Infinity
                    : Number(b.ex_rate);
                return av - bv;
              });
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
        if (!event.wasClean) {
          console.log("Reconnecting WebSocket...");
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      socket.close();
    };
  }, [exchange1, exchange2]);

  // Seed 조회 함수 useCallback
  const fetchSeed = useCallback(async () => {
    try {
      const res = await fetch("/api/seed", { credentials: "include" });
      if (!res.ok) {
        throw new Error(`Fetch error: ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      setSeed(data.amt);
      setSeedInput(data.amt.toString());
    } catch (err) {
      if (err instanceof TypeError) {
        alert("네트워크 오류가 발생했습니다. 인터넷 연결을 확인하세요.");
      } else {
        console.error("Unknown error:", err);
        alert("알 수 없는 오류가 발생했습니다.");
      }
    }
  }, []);

  // Seed 변경 함수 useCallback
  const handleSeedChange = useCallback(async () => {
    try {
      const res = await fetch("/api/seed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ amt: Number(seedInput) }),
      });
      if (!res.ok) {
        throw new Error(`Fetch error: ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      setSeed(data.amt);
      setSeedInput(data.amt.toString());
    } catch (err) {
      if (err instanceof TypeError) {
        alert("네트워크 오류가 발생했습니다. 인터넷 연결을 확인하세요.");
      } else {
        console.error("Unknown error:", err);
        alert("알 수 없는 오류가 발생했습니다.");
      }
    }
  }, [seedInput]);

  useEffect(() => {
    // 로그인 상태 확인
    const checkAuth = async () => {
      const res = await fetch("/api/login/auth", { credentials: "include" });
      if (!res.ok) {
        navigate("/login", { replace: true });
      } else {
        connectWebSocket();
        await fetchTickers();
        await fetchSeed();
      }
    };
    checkAuth();
  }, [navigate, fetchTickers, connectWebSocket, fetchSeed]);

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
        <>
          <CompChart
            exchange1={exchange1}
            exchange2={exchange2}
            symbol={selectedTicker}
            interval="1m"
          />
          {/* Seed 조회 및 변경 UI */}
          <div style={{ margin: "16px 0" }}>
            <b>Seed:</b>{" "}
            {seed && (
              <>
                <Input
                  type="number"
                  value={seedInput}
                  onChange={(e) => setSeedInput(e.target.value)}
                  style={{ width: 100, marginRight: 8 }}
                />
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleSeedChange}
                >
                  변경
                </Button>
              </>
            )}
          </div>
          {tickers && tickers.length > 0 && (
            <div style={{ height: 600, width: 400, marginTop: 24 }}>
              <DataGrid
                rows={tickers.map((t) => ({ id: t.name, ...t }))}
                columns={columns}
                disableRowSelectionOnClick
                hideFooterPagination
              />
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Home;
