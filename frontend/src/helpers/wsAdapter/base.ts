import type {
  CandleBarData,
  TickerData,
  PositionData,
  ExchangeType,
} from "../../types/marketInfo";
import { BybitAdapter } from "./bybit";
import { GateioAdapter } from "./gateio";
import { UpbitAdapter } from "./upbit";

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

export class WebSocketAdapterFactory {
  static getAdapter(exchange: ExchangeType): WebSocketAdapter {
    switch (exchange) {
      case "GATEIO":
        return new GateioAdapter();
      case "UPBIT":
        return new UpbitAdapter();
      case "BYBIT":
        return new BybitAdapter();
      default:
        throw new Error(`No adapter found for exchange: ${exchange}`);
    }
  }
}
