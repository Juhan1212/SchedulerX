import type {
  CandleBarData,
  TickerData,
  ExchangeType,
  PositionData,
} from "../types/marketInfo";

export interface WebSocketAdapter {
  getResponseMessage(
    message: object
  ): TickerData | CandleBarData | PositionData | null;
  getRequestMessage(type: string, params: WebSocketParams): object | undefined;
}

export interface WebSocketParams {
  interval?: string;
  symbol?: string;
}

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

export class WebSocketAdapterFactory {
  static getAdapter(exchange: ExchangeType): WebSocketAdapter {
    switch (exchange) {
      case "GATEIO":
        return new GateioAdapter();
      case "UPBIT":
        return new UpbitAdapter();
      // case "BYBIT":
      //   return new BybitAdapter();
      // case "BINANCE":
      //   return new BinanceAdapter();
      //   case ExchangeType.BINGX:
      //     return new BingXAdapter()
      //   case ExchangeType.BINANCE:
      //     return new BinanceAdapter()
      //   case ExchangeType.BYBIT:
      //     return new BybitAdapter()
      //   case ExchangeType.OKX:
      //     return new OkxAdapter()
      default:
        throw new Error(`No adapter found for exchange: ${exchange}`);
    }
  }
}

export const toFutureSymbol = (symbol: string): string => {
  // Gate.io, Bybit 등은 _USDT로 끝나는 심볼을 사용
  if (symbol.endsWith("_USDT")) return symbol;
  return `${symbol}_USDT`;
};

// Gate.io adapter (passes through with minimal transformation)
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
    // Skip subscription confirmation messages
    if (message.event === "subscribe" || message.event === "unsubscribe") {
      return null;
    }

    if (message.channel === "futures.tickers" && message.event === "update") {
      // Handle ticker data
      const tickerData = message.result[0] as GateioTickerData;
      return {
        channel: "ticker",
        change_percentage: tickerData.change_percentage,
        funding_rate: tickerData.funding_rate,
        mark_price: tickerData.mark_price,
        index_price: tickerData.index_price,
      } as TickerData;
    } else if (
      message.channel === "futures.candlesticks" &&
      message.event === "update"
    ) {
      // Handle candlestick data
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

export const toUpbitSymbol = (symbol: string): string => {
  // BTC → KRW-BTC, ETH → KRW-ETH 등으로 변환
  if (symbol.startsWith("KRW-")) return symbol;
  return `KRW-${symbol}`;
};

export class UpbitAdapter implements WebSocketAdapter {
  getRequestMessage(type: string, params: WebSocketParams) {
    const ticket = Math.random().toString(36).substring(2, 15);
    switch (type) {
      case "kline":
        // Upbit은 배열 형태로 요청, type: candle.1m 등, codes: [symbol...]
        // 예시: [{ticket}, {type: "candle.1m", codes: [...]}, {format: "DEFAULT"}]
        if (type === "kline") {
          if (!params.symbol || !params.interval) {
            console.log(params);
            throw new Error("티커와 인터벌을 모두 지정해야 합니다.");
          }

          // symbol이 string 또는 string[]일 수 있음
          return [
            { ticket: ticket },
            {
              type: `candle.${params["interval"] || "1m"}`,
              codes: [toUpbitSymbol(params["symbol"])],
            },
            { format: "JSON_LIST" },
          ];
        }
        break;
      // Upbit ticker 등 필요시 확장
      default:
        throw new Error(`Unknown request type: ${type}`);
    }
  }

  getResponseMessage(
    message: {
      type: string;
      code: string;
      [key: string]: string;
    }[]
  ) {
    if (message[0].type.startsWith("candle")) {
      return {
        channel: "kline",
        time: new Date(
          message[0].candle_date_time_utc + "Z" // UTC로 인식하기 위해 "Z" 추가
        ).getTime(),
        open: Number(message[0].opening_price),
        high: Number(message[0].high_price),
        low: Number(message[0].low_price),
        close: Number(message[0].trade_price),
        volume: Number(message[0].candle_acc_trade_volume),
      } as CandleBarData;
    }
    return null;
  }
}
