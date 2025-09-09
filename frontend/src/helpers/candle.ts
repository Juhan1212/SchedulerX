export interface CandleData {
  candleData: {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }[];
  volumeData: {
    time: number;
    value: number;
    color?: string;
  }[];
  ex1VolumeData?: {
    time: number;
    value: number;
    color?: string;
  }[];
  ex2VolumeData?: {
    time: number;
    value: number;
    color?: string;
  }[];
  usdtCandleData?: {
    time: number;
    value: number;
  }[];
}

export interface CandlestickParams {
  exchange: string;
  symbol: string;
  interval: string;
  from?: number;
  to?: number;
  limit?: number;
}
