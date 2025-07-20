import type { WebSocketAdapter, WebSocketParams } from "./base";
import type { CandleBarData, TickerData } from "../../types/marketInfo";

interface GateioTickerData {
  contract: string;
  last: string;
  change_percentage: string;
  funding_rate: string;
  funding_rate_indicative: string;
  mark_price: string;
  index_price: string;
  total_size: string;
  volume_24h: string;
  volume_24h_btc: string;
  volume_24h_usd: string;
  quanto_base_rate: string;
  volume_24h_quote: string;
  volume_24h_settle: string;
  volume_24h_base: string;
  low_24h: string;
  high_24h: string;
}

interface GateioCandleData {
  t: number;
  v: number;
  c: string;
  h: string;
  l: string;
  o: string;
  n: string;
  a: string;
}

export const toFutureSymbol = (symbol: string): string => {
  if (symbol.endsWith("_USDT")) return symbol;
  return `${symbol}_USDT`;
};

export class GateioAdapter implements WebSocketAdapter {
  getRequestMessage(type: string, params: WebSocketParams) {
    switch (type) {
      case "kline":
        if (!params.symbol || !params.interval) {
          throw new Error("티커와 인터벌을 모두 지정해야 합니다.");
        }
        return {
          time: Math.floor(Date.now() / 1000),
          channel: "futures.candlesticks",
          event: "subscribe",
          payload: [params.interval, toFutureSymbol(params.symbol)],
        };
      case "ticker":
        if (!params.symbol) {
          throw new Error("티커를 지정해야 합니다.");
        }
        return {
          time: Math.floor(Date.now() / 1000),
          channel: "futures.tickers",
          event: "subscribe",
          payload: [toFutureSymbol(params.symbol)],
        };
      default:
        throw new Error(`Unknown request type: ${type}`);
    }
  }

  getResponseMessage(message: {
    time: number;
    time_ms: number;
    channel: string;
    event: string;
    result: (GateioTickerData | GateioCandleData)[];
  }): TickerData | CandleBarData | null {
    if (message.event === "subscribe" || message.event === "unsubscribe") {
      return null;
    }
    if (message.channel === "futures.tickers" && message.event === "update") {
      const tickerData = message.result[0] as GateioTickerData;
      return {
        channel: "futures.tickers",
        change_percentage: tickerData.change_percentage,
        funding_rate: tickerData.funding_rate,
        mark_price: tickerData.mark_price,
        index_price: tickerData.index_price,
      } as TickerData;
    } else if (
      message.channel === "futures.candlesticks" &&
      message.event === "update"
    ) {
      const candleData = message.result[0] as GateioCandleData;
      return {
        channel: "kline",
        time: Number(candleData.t) * 1000,
        open: parseFloat(candleData.o),
        high: parseFloat(candleData.h),
        low: parseFloat(candleData.l),
        close: parseFloat(candleData.c),
        volume: Number(candleData.v),
      } as CandleBarData;
    }
    return null;
  }
}
