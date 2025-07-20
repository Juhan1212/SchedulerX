import type { WebSocketAdapter, WebSocketParams } from "./base";
import type { CandleBarData, TickerData } from "../../types/marketInfo";

interface BybitKlineData {
  symbol: string;
  start: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

interface BybitTickerData {
  symbol: string;
  mark_price?: string;
  index_price?: string;
  funding_rate?: string;
  price24hPcnt?: string;
  lastPrice?: string;
  [key: string]: unknown;
}

type BybitWebSocketMessage = {
  topic: string;
  data: BybitKlineData | BybitTickerData;
  [key: string]: unknown;
};

const interval_map = {
  "1m": "1",
  "3m": "3",
  "5m": "5",
  "15m": "15",
  "30m": "30",
  "1h": "60",
  "4h": "240",
  "8h": "480",
  "1d": "D",
  "1w": "W",
};

export class BybitAdapter implements WebSocketAdapter {
  getRequestMessage(type: string, params: WebSocketParams) {
    if (!params.symbol) {
      throw new Error("티커를 지정해야 합니다.");
    }
    switch (type) {
      case "kline": {
        if (!params.interval) {
          throw new Error("인터벌을 지정해야 합니다.");
        }
        return {
          op: "subscribe",
          args: [
            `kline.${interval_map[params.interval as keyof typeof interval_map]}.${params.symbol}USDT`,
          ],
        };
      }
      case "ticker": {
        return {
          op: "subscribe",
          args: [`tickers.${params.symbol}USDT`],
        };
      }
      default:
        throw new Error(`Unknown request type: ${type}`);
    }
  }

  getResponseMessage(
    message: BybitWebSocketMessage
  ): CandleBarData | TickerData | null {
    if (message.topic && message.data) {
      if (message.topic.startsWith("kline.")) {
        let d = message.data as BybitKlineData | BybitKlineData[];
        if (Array.isArray(d)) {
          d = d[0];
        }
        if (!d) return null;
        return {
          channel: "kline",
          symbol: d.symbol || (message.topic.split(".")[2] ?? ""),
          time: Number(d.start),
          open: Number(d.open),
          high: Number(d.high),
          low: Number(d.low),
          close: Number(d.close),
          volume: Number(d.volume),
        } as CandleBarData;
      } else if (message.topic.startsWith("tickers.")) {
        const d = message.data as BybitTickerData;
        return {
          channel: "futures.tickers",
          change_percentage: d.price24hPcnt,
          funding_rate: d.fundingRate,
          mark_price: d.markPrice ?? d.lastPrice,
          index_price: d.indexPrice,
        } as TickerData;
      }
    }
    return null;
  }
}
