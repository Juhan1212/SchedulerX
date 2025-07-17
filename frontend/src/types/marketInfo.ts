export interface MarketInfo {
  change_percentage: number | null;
  funding_rate: number | null;
  index_price: number | null;
  mark_price: number | null;
}

export interface TickerData {
  change_percentage: string | null;
  channel?: string | null;
  funding_rate: string | null;
  index_price: string | null;
  mark_price: string | null;
}

export interface CandleBarData {
  channel?: string | null;
  symbol?: string | null;
  close: number;
  high: number;
  low: number;
  open: number;
  time: number;
  volume: number;
}

export interface PositionData {
  channel?: string | null;
  data: {
    contract: string;
    leverage: number;
    margin: number;
    entry_price: number;
    liquidation_price: number;
    size: number;
    user: string;
  }[];
}

export interface PositionByUser {
  contract: string;
  leverage: number;
  margin: number;
  entry_price: number;
  liquidation_price: number;
  size: number;
  user: string;
}

export interface SendWebSocketMessage {
  type: string; // e.g., "kline", "ticker"
  params: object;
}

export interface CandlestickParams {
  symbol: string;
  interval: string;
}

export interface TickerParams {
  symbol: string;
}

export type SubscriptionParams = CandlestickParams | TickerParams; // This union type is allowed as it is erasable

export interface RawCandleData {
  t: string;
  o: string;
  h: string;
  l: string;
  c: string;
  v: string;
}

export const ExchangeType = {
  BINANCE: "BINANCE",
  BYBIT: "BYBIT",
  BINGX: "BINGX",
  BITGET: "BITGET",
  GATEIO: "GATEIO",
  OKX: "OKX",
  UPBIT: "UPBIT",
} as const;
export type ExchangeType = (typeof ExchangeType)[keyof typeof ExchangeType];

export const ContractSize = {
  BTC_USDT: 0.0001,
  ETH_USDT: 0.01,
  SOL_USDT: 1,
} as const;
export type ContractSize = (typeof ContractSize)[keyof typeof ContractSize];
