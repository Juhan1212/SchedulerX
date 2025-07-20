import { createStore } from "zustand";
import {
  WebSocketAdapterFactory,
  type WebSocketParams,
} from "../helpers/wsAdapter/base";
import type {
  CandleBarData,
  ExchangeType,
  PositionData,
  TickerData,
} from "../types/marketInfo";

interface WebSocketState {
  exchange: string;
  symbol: string;
  interval: string;
  listeners: ((data: TickerData | CandleBarData | PositionData) => void)[];
  pendingOperations: { type: string; params: WebSocketParams }[];
  socket: WebSocket | null;
  reconnectTimeout: NodeJS.Timeout | null;
  isConnected: boolean;

  setExchange: (exchange: string) => void;
  setSymbol: (symbol: string) => void;
  setInterval: (interval: string) => void;
  addMessageListener: (
    listener: (data: TickerData | CandleBarData | PositionData) => void
  ) => void;
  removeMessageListener: (
    listener: (data: TickerData | CandleBarData | PositionData) => void
  ) => void;
  sendMessage: (type: string, message: WebSocketParams) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  subscribeToTicker: (symbol: string) => void;
  unsubscribeFromTicker: (symbol: string) => void;
  subscribeToCandleBars: () => void;
  unsubscribeFromCandleBars: (symbol: string, interval: string) => void;
}

const socketMap: Record<string, string> = {
  GATEIO: "wss://fx-ws.gateio.ws/v4/ws/usdt",
  BITGET: "wss://ws.bitget.com/v2/ws/public",
  BINGX: "wss://open-api-cswap-ws.bingx.com/market",
  BINANCE: "wss://ws-fapi.binance.com/ws-fapi/v1",
  BYBIT: "wss://stream.bybit.com/v5/public/linear",
  OKX: "wss://ws.okx.com:8443/ws/v5/public",
  UPBIT: "wss://api.upbit.com/websocket/v1",
};

// 스토어 생성 함수
export const createWebSocketStore = (initialState: Partial<WebSocketState>) =>
  createStore<WebSocketState>((set, get) => ({
    exchange: initialState.exchange!,
    symbol: initialState.symbol!,
    interval: initialState.interval!,
    listeners: [],
    pendingOperations: [],
    socket: null,
    reconnectTimeout: null,
    isConnected: false,

    setExchange: (exchange) => set({ exchange }),
    setSymbol: (symbol) => {
      // 심볼 변경: 상태만 변경 후 ws 재연결
      set({ symbol });
      get().disconnectWebSocket();
      get().connectWebSocket();
    },
    setInterval: (interval) => {
      // 인터벌 변경: 상태만 변경 후 ws 재연결
      set({ interval });
      get().disconnectWebSocket();
      get().connectWebSocket();
    },

    addMessageListener: (listener) => {
      set((state) => ({
        listeners: [...state.listeners, listener],
      }));
    },

    removeMessageListener: (listener) => {
      set((state) => ({
        listeners: state.listeners.filter((l) => l !== listener),
      }));
    },

    sendMessage: (type: string, params: WebSocketParams) => {
      const { exchange, socket, pendingOperations } = get();
      if (!exchange) return;

      if (socket && socket.readyState === WebSocket.OPEN) {
        const exchangeAdapter = WebSocketAdapterFactory.getAdapter(
          exchange as ExchangeType
        );
        const transformedMessage = exchangeAdapter.getRequestMessage(
          type,
          params
        );
        socket.send(JSON.stringify(transformedMessage));
      } else {
        // 소켓이 열려 있지 않으면 대기 중인 작업에 추가
        set({ pendingOperations: [...pendingOperations, { type, params }] });
      }
    },

    connectWebSocket: () => {
      const {
        exchange,
        socket,
        reconnectTimeout,
        pendingOperations,
        listeners,
      } = get();
      if (!exchange || socket) return;

      const ws = new WebSocket(socketMap[exchange]);
      const exchangeAdapter = WebSocketAdapterFactory.getAdapter(
        exchange as ExchangeType
      );

      ws.onopen = () => {
        set({ isConnected: true });

        // 재연결 타이머가 있다면 제거
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          set({ reconnectTimeout: null });
        }

        // 대기 중인 메시지 전송
        pendingOperations.forEach((operation) => {
          get().sendMessage(operation.type, operation.params);
        });
        // 대기 중인 작업 초기화
        set({ pendingOperations: [] });

        // 연결되면 kline 구독
        get().subscribeToCandleBars();
        // 연결되면 ticker 구독
        if (exchange !== "UPBIT") {
          get().subscribeToTicker(get().symbol);
        }
      };

      ws.onclose = () => {
        // 재연결 타이머 설정
        // if (!get().reconnectTimeout) {
        //   const timeout = setTimeout(() => {
        //     set({ isConnected: false, socket: null, reconnectTimeout: null });
        //     get().connectWebSocket();
        //   }, 1000);
        //   set({ reconnectTimeout: timeout });
        // }
      };

      ws.onerror = (error) => {
        console.error("웹소켓 에러", error);
        ws.close();
      };

      ws.onmessage = async (event) => {
        let jsonStr: string;
        if (typeof event.data === "string") {
          jsonStr = event.data;
        } else if (event.data instanceof Blob) {
          // 브라우저 환경
          jsonStr = await event.data.text();
        } else {
          // fallback
          jsonStr = String(event.data);
        }
        const data = JSON.parse(jsonStr);
        const transformedData = exchangeAdapter.getResponseMessage(data);
        if (!transformedData) return;
        listeners.forEach((listener) => listener(transformedData));
      };

      set({ socket: ws });
    },

    disconnectWebSocket: () => {
      const { socket } = get();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
        set({ socket: null });
      }
    },

    subscribeToTicker: (symbol) => {
      if (!symbol) return;
      const { sendMessage } = get();

      sendMessage("ticker", {
        symbol,
      });
    },

    // 구독 해제 지원하는 거래소만 가능
    unsubscribeFromTicker: (symbol) => {
      if (!symbol) return;
      return;
      // const { sendMessage } = get();

      // sendMessage({
      //   action: "unsubscribe",
      //   channel: "futures.tickers",
      //   params: { symbol: symbol },
      // });
    },

    subscribeToCandleBars: () => {
      const { symbol, interval, sendMessage } = get();
      if (!symbol || !interval) return;

      sendMessage("kline", {
        symbol,
        interval,
      });
    },

    // 구독 해제 지원하는 거래소만 가능
    unsubscribeFromCandleBars: (symbol, interval) => {
      if (!symbol || !interval) return;
      // const { sendMessage } = get();

      // sendMessage({
      //   action: "unsubscribe",
      //   channel: "futures.candlesticks",
      //   params: { symbol, interval },
      // });
    },
  }));
