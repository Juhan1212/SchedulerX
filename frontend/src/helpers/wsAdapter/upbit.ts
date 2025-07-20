import type { WebSocketAdapter, WebSocketParams } from "./base";
import type { CandleBarData } from "../../types/marketInfo";

export const toUpbitSymbol = (symbol: string): string => {
  if (symbol.startsWith("KRW-")) return symbol;
  return `KRW-${symbol}`;
};

export class UpbitAdapter implements WebSocketAdapter {
  getRequestMessage(type: string, params: WebSocketParams) {
    switch (type) {
      case "kline": {
        if (!params.symbol || !params.interval) {
          console.log(params);
          throw new Error("티커와 인터벌을 모두 지정해야 합니다.");
        }
        const symbols = Array.isArray(params.symbol)
          ? params.symbol
          : [params.symbol];
        symbols.push("KRW-USDT");
        let interval = params["interval"] || "1m";
        if (interval === "1h") interval = "60m";
        if (interval === "4h") interval = "240m";
        return [
          { ticket: "test" },
          {
            type: `candle.${interval}`,
            codes: symbols.map(toUpbitSymbol),
          },
          { format: "JSON_LIST" },
        ];
      }
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
    try {
      if (message[0].type.startsWith("candle")) {
        return {
          channel: "kline",
          symbol: message[0].code.replace("KRW-", ""),
          time: new Date(message[0].candle_date_time_utc + "Z").getTime(),
          open: Number(message[0].opening_price),
          high: Number(message[0].high_price),
          low: Number(message[0].low_price),
          close: Number(message[0].trade_price),
          volume: Number(message[0].candle_acc_trade_volume),
        } as CandleBarData;
      }
    } catch (error) {
      console.log(message);
      console.error("WebSocket message parsing error:", error);
    }
    return null;
  }
}
